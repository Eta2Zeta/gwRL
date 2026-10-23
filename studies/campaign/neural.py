"""Campaign entity-graph policy/value model and actor-routed batched inference.

Values returned by the network are in raw-return/value_scale units. The linear
three-component head is unbounded; NeuralEvaluator multiplies by value_scale
before handing predictions to MCTS. The default scale is 100 IPP wealth units.
"""
from __future__ import annotations

import math
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor, nn

from studies.shared.multiplayer_mcts import Evaluation, PLAYERS, vector
from .features import (EXTERNAL_REFERENCE, NODE_TYPES, NUMERIC_DIM, RELATIONS, SCHEMA,
                       Graph, action_factors, cached_action, cached_context, cached_observation, canonical, make_input)


@dataclass(frozen=True)
class CampaignModelConfig:
    hidden_dim: int = 64
    message_layers: int = 2
    token_buckets: int = 16384
    value_scale: float = 100.0
    policy_factorization: bool = True

    def __post_init__(self) -> None:
        if type(self.hidden_dim) is not int or self.hidden_dim < 4:
            raise ValueError("hidden_dim must be at least four")
        if type(self.message_layers) is not int or self.message_layers < 1:
            raise ValueError("message_layers must be positive")
        if type(self.token_buckets) is not int or self.token_buckets < 2:
            raise ValueError("token_buckets must be at least two")
        if not math.isfinite(self.value_scale) or self.value_scale <= 0:
            raise ValueError("value_scale must be positive and finite")
        if type(self.policy_factorization) is not bool:
            raise ValueError("policy_factorization must be a boolean")


@dataclass
class _EncodedGraph:
    graph: Graph
    nodes: Tensor
    pooled: Tensor


@dataclass
class _GraphTensors:
    graph: Graph
    tokens: Tensor
    offsets: Tensor
    types: Tensor
    numbers: Tensor
    sources: Tensor
    targets: Tensor
    relations: Tensor


# These tensors contain only source data, never model outputs or gradients.
# Sharing them across actor models is safe; the byte limit also bounds large
# observation/menu entries independently of the source-graph entry limits.
_GRAPH_TENSORS: OrderedDict[tuple, _GraphTensors] = OrderedDict()
_GRAPH_TENSOR_BYTES = 0
_GRAPH_TENSOR_LIMIT = 32 * 1024 * 1024


def _graph_tensors(graph: Graph, device: torch.device, dtype: torch.dtype) -> _GraphTensors:
    global _GRAPH_TENSOR_BYTES
    key = (id(graph), device, dtype)
    if key in _GRAPH_TENSORS:
        _GRAPH_TENSORS.move_to_end(key)
        return _GRAPH_TENSORS[key]
    long = lambda values: torch.tensor(values, dtype=torch.long, device=device)
    sources, targets, relations = zip(*graph.edges) if graph.edges else ((), (), ())
    # An inference-mode tensor cannot subsequently be saved for backward.
    # Construct ordinary constant tensors even when called during inference.
    with torch.inference_mode(False):
        result = _GraphTensors(graph, long(graph.token_ids), long(graph.token_offsets), long(graph.types),
                               torch.tensor(graph.numeric, dtype=dtype, device=device),
                               long(sources), long(targets), long(relations))
    size = sum(value.numel() * value.element_size() for value in vars(result).values()
               if isinstance(value, Tensor))
    if size <= _GRAPH_TENSOR_LIMIT:
        while _GRAPH_TENSORS and _GRAPH_TENSOR_BYTES + size > _GRAPH_TENSOR_LIMIT:
            _, old = _GRAPH_TENSORS.popitem(last=False)
            _GRAPH_TENSOR_BYTES -= sum(value.numel() * value.element_size() for value in vars(old).values()
                                       if isinstance(value, Tensor))
        _GRAPH_TENSORS[key] = result
        _GRAPH_TENSOR_BYTES += size
    return result


