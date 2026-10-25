"""Campaign entity-graph policy/value model and actor-routed batched inference.

Values returned by the network are in raw-return/value_scale units. The linear
three-component head is unbounded; NeuralEvaluator multiplies by value_scale
before handing predictions to MCTS. The default scale is 100 IPP wealth units.
"""
from __future__ import annotations

import inspect
import math
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor, nn

from studies.shared.multiplayer_mcts import Evaluation, PLAYERS, vector
from .features import (EXTERNAL_REFERENCE, NODE_TYPES, NUMERIC_DIM, RELATIONS, SCHEMA,
                       Graph, action_factors, cached_action, cached_context, cached_observation, canonical, make_input)

NUMERIC_SCHEMA = "campaign-numeric-input-v1"


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
    graph: Any
    nodes: Tensor
    pooled: Tensor


@dataclass
class _GraphTensors:
    graph: Any
    tokens: Tensor
    offsets: Tensor
    types: Tensor
    numbers: Tensor
    sources: Tensor
    targets: Tensor
    relations: Tensor
    retained_bytes: int = 0


def _graph_source_bytes(graph: Any) -> int:
    """Conservatively count source storage pinned by a cache's strong refs."""
    if hasattr(graph, "nbytes"):
        return int(graph.nbytes) + 256
    # Reference Graph stores boxed scalars, tuples and strings. Bounds include
    # per-element pointers/objects, containers, identity and reference strings;
    # overcounting shared objects is preferable to hiding retained observations.
    return (512 * graph.node_count + 36 * len(graph.token_ids) + 192 * len(graph.edges) + 512
            + sum(160 + len(key.encode("utf-8")) * 4 + 36 * len(indices)
                  for key, indices in graph.identities.items())
            + sum(160 + len(identity.encode("utf-8")) * 4 for _, identity in graph.references))


# These tensors contain only source data, never model outputs or gradients.
# Sharing them across actor models is safe; the byte limit also bounds large
# observation/menu entries independently of the source-graph entry limits.
_GRAPH_TENSORS: OrderedDict[tuple, _GraphTensors] = OrderedDict()
_GRAPH_TENSOR_BYTES = 0
_GRAPH_TENSOR_LIMIT = 32 * 1024 * 1024
_GRAPH_TENSOR_LOCK = threading.RLock()


def _graph_tensors(graph: Any, device: torch.device, dtype: torch.dtype) -> _GraphTensors:
    global _GRAPH_TENSOR_BYTES
    key = (id(graph), device, dtype)
    with _GRAPH_TENSOR_LOCK:
        if key in _GRAPH_TENSORS:
            _GRAPH_TENSORS.move_to_end(key)
            return _GRAPH_TENSORS[key]
    long = lambda values: torch.tensor(values, dtype=torch.long, device=device)
    # An inference-mode tensor cannot subsequently be saved for backward.
    # Construct ordinary constant tensors even when called during inference.
    with torch.inference_mode(False):
        if hasattr(graph, "arrays"):
            arrays = graph.arrays()
            # Copy read-only native buffers in compiled code. The tensors must
            # never provide a writable alias to an immutable source graph.
            result = _GraphTensors(graph, long(arrays["token_ids"]), long(arrays["token_offsets"]),
                                   long(arrays["types"]), torch.tensor(arrays["numeric"], dtype=dtype, device=device),
                                   long(arrays["sources"]), long(arrays["targets"]), long(arrays["relations"]))
        else:
            sources, targets, relations = zip(*graph.edges) if graph.edges else ((), (), ())
            result = _GraphTensors(graph, long(graph.token_ids), long(graph.token_offsets), long(graph.types),
                                   torch.tensor(graph.numeric, dtype=dtype, device=device),
                                   long(sources), long(targets), long(relations))
    size = _graph_source_bytes(graph) + sum(value.numel() * value.element_size() for value in vars(result).values()
                                           if isinstance(value, Tensor))
    result.retained_bytes = size
    if size <= _GRAPH_TENSOR_LIMIT:
        with _GRAPH_TENSOR_LOCK:
            if key in _GRAPH_TENSORS:
                _GRAPH_TENSORS.move_to_end(key)
                return _GRAPH_TENSORS[key]
            while _GRAPH_TENSORS and _GRAPH_TENSOR_BYTES + size > _GRAPH_TENSOR_LIMIT:
                _, old = _GRAPH_TENSORS.popitem(last=False)
                _GRAPH_TENSOR_BYTES -= old.retained_bytes
            _GRAPH_TENSORS[key] = result
            _GRAPH_TENSOR_BYTES += size
    return result


