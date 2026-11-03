"""Campaign policy/value network over the fixed zone encoding, and batched evaluation.

The network reads the engine's zone encoding (features.py). Each of the map's
37 zones answers fixed questions; their answers, the zone's fixed map facts and
a learned vector for the zone itself make one vector per zone. Messages then
pass along the map's 160 directed borders, while a position vector built from
the position's own answers reads every zone and is read by every zone. The
value head reads the position vector and the zones' mean and maximum. Each
legal option is a vector built from its own answers and the vectors of the
zones it acts from, travels through and acts on; the policy scores every option
of the legal menu, nothing padded and nothing dropped.

An answer adds its column's learned vector, weighted by sign(a) * log(1 + |a|).
Every column has its own vector: a column means one thing in every position.

Values returned by the network are in raw-return/value_scale units. The linear
three-component head is unbounded; NeuralEvaluator multiplies by value_scale
before handing predictions to MCTS. The default scale is 100 IPP wealth units.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
import torch
import torch.nn.functional as F
from torch import Tensor, nn

from studies.shared.multiplayer_mcts import Evaluation, PLAYERS, vector
from .features import GROUP_LEVELS, ZoneBatch, ZoneSpec, default_zone_spec, make_zone_input, pack_zone_inputs


def _require_no_mps_fallback() -> None:
    if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK", "0") not in {"", "0"}:
        raise ValueError("MPS execution requires PYTORCH_ENABLE_MPS_FALLBACK=0; CPU fallback is not allowed")


def resolve_neural_device(device: str | torch.device = "cpu") -> torch.device:
    """Validate an explicit target without choosing a different available device."""
    if not isinstance(device, (str, torch.device)):
        raise ValueError("Neural device must be cpu, mps or cuda[:index]")
    try:
        target = torch.device(device)
    except (RuntimeError, ValueError) as error:
        raise ValueError("Neural device must be cpu, mps or cuda[:index]") from error
    if target.type == "cpu":
        if target.index not in (None, 0):
            raise ValueError("CPU neural execution has no indexed accelerator")
        return torch.device("cpu")
    if target.type == "mps":
        if target.index not in (None, 0) or not torch.backends.mps.is_available():
            raise ValueError("The requested MPS neural device is unavailable")
        _require_no_mps_fallback()
        return torch.device("mps")
    if target.type == "cuda":
        if not torch.cuda.is_available():
            raise ValueError("The requested CUDA neural device is unavailable")
        index = torch.cuda.current_device() if target.index is None else target.index
        if not 0 <= index < torch.cuda.device_count():
            raise ValueError("The requested CUDA neural device index is unavailable")
        return torch.device("cuda", index)
    raise ValueError("Neural device must be cpu, mps or cuda[:index]")


def synchronize_neural_device(device: str | torch.device = "cpu") -> None:
    """Wait for queued accelerator work at explicit timing/checkpoint boundaries."""
    target = resolve_neural_device(device)
    if target.type == "mps":
        torch.mps.synchronize()
    elif target.type == "cuda":
        torch.cuda.synchronize(target)


def neural_device_memory(device: str | torch.device = "cpu") -> dict[str, Any]:
    """Allocator diagnostics, additional to the experiment's process-tree guard.

    MPS driver allocation includes cached/workspace allocations beyond live
    tensors. Its recommended maximum is a hardware recommendation, not the
    user's memory allowance. CPU memory remains measured by the outer guard.
    """
    target = resolve_neural_device(device)
    result: dict[str, Any] = {"device": str(target), "allocated_bytes": None,
                              "driver_allocated_bytes": None, "reserved_bytes": None,
                              "recommended_max_bytes": None}
    if target.type == "mps":
        result.update(allocated_bytes=int(torch.mps.current_allocated_memory()),
                      driver_allocated_bytes=int(torch.mps.driver_allocated_memory()),
                      recommended_max_bytes=int(torch.mps.recommended_max_memory()))
    elif target.type == "cuda":
        result.update(allocated_bytes=int(torch.cuda.memory_allocated(target)),
                      reserved_bytes=int(torch.cuda.memory_reserved(target)))
    return result


def release_device_memory(device: str | torch.device) -> None:
    """Explicit cold-benchmark cleanup: return cached accelerator memory."""
    target = resolve_neural_device(device)
    synchronize_neural_device(target)
    if target.type == "mps":
        torch.mps.empty_cache()
    elif target.type == "cuda":
        with torch.cuda.device(target):
            torch.cuda.empty_cache()


@dataclass(frozen=True)
class CampaignModelConfig:
    hidden_dim: int = 64
    message_layers: int = 2
    value_scale: float = 100.0
    policy_factorization: bool = True

    def __post_init__(self) -> None:
        if type(self.hidden_dim) is not int or self.hidden_dim < 4:
            raise ValueError("hidden_dim must be at least four")
        if type(self.message_layers) is not int or self.message_layers < 1:
            raise ValueError("message_layers must be positive")
        if not math.isfinite(self.value_scale) or self.value_scale <= 0:
            raise ValueError("value_scale must be positive and finite")
        if type(self.policy_factorization) is not bool:
            raise ValueError("policy_factorization must be a boolean")


def batch_tensors(batch: ZoneBatch, device: torch.device, *, non_blocking: bool = False) -> dict[str, Tensor]:
    """The batch's arrays as tensors on `device`.

    Off the CPU every index array travels in one copy and every weight array in
    another: each separate host-to-device copy costs a fixed overhead, larger
    than moving the data. A non-blocking copy may still be reading its host
    buffer when this returns; the buffers stay referenced by the batch, so a
    caller asking for one must keep the batch until it has read the outputs.
    """
    if device.type == "cpu":
        return {name: torch.from_numpy(values) for parts in (batch.integers, batch.floats)
                for name, values in parts.items()}
    out: dict[str, Tensor] = {}
    hosts = []
    for parts, dtype in ((batch.integers, np.int64), (batch.floats, np.float32)):
        if not parts:
            continue
        host = torch.from_numpy(np.concatenate([values.ravel() for values in parts.values()]).astype(dtype, copy=False))
        hosts.append(host)
        joined = host.to(device, non_blocking=non_blocking)
        offset = 0
        for name, values in parts.items():
            out[name] = joined[offset:offset + values.size].view(values.shape)
            offset += values.size
    batch.host_buffers = hosts
    return out


def _conditional_log_softmax(scores: Tensor, owners: Tensor, count: int) -> Tensor:
    """Log-softmax of each score among the scores sharing its owner."""
    maximum = scores.new_full((count,), -torch.inf)
    maximum.scatter_reduce_(0, owners, scores, reduce="amax", include_self=True)
    shifted = scores - maximum.index_select(0, owners)
    totals = scores.new_zeros((count,))
    totals.index_add_(0, owners, shifted.exp())
    return shifted - totals.log().index_select(0, owners)


def _bag(table: Tensor, columns: Tensor, weights: Tensor, rows: Tensor, count: int) -> Tensor:
    """Sum of weighted column vectors per row: one vector per zone, position or option."""
    vectors = table.index_select(0, columns) * weights.unsqueeze(1)
    return vectors.new_zeros((count, table.shape[1])).index_add_(0, rows, vectors)


def _block(inputs: int, dim: int) -> nn.Sequential:
    return nn.Sequential(nn.Linear(inputs, dim), nn.GELU(), nn.LayerNorm(dim))


def _head(inputs: int, dim: int, outputs: int) -> nn.Sequential:
    return nn.Sequential(nn.Linear(inputs, dim), nn.GELU(), nn.Linear(dim, outputs))


class CampaignPolicyValueNet(nn.Module):
    """Zone-graph policy/value network for one alliance.

    `spec` is the zone layout the inputs must carry; by default the campaign
    scenario's. The layout's fixed map facts and borders are buffers outside the
    state dict: the layout version identifies them, and inputs of another
    layout are refused.
    """

    def __init__(self, config: CampaignModelConfig, *, spec: ZoneSpec | None = None,
                 device: str | torch.device = "cpu") -> None:
        super().__init__()
        target = resolve_neural_device(device)
        spec = default_zone_spec() if spec is None else spec
        self.config, self.spec = config, spec
        dim, layers, zones = config.hidden_dim, config.message_layers, len(spec.zones)
        # Identical CPU initialization keeps matched CPU/GPU experiments on the
        # same initial parameters and consumes the same CPU RNG sequence.
        with torch.device("cpu"):
            self.zone_columns = nn.Embedding(spec.zone_columns, dim)
            self.global_columns = nn.Embedding(spec.global_columns, dim)
            self.option_columns = nn.Embedding(spec.action_columns, dim)
            # A row adds in only where its question is answered, so one that
            # training has not yet reached starts at zero and adds nothing.
            for table in (self.zone_columns, self.global_columns, self.option_columns):
                nn.init.zeros_(table.weight)
            self.zone_identity = nn.Embedding(zones, dim)
            self.map_facts = nn.Linear(spec.zone_static.shape[1], dim)
            self.zone_norm, self.global_norm, self.option_norm = nn.LayerNorm(dim), nn.LayerNorm(dim), nn.LayerNorm(dim)
            self.messages = nn.ModuleList(nn.Linear(dim, dim) for _ in range(layers))
            self.border_facts = nn.ModuleList(nn.Linear(spec.edge_static.shape[1], dim) for _ in range(layers))
            self.zone_updates = nn.ModuleList(_block(dim * 3, dim) for _ in range(layers))
            self.position_updates = nn.ModuleList(_block(dim * 2, dim) for _ in range(layers))
            self.state_encoder = _block(dim * 3, dim)
            self.no_zone = nn.Parameter(torch.zeros(dim))
            self.option_encoder = _block(dim * 4, dim)
            self.policy_head = _head(dim * 2, dim, 1)
            self.factor_heads = nn.ModuleList(_head(dim * 2, dim, 1) for _ in range(GROUP_LEVELS))
            self.value_head = _head(dim, dim, 3)
        degree = np.maximum(np.bincount(spec.edge_target, minlength=zones), 1).astype(np.float32)[:, None]
        for name, values in (("zone_static", spec.zone_static), ("edge_source", spec.edge_source),
                             ("edge_target", spec.edge_target), ("edge_static", spec.edge_static),
                             ("in_degree", degree)):
            self.register_buffer(name, torch.from_numpy(np.array(values)), persistent=False)
        self.to(target)

    @property
    def layout_version(self) -> str:
        return self.spec.version

    def forward_batch(self, inputs: Sequence[Any]) -> tuple[list[Tensor], Tensor]:
        """Logits for every listed option of each input, and its three values."""
        if not inputs:
            return [], self.value_head[-1].weight.new_empty((0, 3))
        batch = pack_zone_inputs(inputs, self.spec)
        scores, values = self.forward_packed(batch)
        return list(scores.split(batch.option_counts)), values

    def forward(self, inputs: Sequence[Any]) -> tuple[list[Tensor], Tensor]:
        return self.forward_batch(inputs)

    def forward_packed(self, batch: ZoneBatch, *, non_blocking: bool = False) -> tuple[Tensor, Tensor]:
        """Every listed option's logit, in position order, and each position's values.

        The pass for decisions already laid out by features.pack_zone_arrays.
        With non_blocking, keep `batch` until the outputs are read (batch_tensors).
        """
        device = self.value_head[-1].weight.device
        if device.type == "mps":
            # Also covers callers using the normal PyTorch model.to('mps') API.
            _require_no_mps_fallback()
        t = batch_tensors(batch, device, non_blocking=non_blocking)
        positions, zones, dim = batch.positions, batch.zones, self.config.hidden_dim
        nodes = positions * zones
        local = _bag(self.zone_columns.weight, t["zone_column"], t["zone_weight"], t["zone_rows"], nodes)
        local = local.view(positions, zones, dim) + self.zone_identity.weight + self.map_facts(self.zone_static)
        h = self.zone_norm(local).reshape(nodes, dim)
        u = self.global_norm(_bag(self.global_columns.weight, t["global_column"], t["global_weight"],
                                  t["global_rows"], positions))
        shift = torch.arange(positions, device=device).repeat_interleave(len(self.edge_source)) * zones
        sources, targets = self.edge_source.repeat(positions) + shift, self.edge_target.repeat(positions) + shift
        degree = self.in_degree.repeat(positions, 1)
        for message, border, zone_update, position_update in zip(
                self.messages, self.border_facts, self.zone_updates, self.position_updates, strict=True):
            sent = F.gelu(message(h).index_select(0, sources) + border(self.edge_static).repeat(positions, 1))
            received = h.new_zeros((nodes, dim)).index_add_(0, targets, sent) / degree
            h = h + zone_update(torch.cat((h, received, u.repeat_interleave(zones, 0)), dim=1))
            u = u + position_update(torch.cat((u, h.view(positions, zones, dim).mean(1)), dim=1))
        grid = h.view(positions, zones, dim)
        states = self.state_encoder(torch.cat((u, grid.mean(1), grid.amax(1)), dim=1))
        values = self.value_head(states)  # Unbounded, in raw-value/value_scale units.
        if not batch.options:
            return values.new_empty((0,)), values
        options = self.option_norm(_bag(self.option_columns.weight, t["action_column"], t["action_weight"],
                                        t["action_rows"], batch.options))
        bank = torch.cat((h, self.no_zone.unsqueeze(0)))
        path = h.new_zeros((batch.options, dim)).index_add_(
            0, t["path_option"], bank.index_select(0, t["path_zone"])) * t["path_scale"]
        latent = self.option_encoder(torch.cat((options, bank.index_select(0, t["action_source"]),
                                                bank.index_select(0, t["action_target"]), path), dim=1))
        scores = self.policy_head(torch.cat((states.index_select(0, t["action_position"]), latent), dim=1)).squeeze(1)
        if self.config.policy_factorization:
            scores = self._factored(states, latent, scores, t, batch)
        return scores, values

    def _factored(self, states: Tensor, latent: Tensor, scores: Tensor, t: dict[str, Tensor],
                  batch: ZoneBatch) -> Tensor:
        """Normalize kind -> what acts -> how it travels -> what it acts on -> exact option.

        These are neural conditional readouts of the same complete legal menu.
        No option is inserted, reordered, merged or pruned; each level scores
        a group from the mean vector of its options.
        """
        joint = torch.zeros_like(scores)
        parents = batch.positions
        for level, head in enumerate(self.factor_heads):
            owners, count = t[f"group{level}_owners"], batch.group_counts[level]
            means = latent.new_zeros((count, latent.shape[1])).index_add_(0, owners, latent) / t[f"group{level}_counts"]
            group_scores = head(torch.cat((states.index_select(0, t[f"group{level}_rows"]), means), dim=1)).squeeze(1)
            joint = joint + _conditional_log_softmax(group_scores, t[f"group{level}_parents"], parents).index_select(0, owners)
            parents = count
        return joint + _conditional_log_softmax(scores, t[f"group{GROUP_LEVELS - 1}_owners"], parents)


def _gpu_evaluation_outputs(logits: Sequence[Tensor], values: Tensor, counts: Sequence[int],
                            value_scale: float) -> tuple[list[list[float]], list[tuple[float, float, float]]]:
    """Validate accelerator rows, then cross the host boundary twice per actor.

    Keep each row's original softmax operation and every legal action. Packing
    only consolidates finite checking and device-to-host copies; no padding,
    truncation, policy normalization or owner/chance routing changes.
    """
    if values.shape != (len(counts), 3) or len(logits) != len(counts):
        raise ValueError("Neural model returned an invalid batch shape")
    for scores, count in zip(logits, counts, strict=True):
        if scores.shape != (count,) or scores.device != values.device:
            raise ValueError("Neural policy must contain one device-local logit per legal action")
    if not counts:
        return [], []
    packed_scores = logits[0] if len(logits) == 1 else torch.cat(tuple(logits))
    if packed_scores.numel() and not torch.isfinite(packed_scores).all():
        raise ValueError("Neural policy must contain one finite logit per legal action")
    row_probabilities = [scores.softmax(0) if scores.numel() else scores for scores in logits]
    packed_probabilities = (row_probabilities[0] if len(row_probabilities) == 1
                            else torch.cat(row_probabilities))
    host_probabilities = packed_probabilities.cpu().tolist()
    host_values = [vector(row) for row in (values * value_scale).cpu().tolist()]
    probabilities, offset = [], 0
    for count in counts:
        probabilities.append(host_probabilities[offset:offset + count])
        offset += count
    return probabilities, host_values


class NeuralEvaluator:
    """Route each entitled actor to its model, retaining raw vector returns.

    A chance cutoff has no entitled actor: it deterministically averages the
    three models' raw value vectors and emits no policy. This is a bootstrap
    convention, not a chance action or a peek at the execution random stream.
    """
    def __init__(self, models: Mapping[str, CampaignPolicyValueNet], version: str, *, runtime_policy: Any = None) -> None:
        if set(models) != set(PLAYERS):
            raise ValueError("Provide one campaign model for Axis, Allies and Comintern")
        if not isinstance(version, str) or not version:
            raise ValueError("Neural evaluator needs a nonempty version")
        self.models, self.version = dict(models), version
        self.runtime_policy = runtime_policy

    @property
    def concurrent_evaluation(self) -> bool:
        """CPU models may be evaluated from several search threads at once."""
        return all(parameter.device.type == "cpu" for model in self.models.values()
                   for parameter in model.parameters())

    def evaluate(self, env: Any, actions: Sequence[Any]) -> Evaluation:
        return self.evaluate_batch([(env, actions)])[0]

    def evaluate_batch(self, requests: Sequence[tuple[Any, Sequence[Any]]]) -> list[Evaluation]:
        results: list[Evaluation | None] = [None] * len(requests)
        groups: dict[str, list[tuple[int, Any]]] = {player: [] for player in PLAYERS}
        chance_values: dict[int, list[tuple[float, float, float]]] = {}
        for row, (env, actions) in enumerate(requests):
            if env.is_terminal():
                if actions:
                    raise ValueError("A terminal state cannot have policy actions")
                results[row] = Evaluation([], vector(env.returns()))
                continue
            actor = env.current_decision_player()
            if actor is None:
                if env.decision_kind() != "chance" or actions:
                    raise ValueError("An ownerless nonterminal evaluation must be a chance cutoff")
                item = make_zone_input(env, ())
                chance_values[row] = []
                for player in PLAYERS:
                    groups[player].append((row, item))
            elif actor in PLAYERS:
                groups[actor].append((row, make_zone_input(env, actions)))
            else:
                raise ValueError(f"Unknown campaign decision player: {actor}")
        for player in PLAYERS:
            if not groups[player]:
                continue
            model = self.models[player]
            training = model.training
            model.eval()
            completed_mps_forward = False
            try:
                with torch.inference_mode():
                    batch = [item for _, item in groups[player]]
                    logits, values = model.forward_batch(batch)
                    if values.shape != (len(batch), 3) or len(logits) != len(batch):
                        raise ValueError("Neural model returned an invalid batch shape")
                    counts = [item.action_count for item in batch]
                    if values.device.type != "cpu":
                        host_priors, host_values = _gpu_evaluation_outputs(logits, values, counts, model.config.value_scale)
                        for index, (row, _) in enumerate(groups[player]):
                            if row in chance_values:
                                chance_values[row].append(host_values[index])
                            else:
                                results[row] = Evaluation(host_priors[index], host_values[index])
                        completed_mps_forward = values.device.type == "mps"
                        continue  # The finally still restores model.train(training).
                    for index, (row, _) in enumerate(groups[player]):
                        scores = logits[index]
                        if scores.shape != (counts[index],) or not torch.isfinite(scores).all():
                            raise ValueError("Neural policy must contain one finite logit per legal action")
                        raw = vector((values[index] * model.config.value_scale).tolist())
                        if row in chance_values:
                            chance_values[row].append(raw)
                        else:
                            results[row] = Evaluation(scores.softmax(0).tolist() if scores.numel() else [], raw)
            finally:
                model.train(training)
                if completed_mps_forward and self.runtime_policy is not None:
                    self.runtime_policy.completed(1)
        for row, predictions in chance_values.items():
            results[row] = Evaluation([], vector([sum(value[i] for value in predictions) / len(PLAYERS) for i in range(3)]))
        if any(result is None for result in results):
            raise RuntimeError("A neural batch request was not evaluated")
        return [result for result in results if result is not None]