class _GraphEncoder(nn.Module):
    def __init__(self, config: CampaignModelConfig) -> None:
        super().__init__()
        dim = config.hidden_dim
        self.tokens = nn.EmbeddingBag(config.token_buckets, dim, mode="mean", include_last_offset=True)
        self.types = nn.Embedding(len(NODE_TYPES), dim)
        self.numbers = nn.Linear(NUMERIC_DIM, dim)
        self.relations = nn.Embedding(RELATIONS, dim)
        self.input_norm = nn.LayerNorm(dim)
        self.messages = nn.ModuleList(nn.Linear(dim, dim) for _ in range(config.message_layers))
        self.updates = nn.ModuleList(nn.Sequential(nn.Linear(dim * 2, dim), nn.GELU(), nn.LayerNorm(dim))
                                     for _ in range(config.message_layers))
        self.pool = nn.Sequential(nn.Linear(dim * 2 + 1, dim), nn.GELU(), nn.LayerNorm(dim))

    def forward(self, graphs: Sequence[Graph], external: Sequence[Sequence[_EncodedGraph]] | None = None) -> list[_EncodedGraph]:
        if not graphs:
            return []
        device, dtype = self.tokens.weight.device, self.tokens.weight.dtype
        packs = [_graph_tensors(graph, device, dtype) for graph in graphs]
        starts, token_starts = [0], [0]
        for graph in graphs:
            starts.append(starts[-1] + graph.node_count)
            token_starts.append(token_starts[-1] + len(graph.token_ids))
        long = lambda values: torch.tensor(values, dtype=torch.long, device=device)
        node_count = starts[-1]
        cat = lambda values: values[0] if len(values) == 1 else torch.cat(values)
        ids = cat([pack.tokens for pack in packs])
        offsets = (packs[0].offsets if len(packs) == 1 else
                   torch.cat([*(pack.offsets[:-1] + start for pack, start in zip(packs, token_starts)),
                              long([token_starts[-1]])]))
        types = cat([pack.types for pack in packs])
        numbers = cat([pack.numbers for pack in packs])
        sources = [pack.sources + start for pack, start in zip(packs, starts)]
        targets = [pack.targets + start for pack, start in zip(packs, starts)]
        relations = [pack.relations for pack in packs]
        encoded = self.tokens(ids, offsets) + self.types(types)
        encoded = self.input_norm(encoded + self.numbers(numbers))
        # Context and observation encodings are read-only inputs for later
        # stages. Requests cannot send messages into another request's state.
        external_chunks = []
        external_count = 0
        if external is not None:
            for row, (graph, contexts) in enumerate(zip(graphs, external, strict=True)):
                for context in contexts:
                    indices, destinations = [], []
                    for destination, identity in graph.references:
                        for index in context.graph.identities.get(identity, ()):
                            indices.append(index)
                            destinations.append(starts[row] + destination)
                    if indices:
                        external_chunks.append(context.nodes.index_select(0, long(indices)))
                        offset = node_count + external_count
                        sources.append(torch.arange(offset, offset + len(indices), device=device))
                        targets.append(long(destinations))
                        relations.append(torch.full((len(indices),), EXTERNAL_REFERENCE, dtype=torch.long, device=device))
                        external_count += len(indices)
        source_ids, target_ids, relation_ids = cat(sources), cat(targets), cat(relations)
        degree = torch.bincount(target_ids, minlength=node_count).clamp_min(1).to(dtype).unsqueeze(1)
        external_nodes = torch.cat(external_chunks) if external_chunks else None
        for message, update in zip(self.messages, self.updates, strict=True):
            bank = torch.cat((encoded, external_nodes)) if external_nodes is not None else encoded
            gathered = bank.index_select(0, source_ids) + self.relations(relation_ids)
            aggregate = torch.zeros_like(encoded)
            aggregate.index_add_(0, target_ids, message(gathered))
            encoded = encoded + update(torch.cat((encoded, aggregate / degree), dim=1))
        owners = torch.repeat_interleave(torch.arange(len(graphs), device=device),
                                         long([graph.node_count for graph in graphs]))
        summed = encoded.new_zeros((len(graphs), encoded.shape[1]))
        summed.index_add_(0, owners, encoded)
        counts = encoded.new_tensor([graph.node_count for graph in graphs]).unsqueeze(1)
        maximum = encoded.new_full(summed.shape, -torch.inf)
        maximum.scatter_reduce_(0, owners.unsqueeze(1).expand_as(encoded), encoded, reduce="amax", include_self=True)
        pooled = self.pool(torch.cat((summed / counts, maximum, counts.log1p()), dim=1))
        return [_EncodedGraph(graph, encoded[starts[row]:starts[row + 1]], pooled[row])
                for row, graph in enumerate(graphs)]