class _SourceCache:
    """Byte- and entry-bounded immutable preparation, with strong source refs."""
    def __init__(self, limit: int, entries: int) -> None:
        self.limit, self.entries, self.bytes = limit, entries, 0
        self.values: OrderedDict[tuple, tuple[Any, int]] = OrderedDict()
        self.source_refs: dict[int, tuple[Any, int, int]] = {}
        self.entry_sources: dict[tuple, tuple[int, ...]] = {}
        self._lock = threading.RLock()

    def __getstate__(self) -> dict:
        # Caches are process-local preparation, not checkpoint contents. Model
        # deepcopy and pickle retain all learned state while starting these cold.
        return {"limit": self.limit, "entries": self.entries}

    def __setstate__(self, state: dict) -> None:
        self.__init__(state["limit"], state["entries"])

    def get(self, key: tuple) -> Any:
        with self._lock:
            found = self.values.get(key)
            if found is not None:
                self.values.move_to_end(key)
                return found[0]
        return None

    def _remove(self, key: tuple) -> None:
        _, size = self.values.pop(key)
        self.bytes -= size
        for identity in self.entry_sources.pop(key):
            source, count, source_size = self.source_refs[identity]
            if count == 1:
                self.bytes -= source_size
                del self.source_refs[identity]
            else:
                self.source_refs[identity] = source, count - 1, source_size

    def put(self, key: tuple, value: Any, size: int, *, sources: Sequence[Any] = ()) -> Any:
        unique = {id(source): source for source in sources}
        source_sizes = {identity: _graph_source_bytes(source) for identity, source in unique.items()}
        with self._lock:
            if size + sum(source_sizes.values()) <= self.limit and self.entries:
                if key in self.values:
                    self._remove(key)
                def addition() -> int:
                    return size + sum(source_size for identity, source_size in source_sizes.items()
                                      if identity not in self.source_refs)
                while self.values and (self.bytes + addition() > self.limit or len(self.values) >= self.entries):
                    self._remove(next(iter(self.values)))
                self.values[key] = value, size
                self.bytes += size
                self.entry_sources[key] = tuple(unique)
                for identity, source in unique.items():
                    if identity in self.source_refs:
                        old_source, count, source_size = self.source_refs[identity]
                        self.source_refs[identity] = old_source, count + 1, source_size
                    else:
                        self.source_refs[identity] = source, 1, source_sizes[identity]
                        self.bytes += source_sizes[identity]
        return value

    def clear(self) -> None:
        with self._lock:
            self.values.clear()
            self.source_refs.clear()
            self.entry_sources.clear()
            self.bytes = 0


@dataclass
class _ReferenceIndices:
    graph: Any
    context: Any
    destinations: Tensor
    indices: Tensor


_REFERENCE_INDICES = _SourceCache(64 * 1024 * 1024, 4096)


def _reference_indices(graph: Any, context: Any, device: torch.device) -> _ReferenceIndices:
    key = (id(graph), id(context), device)
    cached = _REFERENCE_INDICES.get(key)
    if cached is not None:
        return cached
    with torch.inference_mode(False):
        if hasattr(graph, "external_references") and hasattr(context, "arrays"):
            destinations, indices = graph.external_references(context)
        else:
            # Mixed native/reference graphs are supported for diagnostics too.
            reference = graph.debug_graph() if hasattr(graph, "debug_graph") else graph
            registry = context.debug_graph() if hasattr(context, "debug_graph") else context
            reference = Graph(**reference) if isinstance(reference, dict) else reference
            registry = Graph(**registry) if isinstance(registry, dict) else registry
            destinations, indices = [], []
            for destination, identity in reference.references:
                for index in registry.identities.get(identity, ()):
                    indices.append(index)
                    destinations.append(destination)
        result = _ReferenceIndices(graph, context,
                                   torch.tensor(destinations, dtype=torch.long, device=device),
                                   torch.tensor(indices, dtype=torch.long, device=device))
    size = (result.indices.numel() + result.destinations.numel()) * 8 + 256
    return _REFERENCE_INDICES.put(key, result, size, sources=(graph, context))


