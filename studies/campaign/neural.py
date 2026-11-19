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


def _zone_terms(model: "CampaignPolicyValueNet") -> tuple[Tensor, Tensor]:
    """Each zone's own learned vector and its map facts' vector: (zones, dim) each."""
    return model.zone_identity.weight, _linear(model.map_facts, model.zone_static)


def _border_terms(model: "CampaignPolicyValueNet", layer: int) -> Tensor:
    """Each border's own term in a message-passing layer: (borders, dim)."""
    return _linear(model.border_facts[layer], model.edge_static)


def _state_layers(models: Sequence[Any], sizes: Sequence[int], local: Tensor, glob: Tensor,
                  zone_terms: Sequence[Tensor], border_terms: Sequence[Tensor], *,
                  averaging_matrix: bool = False) -> tuple[Tensor, Tensor, Tensor]:
    """The zone and position layers: zone vectors, state vectors and values.

    `local` holds each state's zones' answers, (states, zones, dim), and `glob`
    each state's own, (states, dim); the states come grouped by network, sizes[i]
    for models[i]. Every state has the map's zones and borders, so a message
    layer gathers each border's source zone with one fixed index along the zone
    axis. Each zone averages the messages it receives by adding them in and
    dividing by its in-degree, or, with `averaging_matrix`, by a matrix product
    with a fixed (zones, borders) matrix, which needs no atomic addition on a GPU:
    the compiled layers use it (compiled_state_layers).
    """
    model = models[0]
    zones = local.shape[1]
    for term in zone_terms:
        local = local + term
    h = _by_network(local, sizes, [m.zone_norm for m in models], _norm)
    u = _by_network(glob, sizes, [m.global_norm for m in models], _norm)
    for layer, border in enumerate(border_terms):
        sent = F.gelu(_by_network(h, sizes, [m.messages[layer] for m in models], _linear).index_select(
            1, model.edge_source) + border)
        if averaging_matrix:
            received = torch.matmul(model.border_average, sent)
        else:
            received = sent.new_zeros(h.shape).index_add_(1, model.edge_target, sent) / model.in_degree
        h = h + _by_network(torch.cat((h, received, u.unsqueeze(1).expand(-1, zones, -1)), dim=2), sizes,
                            [m.zone_updates[layer] for m in models], _apply_block)
        u = u + _by_network(torch.cat((u, h.mean(1)), dim=1), sizes,
                            [m.position_updates[layer] for m in models], _apply_block)
    states = _by_network(torch.cat((u, h.mean(1), h.amax(1)), dim=1), sizes,
                         [m.state_encoder for m in models], _apply_block)
    return h, states, _by_network(states, sizes, [m.value_head for m in models], _apply_head)  # value_scale units.


# The state counts the compiled zone and position layers are compiled for: each at
# most a third more than the one below, so padding costs at most a third more work.
STATE_BUCKETS = (1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128, 160, 192, 256, 320, 384, 512)