class CampaignPolicyValueNet(nn.Module):
    """Complete registry/state/action graph model with variable legal menus.

    Static token/topology parsing can be reused, but each forward recomputes all
    learned embeddings. Within a batch a shared context is encoded once; its
    state-independent vectors are safely reused inside that autograd graph.
    Actions read their own complete parameters plus referenced state/registry
    entities. All actual legal actions are scored; padded actions never exist.
    """
    def __init__(self, config: CampaignModelConfig) -> None:
        super().__init__()
        self.config = config
        dim = config.hidden_dim
        self.encoder = _GraphEncoder(config)
        self.state_encoder = nn.Sequential(nn.Linear(dim * 2, dim), nn.GELU(), nn.LayerNorm(dim))
        self.policy_head = nn.Sequential(nn.Linear(dim * 2, dim), nn.GELU(), nn.Linear(dim, 1))
        self.factor_heads = nn.ModuleList(nn.Sequential(nn.Linear(dim * 2, dim), nn.GELU(), nn.Linear(dim, 1))
                                         for _ in range(4))
        self.value_head = nn.Sequential(nn.Linear(dim, dim), nn.GELU(), nn.Linear(dim, 3))

    @staticmethod
    def _conditional_log_softmax(scores: Tensor, owners: Tensor, count: int) -> Tensor:
        maximum = scores.new_full((count,), -torch.inf)
        maximum.scatter_reduce_(0, owners, scores, reduce="amax", include_self=True)
        shifted = scores - maximum.index_select(0, owners)
        totals = scores.new_zeros((count,))
        totals.index_add_(0, owners, shifted.exp())
        return shifted - totals.log().index_select(0, owners)

    def _factored_logits(self, state: Tensor, latent: Tensor, scores: Tensor, features: Sequence[dict]) -> Tensor:
        """Normalize family -> source/group -> path -> target -> exact action.

        These are neural conditional readouts of the same complete legal menu.
        No game action is inserted/reordered, no group is declared equivalent,
        and no leaf is pruned. All sibling scores are evaluated in batches.
        """
        factors = [action_factors(action) for action in features]
        joint = torch.zeros_like(scores)
        for level, head in enumerate(self.factor_heads, 1):
            prefixes = sorted({factor[:level] for factor in factors})
            lookup = {prefix: index for index, prefix in enumerate(prefixes)}
            owners = torch.tensor([lookup[factor[:level]] for factor in factors], dtype=torch.long, device=scores.device)
            means = latent.new_zeros((len(prefixes), latent.shape[1]))
            means.index_add_(0, owners, latent)
            counts = torch.bincount(owners, minlength=len(prefixes)).to(latent.dtype).unsqueeze(1)
            group_scores = head(torch.cat((state.expand(len(prefixes), -1), means / counts), dim=1)).squeeze(1)
            parents = {prefix: index for index, prefix in enumerate(sorted({prefix[:-1] for prefix in prefixes}))}
            parent_ids = torch.tensor([parents[prefix[:-1]] for prefix in prefixes], dtype=torch.long, device=scores.device)
            conditional = self._conditional_log_softmax(group_scores, parent_ids, len(parents))
            joint = joint + conditional.index_select(0, owners)
        return joint + self._conditional_log_softmax(scores, owners, len(prefixes))

    def forward_batch(self, inputs: Sequence[dict[str, Any]]) -> tuple[list[Tensor], Tensor]:
        if not inputs:
            return [], self.value_head[-1].weight.new_empty((0, 3))
        contexts, context_rows, context_lookup = [], [], {}
        observations, action_graphs, action_rows, lengths = [], [], [], []
        for row, item in enumerate(inputs):
            if item.get("schema") != SCHEMA or set(item) != {"schema", "observation", "context", "actions"}:
                raise ValueError("Unsupported campaign neural input schema")
            if not isinstance(item["observation"], dict) or not isinstance(item["context"], dict) or not isinstance(item["actions"], list):
                raise ValueError("Neural inputs need observation/context objects and an action list")
            context_key = canonical(item["context"])
            if context_key not in context_lookup:
                context_lookup[context_key] = len(contexts)
                contexts.append(cached_context(context_key, self.config.token_buckets))
            context_rows.append(context_lookup[context_key])
            observations.append(cached_observation(canonical(item["observation"]), self.config.token_buckets))
            lengths.append(len(item["actions"]))
            for action in item["actions"]:
                if not isinstance(action, dict):
                    raise ValueError("Each legal action needs a complete feature object")
                action_graphs.append(cached_action(canonical(action), self.config.token_buckets))
                action_rows.append(row)
        static = self.encoder(contexts)
        dynamic = self.encoder(observations, [[static[index]] for index in context_rows])
        states = self.state_encoder(torch.stack([torch.cat((dynamic[row].pooled, static[index].pooled))
                                                for row, index in enumerate(context_rows)]))
        values = self.value_head(states)  # Unbounded, in raw-value/value_scale units.
        if not action_graphs:
            return [values.new_empty((0,)) for _ in inputs], values
        actions = self.encoder(action_graphs, [[dynamic[row], static[context_rows[row]]] for row in action_rows])
        owners = torch.tensor(action_rows, dtype=torch.long, device=states.device)
        joint = torch.cat((states.index_select(0, owners), torch.stack([action.pooled for action in actions])), dim=1)
        all_logits = self.policy_head(joint).squeeze(1)
        logits = list(all_logits.split(lengths))
        if self.config.policy_factorization:
            action_latent = torch.stack([action.pooled for action in actions])
            offset = 0
            for row, count in enumerate(lengths):
                if count:
                    logits[row] = self._factored_logits(states[row], action_latent[offset:offset + count],
                                                       logits[row], inputs[row]["actions"])
                offset += count
        return logits, values

    def forward(self, inputs: Sequence[dict[str, Any]]) -> tuple[list[Tensor], Tensor]:
        return self.forward_batch(inputs)