@dataclass
class _EncoderLayout:
    graphs: tuple[Any, ...]
    contexts: tuple[tuple[Any, ...], ...]
    starts: tuple[int, ...]
    ids: Tensor
    offsets: Tensor
    types: Tensor
    numbers: Tensor
    sources: Tensor
    targets: Tensor
    relations: Tensor
    degree: Tensor
    owners: Tensor
    counts: Tensor
    external: tuple[tuple[int, int, Tensor], ...]


_ENCODER_LAYOUTS = _SourceCache(64 * 1024 * 1024, 256)


def _encoder_layout(graphs: Sequence[Any], external: Sequence[Sequence[_EncodedGraph]] | None,
                    device: torch.device, dtype: torch.dtype) -> _EncoderLayout:
    contexts = tuple(tuple(context.graph for context in row) for row in external) if external is not None else ()
    key = (tuple(map(id, graphs)), tuple(tuple(map(id, row)) for row in contexts), device, dtype)
    cached = _ENCODER_LAYOUTS.get(key)
    if cached is not None:
        return cached
    packs = [_graph_tensors(graph, device, dtype) for graph in graphs]
    starts, token_starts = [0], [0]
    for graph, pack in zip(graphs, packs, strict=True):
        starts.append(starts[-1] + graph.node_count)
        token_starts.append(token_starts[-1] + pack.tokens.numel())
    long = lambda values: torch.tensor(values, dtype=torch.long, device=device)
    cat = lambda values: values[0] if len(values) == 1 else torch.cat(values)
    node_count = starts[-1]
    # This is the original batching/edge order. Only constant preparation is
    # reused; every message, pooling and gradient operation remains unchanged.
    with torch.inference_mode(False):
        ids = cat([pack.tokens for pack in packs])
        offsets = (packs[0].offsets if len(packs) == 1 else
                   torch.cat([*(pack.offsets[:-1] + start for pack, start in zip(packs, token_starts)),
                              long([token_starts[-1]])]))
        types = cat([pack.types for pack in packs])
        numbers = cat([pack.numbers for pack in packs])
        sources = [pack.sources + start for pack, start in zip(packs, starts)]
        targets = [pack.targets + start for pack, start in zip(packs, starts)]
        relations = [pack.relations for pack in packs]
        external_count, external_indices = 0, []
        rows = enumerate(zip(graphs, contexts, strict=True)) if contexts else ()
        for row, (graph, registries) in rows:
            for column, context in enumerate(registries):
                match = _reference_indices(graph, context, device)
                count = match.indices.numel()
                if count:
                    external_indices.append((row, column, match.indices))
                    offset = node_count + external_count
                    sources.append(torch.arange(offset, offset + count, device=device))
                    targets.append(match.destinations + starts[row])
                    relations.append(torch.full((count,), EXTERNAL_REFERENCE, dtype=torch.long, device=device))
                    external_count += count
        source_ids, target_ids, relation_ids = cat(sources), cat(targets), cat(relations)
        degree = torch.bincount(target_ids, minlength=node_count).clamp_min(1).to(dtype).unsqueeze(1)
        owners = torch.repeat_interleave(torch.arange(len(graphs), device=device),
                                         long([graph.node_count for graph in graphs]))
        counts = torch.tensor([graph.node_count for graph in graphs], device=device, dtype=dtype).unsqueeze(1)
    result = _EncoderLayout(tuple(graphs), contexts, tuple(starts), ids, offsets, types, numbers,
                            source_ids, target_ids, relation_ids, degree, owners, counts, tuple(external_indices))
    size = sum(value.numel() * value.element_size() for value in vars(result).values() if isinstance(value, Tensor))
    size += sum(indices.numel() * indices.element_size() for _, _, indices in result.external)
    sources = (*graphs, *(graph for row in contexts for graph in row))
    return _ENCODER_LAYOUTS.put(key, result, size + 256 + 32 * (len(graphs) + len(contexts)), sources=sources)


