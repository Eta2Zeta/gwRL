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
from typing import Any, Callable, Mapping, Sequence

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
    exponentials = shifted.exp()  # 32-bit even under automatic mixed precision
    totals = exponentials.new_zeros((count,))
    totals.index_add_(0, owners, exponentials)
    return shifted - totals.log().index_select(0, owners)


def _bag(table: Tensor, columns: Tensor, weights: Tensor, bags: Tensor) -> Tensor:
    """Sum of weighted column vectors per bag: one vector per zone, position or option.

    Bag i adds the rows of columns[bags[i]:bags[i + 1]], each times its weight;
    an empty bag is zero. One fused lookup, without first gathering every
    answer's row into a temporary array (measured in
    docs/archive/records/coordinator_lookups_2026_11_12.md).
    """
    return F.embedding_bag(columns, table, bags, mode="sum", per_sample_weights=weights.to(table.dtype),
                           include_last_offset=True)


def _block(inputs: int, dim: int) -> nn.Sequential:
    return nn.Sequential(nn.Linear(inputs, dim), nn.GELU(), nn.LayerNorm(dim))


def _head(inputs: int, dim: int, outputs: int) -> nn.Sequential:
    return nn.Sequential(nn.Linear(inputs, dim), nn.GELU(), nn.Linear(dim, outputs))


# The layers above, applied with their own parameters as their modules apply them,
# without a module call's own cost.
def _linear(layer: nn.Linear, x: Tensor) -> Tensor:
    return F.linear(x, layer.weight, layer.bias)


def _norm(layer: nn.LayerNorm, x: Tensor) -> Tensor:
    return F.layer_norm(x, layer.normalized_shape, layer.weight, layer.bias, layer.eps)


def _apply_block(block: nn.Sequential, x: Tensor) -> Tensor:
    return _norm(block[2], F.gelu(_linear(block[0], x)))


def _apply_head(head: nn.Sequential, x: Tensor) -> Tensor:
    return _linear(head[2], F.gelu(_linear(head[0], x)))


def _by_network(x: Tensor, sizes: Sequence[int], layers: Sequence[Any],
                apply: Callable[[Any, Tensor], Tensor]) -> Tensor:
    """apply(layer, rows) for each network's own rows of x, which come in network order:
    sizes[i] rows for layers[i]."""
    parts = [(layer, size) for layer, size in zip(layers, sizes, strict=True) if size]
    if len(parts) <= 1:
        return apply(parts[0][0] if parts else layers[0], x)
    return torch.cat([apply(layer, rows) for (layer, _), rows in zip(parts, x.split([size for _, size in parts]))])


_APPLY = {"linear": _linear, "norm": _norm, "block": _apply_block, "head": _apply_head}


@dataclass(frozen=True)
class _GroupedLayers:
    """One kind of layer of several networks, stacked for grouped matrix products.

    `first` and `second` are the linear layers' weights, transposed as
    torch._grouped_mm reads them: groups x inputs x outputs. Each bias is an extra
    input, which a column of ones multiplies (_GROUP_PAD columns, the rest zeros,
    since the product needs rows of a multiple of 16 bytes), and the outputs are
    padded with zeros to a multiple of _GROUP_PAD; `outputs` is the second layer's
    true number. `scale` and `shift` are the layer normalization's, one row per
    group.
    """
    first: Tensor | None = None
    second: Tensor | None = None
    outputs: int = 0
    scale: Tensor | None = None
    shift: Tensor | None = None
    eps: float = 1e-5


_GROUP_PAD = 4  # Four 32-bit numbers: torch._grouped_mm needs strides of a multiple of 16 bytes.