class NeuralEvaluator:
    """Route each entitled actor to its model, retaining raw vector returns.

    A chance cutoff has no entitled actor: it deterministically averages the
    three models' raw value vectors and emits no policy. This is a bootstrap
    convention, not a chance action or a peek at the execution random stream.
    """
    def __init__(self, models: Mapping[str, CampaignPolicyValueNet], version: str) -> None:
        if set(models) != set(PLAYERS):
            raise ValueError("Provide one campaign model for Axis, Allies and Comintern")
        if not isinstance(version, str) or not version:
            raise ValueError("Neural evaluator needs a nonempty version")
        self.models, self.version = dict(models), version

    def evaluate(self, env: Any, actions: Sequence[Any]) -> Evaluation:
        return self.evaluate_batch([(env, actions)])[0]

    def evaluate_batch(self, requests: Sequence[tuple[Any, Sequence[Any]]]) -> list[Evaluation]:
        results: list[Evaluation | None] = [None] * len(requests)
        groups: dict[str, list[tuple[int, dict[str, Any]]]] = {player: [] for player in PLAYERS}
        chance_values: dict[int, list[tuple[float, float, float]]] = {}
        for row, (env, actions) in enumerate(requests):
            if env.is_terminal():
                if actions:
                    raise ValueError("A terminal state cannot have policy actions")
                results[row] = Evaluation([], vector(env.returns()))
                continue
            actor = env.current_decision_player()
            item = make_input(env, actions)
            if actor is None:
                if env.decision_kind() != "chance" or actions:
                    raise ValueError("An ownerless nonterminal evaluation must be a chance cutoff")
                chance_values[row] = []
                for player in PLAYERS:
                    groups[player].append((row, item))
            elif actor in PLAYERS:
                groups[actor].append((row, item))
            else:
                raise ValueError(f"Unknown campaign decision player: {actor}")
        for player in PLAYERS:
            if not groups[player]:
                continue
            model = self.models[player]
            training = model.training
            model.eval()
            try:
                with torch.inference_mode():
                    logits, values = model.forward_batch([item for _, item in groups[player]])
                    if values.shape != (len(groups[player]), 3) or len(logits) != len(groups[player]):
                        raise ValueError("Neural model returned an invalid batch shape")
                    for index, (row, item) in enumerate(groups[player]):
                        scores = logits[index]
                        if scores.shape != (len(item["actions"]),) or not torch.isfinite(scores).all():
                            raise ValueError("Neural policy must contain one finite logit per legal action")
                        raw = vector((values[index] * model.config.value_scale).tolist())
                        if row in chance_values:
                            chance_values[row].append(raw)
                        else:
                            results[row] = Evaluation(scores.softmax(0).tolist() if scores.numel() else [], raw)
            finally:
                model.train(training)
        for row, predictions in chance_values.items():
            results[row] = Evaluation([], vector([sum(value[i] for value in predictions) / len(PLAYERS) for i in range(3)]))
        if any(result is None for result in results):
            raise RuntimeError("A neural batch request was not evaluated")
        return [result for result in results if result is not None]