@dataclass
class _FactorLevel:
    count: int
    parent_count: int
    owners: Tensor
    counts: Tensor
    parents: Tensor


_ACTION_FACTORS = _SourceCache(4 * 1024 * 1024, 4096)
_FACTOR_LAYOUTS = _SourceCache(8 * 1024 * 1024, 512)


def _factors_for_action(graph: Any, feature: dict) -> tuple[str, ...]:
    key = (id(graph),)
    cached = _ACTION_FACTORS.get(key)
    if cached is not None:
        return cached[1]
    factors = action_factors(feature)
    _ACTION_FACTORS.put(key, (graph, factors), 256 + sum(len(value.encode("utf-8")) for value in factors), sources=(graph,))
    return factors


def _factor_layout(factors: Sequence[tuple[str, ...]], device: torch.device,
                   dtype: torch.dtype) -> tuple[_FactorLevel, ...]:
    factors = tuple(factors)
    key = (factors, device, dtype)
    cached = _FACTOR_LAYOUTS.get(key)
    if cached is not None:
        return cached
    levels = []
    with torch.inference_mode(False):
        for level in range(1, 5):
            prefixes = sorted({factor[:level] for factor in factors})
            lookup = {prefix: index for index, prefix in enumerate(prefixes)}
            owners = torch.tensor([lookup[factor[:level]] for factor in factors], dtype=torch.long, device=device)
            counts = torch.bincount(owners, minlength=len(prefixes)).to(dtype).unsqueeze(1)
            parents = {prefix: index for index, prefix in enumerate(sorted({prefix[:-1] for prefix in prefixes}))}
            parent_ids = torch.tensor([parents[prefix[:-1]] for prefix in prefixes], dtype=torch.long, device=device)
            levels.append(_FactorLevel(len(prefixes), len(parents), owners, counts, parent_ids))
    result = tuple(levels)
    size = sum(value.numel() * value.element_size() for item in result for value in vars(item).values()
               if isinstance(value, Tensor))
    size += 512 + sum(64 + len(value.encode("utf-8")) for factor in factors for value in factor)
    return _FACTOR_LAYOUTS.put(key, result, size)


def _clear_static_after_load(module: nn.Module, incompatible_keys: Any) -> None:
    module.clear_inference_cache()


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

    def forward(self, graphs: Sequence[Any], external: Sequence[Sequence[_EncodedGraph]] | None = None) -> list[_EncodedGraph]:
        if not graphs:
            return []
        device, dtype = self.tokens.weight.device, self.tokens.weight.dtype
        layout = _encoder_layout(graphs, external, device, dtype)
        encoded = self.tokens(layout.ids, layout.offsets) + self.types(layout.types)
        encoded = self.input_norm(encoded + self.numbers(layout.numbers))
        # External vectors are always read from this forward's learned state.
        external_chunks = ([external[row][column].nodes.index_select(0, indices)
                            for row, column, indices in layout.external] if external is not None else [])
        external_nodes = torch.cat(external_chunks) if external_chunks else None
        for message, update in zip(self.messages, self.updates, strict=True):
            bank = torch.cat((encoded, external_nodes)) if external_nodes is not None else encoded
            gathered = bank.index_select(0, layout.sources) + self.relations(layout.relations)
            aggregate = torch.zeros_like(encoded)
            aggregate.index_add_(0, layout.targets, message(gathered))
            encoded = encoded + update(torch.cat((encoded, aggregate / layout.degree), dim=1))
        summed = encoded.new_zeros((len(graphs), encoded.shape[1]))
        summed.index_add_(0, layout.owners, encoded)
        maximum = encoded.new_full(summed.shape, -torch.inf)
        maximum.scatter_reduce_(0, layout.owners.unsqueeze(1).expand_as(encoded), encoded, reduce="amax", include_self=True)
        pooled = self.pool(torch.cat((summed / layout.counts, maximum, layout.counts.log1p()), dim=1))
        return [_EncodedGraph(graph, encoded[layout.starts[row]:layout.starts[row + 1]], pooled[row])
                for row, graph in enumerate(graphs)]