def state_bucket(count: int) -> int:
    """The smallest fixed state count at least `count`; above 512, a multiple of 128."""
    for size in STATE_BUCKETS:
        if size >= count:
            return size
    return -(-count // 128) * 128


def _one_network_state_layers(model: "CampaignPolicyValueNet", local: Tensor, glob: Tensor):
    return _state_layers((model,), (local.shape[0],), local, glob, _zone_terms(model),
                         [_border_terms(model, layer) for layer in range(model.config.message_layers)],
                         averaging_matrix=True)


_compiled_layers: Any = None


def compiled_state_layers(model: "CampaignPolicyValueNet", local: Tensor, glob: Tensor):
    """One network's zone and position layers, compiled by torch.compile for the shape
    of `local`: once per state bucket, and again only for a network of another size.

    The compiled code reads the network's weights as they are at each call, so new
    weights copied in need no new compilation. For inference only.
    """
    global _compiled_layers
    if _compiled_layers is None:
        # One compilation per bucket and network size, beyond the default limit of 8.
        torch._dynamo.config.cache_size_limit = max(torch._dynamo.config.cache_size_limit, 128)
        _compiled_layers = torch.compile(_one_network_state_layers, dynamic=False, fullgraph=True)
    return _compiled_layers(model, local, glob)


def distinct_networks(models: Mapping[str, Any]) -> list[Any]:
    """Each network of an alliance-to-network mapping once, in alliance order.

    Three separate networks, or one network that serves all three alliances."""
    found: dict[int, Any] = {}
    for player in PLAYERS:
        found.setdefault(id(models[player]), models[player])
    return list(found.values())


def alliance_networks(config: "CampaignModelConfig", networks: str = "one", *,
                      device: str | torch.device = "cpu") -> dict[str, "CampaignPolicyValueNet"]:
    """One fresh network for all three alliances, or, with networks "three", one for each."""
    if networks == "one":
        model = CampaignPolicyValueNet(config, device=device).eval()
        return {player: model for player in PLAYERS}
    if networks != "three":
        raise ValueError("networks must be three or one")
    return {player: CampaignPolicyValueNet(config, device=device).eval() for player in PLAYERS}


def alliance_weights(models: Mapping[str, nn.Module], *, clone: bool = False) -> dict[str, dict[str, Tensor]]:
    """Each alliance's network's weights on the CPU: one dictionary for each distinct
    network, so that one network serving all three alliances is copied once."""
    made: dict[int, dict[str, Tensor]] = {}
    for model in distinct_networks(models):
        made[id(model)] = {name: tensor.detach().cpu().clone() if clone else tensor.detach().cpu()
                           for name, tensor in model.state_dict().items()}
    return {player: made[id(models[player])] for player in PLAYERS}


def load_alliance_weights(models: Mapping[str, nn.Module], weights: Mapping[str, Mapping[str, Tensor]]) -> None:
    """Load each alliance's weights into its network, each distinct network once."""
    loaded: set[int] = set()
    for player in PLAYERS:
        if id(models[player]) not in loaded:
            models[player].load_state_dict(weights[player])
            loaded.add(id(models[player]))


class _OneNetwork:
    """A pass's view of one network: its own tables and fixed terms, worked out for
    this pass, so that training reaches every parameter."""

    compiled = False

    def __init__(self, model: "CampaignPolicyValueNet") -> None:
        self.models = (model,)
        self.zone_table = model.zone_columns.weight
        self.global_table = model.global_columns.weight
        self.option_table = model.option_columns.weight
        self.no_zone = model.no_zone.unsqueeze(0)

    def zone_terms(self, batch: ZoneBatch, t: dict[str, Tensor]) -> tuple[Tensor, Tensor]:
        """Each zone's own learned vector and its map facts' vector: (zones, dim) each."""
        return _zone_terms(self.models[0])

    def border_terms(self, layer: int, batch: ZoneBatch, t: dict[str, Tensor]) -> Tensor:
        """Each border's own term in a message-passing layer: (borders, dim)."""
        return _border_terms(self.models[0], layer)


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
    inference only; build a new one after the weights change. With `compiled`,
    one network runs its zone and position layers compiled for fixed numbers of
    states (compiled_state_layers); several networks always run them as written.
    """

    def __init__(self, models: Sequence["CampaignPolicyValueNet"], *, compiled: bool = False) -> None:
        models = tuple(models)
        if not models:
            raise ValueError("A network stack needs at least one network")
        first = models[0]
        for model in models[1:]:
            if model.config != first.config or model.layout_version != first.layout_version:
                raise ValueError("Stacked networks must share their configuration and input layout")
        self.models, self.spec, self.config = models, first.spec, first.config
        self.compiled = compiled and len(models) == 1
        with torch.inference_mode():
            self.zone_table = torch.cat([model.zone_columns.weight for model in models])
            self.global_table = torch.cat([model.global_columns.weight for model in models])
            self.option_table = torch.cat([model.option_columns.weight for model in models])
            self.no_zone = torch.stack([model.no_zone for model in models])
            self.identity = torch.stack([model.zone_identity.weight for model in models])
            self.facts = torch.stack([_linear(model.map_facts, model.zone_static) for model in models])
            self.border = [torch.stack([_border_terms(model, layer) for model in models])
                           for layer in range(first.config.message_layers)]

    def _single(self, batch: ZoneBatch) -> int | None:
        present = [index for index, size in enumerate(batch.network_positions) if size]
        return present[0] if len(present) == 1 else None

    def zone_terms(self, batch: ZoneBatch, t: dict[str, Tensor]) -> tuple[Tensor, Tensor]:
        """Each zone's own vector and its map facts' vector: (zones, dim) each when one
        network has every state, else (states, zones, dim)."""
        single = self._single(batch)
        if single is not None:
            return self.identity[single], self.facts[single]
        network = t["position_network"]
        return self.identity.index_select(0, network), self.facts.index_select(0, network)

    def border_terms(self, layer: int, batch: ZoneBatch, t: dict[str, Tensor]) -> Tensor:
        """(borders, dim) when one network has every state, else (states, borders, dim)."""
        single = self._single(batch)
        if single is not None:
            return self.border[layer][single]
        return self.border[layer].index_select(0, t["position_network"])

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
    the outputs are read (batch_tensors). A compiled stack, outside training,
    runs the zone and position layers compiled, the states padded with empty
    ones to the next of STATE_BUCKETS.
    """
    models = networks.models
    model = models[0]
    device = model.value_head[-1].weight.device
    if device.type == "mps":
        # Also covers callers using the normal PyTorch model.to('mps') API.
        _require_no_mps_fallback()
    positions, zones, dim = batch.positions, batch.zones, model.config.hidden_dim
    compiled = networks.compiled and not torch.is_grad_enabled()
    padded = state_bucket(positions) if compiled else positions
    if padded > positions:
        # Empty bags for the padded states: their zone and position vectors start at zero.
        integers = batch.integers
        integers["zone_bags"] = np.concatenate(
            (integers["zone_bags"], np.full((padded - positions) * zones, integers["zone_bags"][-1], np.int64)))
        integers["global_bags"] = np.concatenate(
            (integers["global_bags"], np.full(padded - positions, integers["global_bags"][-1], np.int64)))
    t = batch_tensors(batch, device, non_blocking=non_blocking)
    local = _bag(networks.zone_table, t["zone_column"], t["zone_weight"], t["zone_bags"]).view(padded, zones, dim)
    glob = _bag(networks.global_table, t["global_column"], t["global_weight"], t["global_bags"])
    if compiled:
        h, states, values = compiled_state_layers(model, local, glob)
        h, states, values = h[:positions], states[:positions], values[:positions]
    else:
        h, states, values = _state_layers(models, batch.network_positions, local, glob, networks.zone_terms(batch, t),
                                          [networks.border_terms(layer, batch, t)
                                           for layer in range(model.config.message_layers)])
    h = h.reshape(positions * zones, dim)
    if not batch.options:
        return values.new_empty((0,)), values
    option_sizes = batch.network_options
    options = _by_network(_bag(networks.option_table, t["action_column"], t["action_weight"], t["action_bags"]),
                          option_sizes, [m.option_norm for m in models], _norm)
    bank = torch.cat((h, networks.no_zone))
    path = h.new_zeros((batch.options, dim)).index_add_(
        0, t["path_option"], bank.index_select(0, t["path_zone"])) * t["path_scale"]
    latent = _by_network(torch.cat((options, bank.index_select(0, t["action_source"]),
                                    bank.index_select(0, t["action_target"]), path), dim=1),
                         option_sizes, [m.option_encoder for m in models], _apply_block)
    scores = _by_network(torch.cat((states.index_select(0, t["action_position"]), latent), dim=1), option_sizes,
                         [m.policy_head for m in models], _apply_head).squeeze(1)
    if model.config.policy_factorization:
        scores = _readout(models, states, latent, scores, t, batch)
    return scores, values


def _readout(models: Sequence[Any], states: Tensor, latent: Tensor, scores: Tensor, t: dict[str, Tensor],
             batch: ZoneBatch) -> Tensor:
    """Normalize kind -> what acts -> how it travels -> what it acts on -> exact option.

    These are neural conditional readouts of the same complete legal menu.
    No option is inserted, reordered, merged or pruned; each level scores a
    group from the mean vector of its options. Every group of every level and
    every option is normalized among those sharing its parent in one softmax
    pass, and an option's log-probability is the sum along its branch.
    """
    groups = batch.groups
    # Each option's vector added to its group at every level, one level at a time:
    # readout_owners lists the options' groups level by level. A repeat of the
    # options' vectors, one copy per level, would make the Mac's GPU compile a graph
    # for every new number of options, which is nearly every inference batch
    # (docs/archive/records/inference_server_profile_gpu_2026_11_18.md).
    owners = t["readout_owners"].view(GROUP_LEVELS, -1)
    means = latent.new_zeros((groups, latent.shape[1]))
    for level in range(GROUP_LEVELS):
        means.index_add_(0, owners[level], latent)
    means = means / t["readout_counts"]
    heads = [model.factor_heads[level] for level in range(GROUP_LEVELS) for model in models]
    group_scores = _by_network(torch.cat((states.index_select(0, t["readout_rows"]), means), dim=1),
                               batch.readout_sizes, heads, _apply_head).squeeze(1)
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
        # Each zone's average of the messages it receives, as a (zones, borders) matrix:
        # 1 / in-degree where a border ends at the zone. A zone no border reaches gets 0.
        degree = np.maximum(np.bincount(spec.edge_target, minlength=zones), 1).astype(np.float32)
        average = np.zeros((zones, len(spec.edge_target)), dtype=np.float32)
        average[spec.edge_target, np.arange(len(spec.edge_target))] = 1.0 / degree[spec.edge_target]
        for name, values in (("zone_static", spec.zone_static), ("edge_source", spec.edge_source),
                             ("edge_target", spec.edge_target), ("edge_static", spec.edge_static),
                             ("in_degree", degree[:, None]), ("border_average", average)):
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
    networks' raw value vectors, of the three alliances' networks or of the one
    network serving all three, and emits no policy. This is a bootstrap
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
        # Each alliance's network, or one network that serves all three alliances.
        networks = distinct_networks(self.models)
        network_of = {player: next(index for index, model in enumerate(networks) if model is self.models[player])
                      for player in PLAYERS}
        groups: list[list[tuple[int, Any]]] = [[] for _ in networks]
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
                for group in groups:  # Every network rates a chance cutoff, once.
                    group.append((row, item))
            elif actor in PLAYERS:
                groups[network_of[actor]].append((row, make_zone_input(env, actions)))
            else:
                raise ValueError(f"Unknown campaign decision player: {actor}")
        for model, group in zip(networks, groups, strict=True):
            if not group:
                continue
            training = model.training
            model.eval()
            completed_mps_forward = False
            try:
                with torch.inference_mode():
                    batch = [item for _, item in group]
                    logits, values = model.forward_batch(batch)
                    if values.shape != (len(batch), 3) or len(logits) != len(batch):
                        raise ValueError("Neural model returned an invalid batch shape")
                    counts = [item.action_count for item in batch]
                    if values.device.type != "cpu":
                        host_priors, host_values = _gpu_evaluation_outputs(logits, values, counts, model.config.value_scale)
                        for index, (row, _) in enumerate(group):
                            if row in chance_values:
                                chance_values[row].append(host_values[index])
                            else:
                                results[row] = Evaluation(host_priors[index], host_values[index])
                        completed_mps_forward = values.device.type == "mps"
                        continue  # The finally still restores model.train(training).
                    for index, (row, _) in enumerate(group):
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
            results[row] = Evaluation([], vector([sum(value[i] for value in predictions) / len(predictions)
                                                  for i in range(3)]))
        if any(result is None for result in results):
            raise RuntimeError("A neural batch request was not evaluated")
        return [result for result in results if result is not None]