def _with_bias(layer: nn.Linear) -> Tensor:
    """The layer's weights, its bias as one more input and zeros to pad inputs and outputs."""
    outputs, inputs = layer.weight.shape
    padded = layer.weight.new_zeros((-(-outputs // _GROUP_PAD) * _GROUP_PAD, inputs + _GROUP_PAD))
    padded[:outputs, :inputs] = layer.weight
    padded[:outputs, inputs] = layer.bias
    return padded


def _stack_layers(layers: Sequence[Any], kind: str) -> _GroupedLayers:
    def linear(index: int) -> Tensor:
        return torch.stack([_with_bias(layer if index < 0 else layer[index]) for layer in layers]).transpose(1, 2)

    def norm(pick: Callable[[Any], nn.LayerNorm]) -> dict[str, Any]:
        norms = [pick(layer) for layer in layers]
        return {"scale": torch.stack([n.weight for n in norms]), "shift": torch.stack([n.bias for n in norms]),
                "eps": norms[0].eps}

    if kind == "linear":
        return _GroupedLayers(first=linear(-1))
    if kind == "norm":
        return _GroupedLayers(**norm(lambda layer: layer))
    if kind == "block":
        return _GroupedLayers(first=linear(0), **norm(lambda block: block[2]))
    return _GroupedLayers(first=linear(0), second=linear(2), outputs=layers[0][2].out_features)  # A head.


def _grouped_here(x: Tensor) -> bool:
    """Grouped matrix products pay on the CPU, for inference; on the Mac's GPU they were slower."""
    return _GROUPED_MM and x.device.type == "cpu" and not torch.is_grad_enabled()


_GROUPED_MM = hasattr(torch, "_grouped_mm")


def _per_network(networks: Any, key: tuple, parts: Tensor | tuple[Tensor, ...], sizes: Sequence[int],
                 layers: Sequence[Any], kind: str) -> Tensor:
    """Each layer, of `kind` linear, norm, block or head, on its own rows of the parts
    joined side by side; rows come in layer order, sizes[i] for layers[i].

    Where it can (a network stack, on the CPU, without gradients, with rows for
    more than one layer), each step is one call for every layer at once: a grouped
    matrix product (torch._grouped_mm, which multiplies each group of rows by its
    own matrix), with each bias as a column of ones joined to the input, and one
    layer normalization whose scale and shift are then each row's own. Otherwise
    each layer is applied to its own rows in turn (_by_network). Both give the
    same outputs up to floating-point rounding.
    """
    parts = parts if isinstance(parts, tuple) else (parts,)
    if (not hasattr(networks, "stacked_layers") or sum(1 for size in sizes if size) < 2
            or not _grouped_here(parts[0]) or sum(part.shape[1] for part in parts) % _GROUP_PAD):
        x = parts[0] if len(parts) == 1 else torch.cat(parts, dim=1)
        return _by_network(x, sizes, layers, _APPLY[kind])
    stacked, sizes = networks.stacked_layers(key, layers, kind), tuple(sizes)
    rows = sum(sizes)
    if kind == "norm":
        x = parts[0] if len(parts) == 1 else torch.cat(parts, dim=1)
        return networks.scale_and_shift(F.layer_norm(x, (x.shape[1],), eps=stacked.eps), stacked, sizes)
    offsets = networks.offsets(sizes)
    y = torch._grouped_mm(torch.cat((*parts, networks.ones(rows)), dim=1), stacked.first, offs=offsets)
    if kind == "linear":
        return y
    y = F.gelu(y)
    if kind == "block":
        return networks.scale_and_shift(F.layer_norm(y, (y.shape[1],), eps=stacked.eps), stacked, sizes)
    y = torch._grouped_mm(torch.cat((y, networks.ones(rows)), dim=1), stacked.second, offs=offsets)
    return y if y.shape[1] == stacked.outputs else y[:, :stacked.outputs]


def _border_indices(spec_sources: Tensor, spec_targets: Tensor, in_degree: Tensor, positions: int,
                    zones: int) -> tuple[Tensor, Tensor, Tensor]:
    """Every position's borders as rows of the batch's zone vectors, and each zone's in-degree."""
    shift = torch.arange(positions, device=spec_sources.device).repeat_interleave(len(spec_sources)) * zones
    return spec_sources.repeat(positions) + shift, spec_targets.repeat(positions) + shift, in_degree.repeat(positions, 1)


class _OneNetwork:
    """A pass's view of one network: its own tables and fixed terms, worked out for
    this pass, so that training reaches every parameter."""

    def __init__(self, model: "CampaignPolicyValueNet") -> None:
        self.models = (model,)
        self.zone_table = model.zone_columns.weight
        self.global_table = model.global_columns.weight
        self.option_table = model.option_columns.weight
        self.no_zone = model.no_zone.unsqueeze(0)

    def zone_terms(self, batch: ZoneBatch, t: dict[str, Tensor]) -> tuple[Tensor, Tensor]:
        model = self.models[0]
        return model.zone_identity.weight, _linear(model.map_facts, model.zone_static)

    def border_terms(self, layer: int, batch: ZoneBatch, t: dict[str, Tensor]) -> Tensor:
        model = self.models[0]
        return _linear(model.border_facts[layer], model.edge_static).repeat(batch.positions, 1)

    def borders(self, positions: int, zones: int) -> tuple[Tensor, Tensor, Tensor]:
        model = self.models[0]
        return _border_indices(model.edge_source, model.edge_target, model.in_degree, positions, zones)


class NetworkStack:
    """Several networks of one layout evaluated in one pass, each on its own decisions.

    A pass costs much more than its share of arithmetic: about as much again as
    a few positions, whatever its size (measured in
    docs/archive/records/coordinator_one_pass_2026_11_14.md). The coordinator
    therefore evaluates the three alliances' positions together
    (studies/campaign/shared_evaluator.py).
    Each network's answers read its own rows of the networks' tables, laid end
    to end, and each of its layers reads only its own decisions' rows, so every
    output is the network's own, up to floating-point rounding.

    The stack reads the networks' weights once, when it is built, and is for
    inference only; build a new one after the weights change.
    """

    def __init__(self, models: Sequence["CampaignPolicyValueNet"]) -> None:
        models = tuple(models)
        if not models:
            raise ValueError("A network stack needs at least one network")
        first = models[0]
        for model in models[1:]:
            if model.config != first.config or model.layout_version != first.layout_version:
                raise ValueError("Stacked networks must share their configuration and input layout")
        self.models, self.spec, self.config = models, first.spec, first.config
        with torch.inference_mode():
            self.zone_table = torch.cat([model.zone_columns.weight for model in models])
            self.global_table = torch.cat([model.global_columns.weight for model in models])
            self.option_table = torch.cat([model.option_columns.weight for model in models])
            self.no_zone = torch.stack([model.no_zone for model in models])
            self.identity = torch.stack([model.zone_identity.weight for model in models])
            self.facts = torch.stack([_linear(model.map_facts, model.zone_static) for model in models])
            self.border = [torch.stack([_linear(model.border_facts[layer], model.edge_static) for model in models])
                           for layer in range(first.config.message_layers)]
        self._borders: dict[int, tuple[Tensor, Tensor, Tensor]] = {}
        self._repeated: dict[tuple[int, int, int], Tensor] = {}
        # For grouped matrix products (_per_network): each kind of layer's weights,
        # stacked once like the tables, and small tensors that depend only on how
        # many rows each network has, kept for the passes that repeat them.
        self._stacked: dict[tuple, _GroupedLayers] = {}
        self._offsets: dict[tuple[int, ...], Tensor] = {}
        self._row_layers: dict[tuple[int, ...], Tensor] = {}
        self._ones: dict[int, Tensor] = {}

    def stacked_layers(self, key: tuple, layers: Sequence[Any], kind: str) -> _GroupedLayers:
        found = self._stacked.get(key)
        if found is None:
            with torch.inference_mode():
                found = self._stacked[key] = _stack_layers(layers, kind)
        return found

    def offsets(self, sizes: tuple[int, ...]) -> Tensor:
        """Where each group's rows end, as torch._grouped_mm reads them."""
        found = self._offsets.get(sizes)
        if found is None:
            if len(self._offsets) > 4096:
                self._offsets.clear()
            found = self._offsets[sizes] = torch.tensor(np.cumsum(sizes), dtype=torch.int32)
        return found

    def ones(self, rows: int) -> Tensor:
        """A column of ones, the input that each linear layer's bias multiplies, and zeros to pad it."""
        found = self._ones.get(rows)
        if found is None:
            if len(self._ones) > 4096:
                self._ones.clear()
            found = self._ones[rows] = torch.zeros((rows, _GROUP_PAD))
            found[:, 0] = 1.0
        return found

    def scale_and_shift(self, normed: Tensor, stacked: _GroupedLayers, sizes: tuple[int, ...]) -> Tensor:
        """Each row's own layer normalization scale and shift, after normalizing all rows at once."""
        rows = self._row_layers.get(sizes)
        if rows is None:
            if len(self._row_layers) > 4096:
                self._row_layers.clear()
            rows = self._row_layers[sizes] = torch.repeat_interleave(torch.arange(len(sizes)), torch.tensor(sizes))
        return torch.addcmul(stacked.shift.index_select(0, rows), normed, stacked.scale.index_select(0, rows))

    def _single(self, batch: ZoneBatch) -> int | None:
        present = [index for index, size in enumerate(batch.network_positions) if size]
        return present[0] if len(present) == 1 else None

    def zone_terms(self, batch: ZoneBatch, t: dict[str, Tensor]) -> tuple[Tensor, Tensor]:
        single = self._single(batch)
        if single is not None:
            return self.identity[single], self.facts[single]
        network = t["position_network"]
        return self.identity.index_select(0, network), self.facts.index_select(0, network)

    def border_terms(self, layer: int, batch: ZoneBatch, t: dict[str, Tensor]) -> Tensor:
        single, positions = self._single(batch), batch.positions
        if single is None:
            return self.border[layer].index_select(0, t["position_network"]).view(-1, self.config.hidden_dim)
        key = (layer, single, positions)
        repeated = self._repeated.get(key)
        if repeated is None:
            if len(self._repeated) >= 64:  # A few megabytes at most.
                self._repeated.clear()
            repeated = self._repeated[key] = self.border[layer][single].repeat(positions, 1)
        return repeated

    def borders(self, positions: int, zones: int) -> tuple[Tensor, Tensor, Tensor]:
        found = self._borders.get(positions)
        if found is None:
            if len(self._borders) > 256:
                self._borders.clear()
            model = self.models[0]
            found = self._borders[positions] = _border_indices(model.edge_source, model.edge_target,
                                                               model.in_degree, positions, zones)
        return found

    def forward_packed(self, batch: ZoneBatch, *, non_blocking: bool = False) -> tuple[Tensor, Tensor]:
        """Every listed option's logit, in position order, and each position's values,
        for decisions packed with features.pack_zone_arrays(..., network_positions)."""
        if len(batch.network_positions) != len(self.models):
            raise ValueError("The batch names a different number of networks")
        return _forward(self, batch, non_blocking=non_blocking)


def _forward(networks: Any, batch: ZoneBatch, *, non_blocking: bool = False) -> tuple[Tensor, Tensor]:
    """The network: every listed option's logit, in position order, and each position's values.

    `networks` is one network (_OneNetwork) or several (NetworkStack); each
    layer reads each network's own rows. With non_blocking, keep `batch` until
    the outputs are read (batch_tensors).
    """
    models = networks.models
    model = models[0]
    device = model.value_head[-1].weight.device
    if device.type == "mps":
        # Also covers callers using the normal PyTorch model.to('mps') API.
        _require_no_mps_fallback()
    t = batch_tensors(batch, device, non_blocking=non_blocking)
    positions, zones, dim = batch.positions, batch.zones, model.config.hidden_dim
    nodes = positions * zones
    sizes = batch.network_positions
    node_sizes = [size * zones for size in sizes]
    identity, facts = networks.zone_terms(batch, t)
    local = _bag(networks.zone_table, t["zone_column"], t["zone_weight"], t["zone_bags"])
    local = local.view(positions, zones, dim) + identity + facts
    h = _per_network(networks, ("zone_norm",), local.view(nodes, dim), node_sizes,
                     [m.zone_norm for m in models], "norm")
    u = _per_network(networks, ("global_norm",),
                     _bag(networks.global_table, t["global_column"], t["global_weight"], t["global_bags"]),
                     sizes, [m.global_norm for m in models], "norm")
    sources, targets, degree = networks.borders(positions, zones)
    for layer in range(model.config.message_layers):
        sent = F.gelu(_per_network(networks, ("messages", layer), h, node_sizes,
                                   [m.messages[layer] for m in models], "linear").index_select(0, sources)
                      + networks.border_terms(layer, batch, t))
        # Zeros of the messages' own type, so that a pass under automatic mixed
        # precision, whose messages are half-precision, can add them up.
        received = sent.new_zeros((nodes, dim)).index_add_(0, targets, sent) / degree
        h = h + _per_network(networks, ("zone_updates", layer), (h, received, u.repeat_interleave(zones, 0)),
                             node_sizes, [m.zone_updates[layer] for m in models], "block")
        u = u + _per_network(networks, ("position_updates", layer), (u, h.view(positions, zones, dim).mean(1)),
                             sizes, [m.position_updates[layer] for m in models], "block")
    grid = h.view(positions, zones, dim)
    states = _per_network(networks, ("state_encoder",), (u, grid.mean(1), grid.amax(1)), sizes,
                          [m.state_encoder for m in models], "block")
    # Raw-value/value_scale units.
    values = _per_network(networks, ("value_head",), states, sizes, [m.value_head for m in models], "head")
    if not batch.options:
        return values.new_empty((0,)), values
    option_sizes = batch.network_options
    options = _per_network(networks, ("option_norm",),
                           _bag(networks.option_table, t["action_column"], t["action_weight"], t["action_bags"]),
                           option_sizes, [m.option_norm for m in models], "norm")
    bank = torch.cat((h, networks.no_zone))
    path = h.new_zeros((batch.options, dim)).index_add_(
        0, t["path_option"], bank.index_select(0, t["path_zone"])) * t["path_scale"]
    latent = _per_network(networks, ("option_encoder",),
                          (options, bank.index_select(0, t["action_source"]),
                           bank.index_select(0, t["action_target"]), path),
                          option_sizes, [m.option_encoder for m in models], "block")
    scores = _per_network(networks, ("policy_head",), (states.index_select(0, t["action_position"]), latent),
                          option_sizes, [m.policy_head for m in models], "head").squeeze(1)
    if model.config.policy_factorization:
        scores = _readout(networks, states, latent, scores, t, batch)
    return scores, values


def _readout(networks: Any, states: Tensor, latent: Tensor, scores: Tensor, t: dict[str, Tensor],
             batch: ZoneBatch) -> Tensor:
    """Normalize kind -> what acts -> how it travels -> what it acts on -> exact option.

    These are neural conditional readouts of the same complete legal menu.
    No option is inserted, reordered, merged or pruned; each level scores a
    group from the mean vector of its options. Every group of every level and
    every option is normalized among those sharing its parent in one softmax
    pass, and an option's log-probability is the sum along its branch.
    """
    groups = batch.groups
    means = latent.new_zeros((groups, latent.shape[1])).index_add_(
        0, t["readout_owners"], latent.repeat(GROUP_LEVELS, 1)) / t["readout_counts"]
    heads = [model.factor_heads[level] for level in range(GROUP_LEVELS) for model in networks.models]
    group_scores = _per_network(networks, ("factor_heads",), (states.index_select(0, t["readout_rows"]), means),
                                batch.readout_sizes, heads, "head").squeeze(1)
    normalized = _conditional_log_softmax(torch.cat((group_scores, scores)), t["readout_segments"],
                                          batch.positions + groups)
    return normalized.index_select(0, t["readout_terms"]).view(GROUP_LEVELS + 1, -1).sum(0)


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
        if len(batch.network_positions) != 1:
            raise ValueError("A batch for several networks needs a NetworkStack")
        return _forward(_OneNetwork(self), batch, non_blocking=non_blocking)


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