class CampaignPolicyValueNet(nn.Module):
    """Complete registry/state/action graph model with variable legal menus.

    Static token/topology preparation is reused. Training recomputes all learned
    embeddings; explicitly versioned frozen inference can reuse registry vectors.
    Within a batch a shared context is encoded once; its state-independent vectors
    are safely reused inside that autograd graph.
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
        self._static_contexts = _SourceCache(64 * 1024 * 1024, 8)
        self._static_signature: tuple | None = None
        self.register_load_state_dict_post_hook(_clear_static_after_load)

    def clear_inference_cache(self) -> None:
        self._static_contexts.clear()
        self._static_signature = None

    def _encode_contexts(self, contexts: Sequence[Any], model_version: str | None) -> list[_EncodedGraph]:
        # An ordinary no_grad forward is deliberately insufficient: the caller
        # must supply a frozen policy version, eval mode and inference mode.
        if model_version is None or self.training or not torch.is_inference_mode_enabled():
            return self.encoder(contexts)
        tensors = (*self.parameters(), *self.buffers())
        try:
            signature = (model_version, tuple((id(value), value._version, value.device, value.dtype)
                                              for value in tensors))
        except RuntimeError:
            # Inference tensors do not have version counters; do not guess at
            # whether a parameter created under inference_mode is unchanged.
            return self.encoder(contexts)
        if signature != self._static_signature:
            self.clear_inference_cache()
            self._static_signature = signature
        # Preserve the complete ordered context batch. Encoding a context alone
        # can select a different floating-point matrix kernel from the original
        # batch, so individual-context learned caches would weaken exact parity.
        key = (tuple(map(id, contexts)),)
        cached = self._static_contexts.get(key)
        if cached is not None:
            return cached
        result = self.encoder(contexts)
        size = sum((item.nodes.numel() + item.pooled.numel()) * item.nodes.element_size() for item in result)
        return self._static_contexts.put(key, result, size + 256 * len(result), sources=contexts)

    @staticmethod
    def _conditional_log_softmax(scores: Tensor, owners: Tensor, count: int) -> Tensor:
        maximum = scores.new_full((count,), -torch.inf)
        maximum.scatter_reduce_(0, owners, scores, reduce="amax", include_self=True)
        shifted = scores - maximum.index_select(0, owners)
        totals = scores.new_zeros((count,))
        totals.index_add_(0, owners, shifted.exp())
        return shifted - totals.log().index_select(0, owners)

    def _factored_logits(self, state: Tensor, latent: Tensor, scores: Tensor,
                         factors: Sequence[tuple[str, ...]]) -> Tensor:
        """Normalize family -> source/group -> path -> target -> exact action.

        These are neural conditional readouts of the same complete legal menu.
        No game action is inserted/reordered, no group is declared equivalent,
        and no leaf is pruned. All sibling scores are evaluated in batches.
        """
        levels = _factor_layout(factors, scores.device, latent.dtype)
        joint = torch.zeros_like(scores)
        for level, head in zip(levels, self.factor_heads, strict=True):
            means = latent.new_zeros((level.count, latent.shape[1]))
            means.index_add_(0, level.owners, latent)
            group_scores = head(torch.cat((state.expand(level.count, -1), means / level.counts), dim=1)).squeeze(1)
            conditional = self._conditional_log_softmax(group_scores, level.parents, level.parent_count)
            joint = joint + conditional.index_select(0, level.owners)
        return joint + self._conditional_log_softmax(scores, level.owners, level.count)

    def forward_batch(self, inputs: Sequence[dict[str, Any]], *,
                      model_version: str | None = None) -> tuple[list[Tensor], Tensor]:
        if not inputs:
            return [], self.value_head[-1].weight.new_empty((0, 3))
        contexts, context_rows, context_lookup = [], [], {}
        observations, action_graphs, action_rows, lengths, factors = [], [], [], [], []
        for row, item in enumerate(inputs):
            if item.get("schema") == NUMERIC_SCHEMA:
                if set(item) != {"schema", "owner", "context_key", "packed_graph"}:
                    raise ValueError("Unsupported campaign numerical input schema")
                packed = item["packed_graph"]
                if not isinstance(packed, dict) or set(packed) != {"context", "observation", "actions", "action_factors"}:
                    raise ValueError("Numerical inputs need complete context, observation, actions and factors")
                context_key = (NUMERIC_SCHEMA, item["context_key"])
                context, observation, menu = packed["context"], packed["observation"], packed["actions"]
                if any(getattr(graph, "token_buckets", self.config.token_buckets) != self.config.token_buckets
                       for graph in (context, observation, *menu)):
                    raise ValueError("Numerical graphs do not match the model's lexical vocabulary")
                row_factors = tuple(tuple(factor) for factor in packed["action_factors"])
                if len(row_factors) != len(menu) or any(len(factor) != 4 or any(not isinstance(value, str) for value in factor)
                                                       for factor in row_factors):
                    raise ValueError("Each numerical action needs its four exact policy factors")
            elif item.get("schema") == SCHEMA:
                if set(item) != {"schema", "observation", "context", "actions"}:
                    raise ValueError("Unsupported campaign neural input schema")
                if not isinstance(item["observation"], dict) or not isinstance(item["context"], dict) or not isinstance(item["actions"], list):
                    raise ValueError("Neural inputs need observation/context objects and an action list")
                context_key = (SCHEMA, canonical(item["context"]))
                context = cached_context(context_key[1], self.config.token_buckets)
                observation = cached_observation(canonical(item["observation"]), self.config.token_buckets)
                menu, row_factors = [], []
                for action in item["actions"]:
                    if not isinstance(action, dict):
                        raise ValueError("Each legal action needs a complete feature object")
                    graph = cached_action(canonical(action), self.config.token_buckets)
                    menu.append(graph)
                    row_factors.append(_factors_for_action(graph, action))
            else:
                raise ValueError("Unsupported campaign neural input schema")
            if context_key not in context_lookup:
                context_lookup[context_key] = len(contexts)
                contexts.append(context)
            context_rows.append(context_lookup[context_key])
            observations.append(observation)
            lengths.append(len(menu))
            factors.append(row_factors)
            for graph in menu:
                action_graphs.append(graph)
                action_rows.append(row)
        static = self._encode_contexts(contexts, model_version)
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
                                                       logits[row], factors[row])
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
        self._versioned_forward: dict[str, bool] = {}
        for player, model in self.models.items():
            try:
                parameters = inspect.signature(model.forward_batch).parameters.values()
                supported = any(parameter.kind == inspect.Parameter.VAR_KEYWORD or
                                (parameter.name == "model_version" and parameter.kind in
                                 {inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY})
                                for parameter in parameters)
            except (TypeError, ValueError):
                supported = False
            self._versioned_forward[player] = isinstance(model, CampaignPolicyValueNet) and supported

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
            prepared: dict[int | None, dict] = {}

            def input_for(player: str) -> dict:
                model = self.models[player]
                buckets = model.config.token_buckets if self._versioned_forward[player] else None
                if buckets not in prepared:
                    if buckets is None:
                        prepared[buckets] = make_input(env, actions)
                    else:
                        # Portable environments and old replays retain the raw
                        # fallback. Distinct actor vocabularies stay independent.
                        try:
                            from .features import make_numeric_input
                        except ImportError:
                            prepared[buckets] = make_input(env, actions)
                        else:
                            prepared[buckets] = make_numeric_input(env, actions, buckets)
                return prepared[buckets]
            if actor is None:
                if env.decision_kind() != "chance" or actions:
                    raise ValueError("An ownerless nonterminal evaluation must be a chance cutoff")
                chance_values[row] = []
                for player in PLAYERS:
                    groups[player].append((row, input_for(player)))
            elif actor in PLAYERS:
                groups[actor].append((row, input_for(actor)))
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
                    batch = [item for _, item in groups[player]]
                    if self._versioned_forward[player]:
                        logits, values = model.forward_batch(batch, model_version=self.version)
                    else:
                        logits, values = model.forward_batch(batch)
                    if values.shape != (len(groups[player]), 3) or len(logits) != len(groups[player]):
                        raise ValueError("Neural model returned an invalid batch shape")
                    for index, (row, item) in enumerate(groups[player]):
                        scores = logits[index]
                        count = len(item["packed_graph"]["actions"]) if item["schema"] == NUMERIC_SCHEMA else len(item["actions"])
                        if scores.shape != (count,) or not torch.isfinite(scores).all():
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
