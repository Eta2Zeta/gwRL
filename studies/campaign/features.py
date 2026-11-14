"""The network's input: the fixed zone encoding of a campaign decision.

The engine describes a decision as nonzero answers to fixed questions about
each zone of the map, about the position as a whole and about each legal
option (src/zone_encoding.cpp; docs/design/network_input.md).
Every answer is an integer and every question has one fixed column. This
module fetches that encoding and lays several decisions out as flat arrays
for one network pass.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Mapping, Sequence

import numpy as np

import gwrl_cpp

ZoneInput = gwrl_cpp.CampaignZoneInput
GROUP_LEVELS = 4  # Policy groups per option: kind, what acts, how it travels, what it acts on.


@dataclass(frozen=True)
class ZoneSpec:
    """The fixed layout: column counts, map facts and borders. Never per position."""
    version: str
    zones: tuple[str, ...]
    zone_columns: int
    global_columns: int
    action_columns: int
    zone_static: np.ndarray   # (zones, map facts) float32
    edge_source: np.ndarray   # (borders,) int64, directed
    edge_target: np.ndarray   # (borders,) int64
    edge_static: np.ndarray   # (borders, border facts) float32
    # The position columns naming the deciding player: (column, player or None).
    owner_columns: tuple[tuple[int, str | None], ...] = ()


def zone_spec(env: Any) -> ZoneSpec:
    raw = getattr(env, "raw", env)
    spec = raw.zone_encoding_spec()
    owners = tuple((index, None if name == "deciding_player:~none" else name.split(":", 1)[1])
                   for index, name in enumerate(spec["global_column_names"]) if name.startswith("deciding_player:"))
    return ZoneSpec(version=spec["version"], zones=tuple(spec["zones"]), zone_columns=int(spec["zone_columns"]),
                    global_columns=int(spec["global_columns"]), action_columns=int(spec["action_columns"]),
                    zone_static=np.asarray(spec["zone_static"], dtype=np.float32),
                    edge_source=np.asarray(spec["edge_source"], dtype=np.int64),
                    edge_target=np.asarray(spec["edge_target"], dtype=np.int64),
                    edge_static=np.asarray(spec["edge_static"], dtype=np.float32), owner_columns=owners)


@lru_cache(maxsize=1)
def default_zone_spec() -> ZoneSpec:
    """The campaign scenario's layout. Every horizon of the curriculum shares it."""
    from .curriculum import make_env
    return zone_spec(make_env(1, calendar_rounds=1))


def make_zone_input(env: Any, actions: Sequence[Any]) -> ZoneInput:
    """The decision's encoding listing exactly `actions`, built once per decision."""
    export = getattr(env, "zone_input", None)
    if export is None:
        raise TypeError("Campaign evaluation needs an environment with the zone encoding")
    zone = export(tuple(actions))
    if not isinstance(zone, ZoneInput) or zone.action_count != len(actions):
        raise ValueError("The zone encoding does not list the requested options")
    return zone


def validate_zone_input(item: Any, version: str) -> int:
    """A stored input's option count, after checking it belongs to this layout."""
    if not isinstance(item, ZoneInput) or item.version != version:
        raise ValueError("Input is not a zone encoding of this layout")
    return item.action_count


def zone_owner(item: ZoneInput, spec: ZoneSpec) -> str | None:
    """The deciding player the input names, as the network reads it; None at chance."""
    present = np.isin([column for column, _ in spec.owner_columns], item.arrays()["global_column"])
    named = [player for (_, player), found in zip(spec.owner_columns, present) if found]
    if len(named) != 1:
        raise ValueError("Zone input does not name exactly one deciding player")
    return named[0]


def _signed_log(values: np.ndarray) -> np.ndarray:
    values = values.astype(np.float32)
    return np.sign(values) * np.log1p(np.abs(values))


def _join(parts: list[np.ndarray], dtype: Any) -> np.ndarray:
    return np.concatenate(parts).astype(dtype, copy=False) if parts else np.zeros(0, dtype)


def _check_range(values: np.ndarray, low: int, high: int, what: str) -> None:
    if values.size and (int(values.min()) < low or int(values.max()) >= high):
        raise ValueError(f"Zone input {what} out of range")


def _bag_offsets(counts: Any) -> np.ndarray:
    """Where each bag's answers start, then the end of the last: bag i adds answers
    offsets[i] to offsets[i + 1] - 1, the layout neural._bag reads."""
    offsets = np.zeros(len(counts) + 1, dtype=np.int64)
    np.cumsum(counts, out=offsets[1:])
    return offsets


@dataclass
class ZoneBatch:
    """Several decisions as flat host arrays for one network pass.

    Answers are grouped by the bag they add into, in bag order: each zone of
    each position, each position, or each option. A bag array holds where each
    bag's answers start, then the end of the last. Option zones index the
    batch's zone vectors, followed by one "no zone" slot per network.

    The policy readout scores the policy groups of all four levels and every
    option, then normalizes each among those sharing its parent, in one pass
    (neural._readout). The groups of all levels are numbered one after another,
    level 0 first, each level's groups in position order. `readout_segments`
    names each group's and each option's parent: for level 0 its position, for
    the other levels and for options a group of the level above, counted after
    the positions. `readout_terms` lists, for each option, its group at each
    level and then the option itself, level by level.

    One pass may evaluate decisions for several networks of one layout
    (neural.NetworkStack): `network_positions` says how many decisions each
    network has, in order, and the decisions come grouped that way. Each
    network's answers then read its own rows of the networks' tables, laid end
    to end, and each network's layers read its own rows of every kind; the
    `network_*` and `readout_sizes` lists give those rows' counts.
    """
    positions: int
    zones: int
    option_counts: list[int]
    network_positions: list[int]
    network_options: list[int]
    # Policy groups for each level and network, level by level: one group head each.
    readout_sizes: list[int]
    integers: dict[str, np.ndarray]
    floats: dict[str, np.ndarray]
    # Host copies a device transfer may still be reading; see neural.batch_tensors.
    host_buffers: list[Any] = field(default_factory=list)

    @property
    def options(self) -> int:
        return sum(self.option_counts)

    @property
    def groups(self) -> int:
        return sum(self.readout_sizes)


def pack_zone_arrays(items: Sequence[Mapping[str, np.ndarray]], spec: ZoneSpec,
                     network_positions: Sequence[int] | None = None) -> ZoneBatch:
    """Lay decisions out for one pass, checking every index the network reads.

    With `network_positions`, the first network_positions[0] decisions belong
    to the first of several networks, the next ones to the second, and so on.
    """
    zones = len(spec.zones)
    count = len(items)
    networks = [count] if network_positions is None else [int(size) for size in network_positions]
    if not networks or min(networks) < 0 or sum(networks) != count:
        raise ValueError("The networks' decision counts do not add up to the decisions")
    network = np.repeat(np.arange(len(networks), dtype=np.int64), networks)
    several = len(networks) > 1
    options = [len(item["action_source"]) for item in items]
    zone_index = _join([item["zone_index"] for item in items], np.int64)
    _check_range(zone_index, 0, zones, "zone")
    zone_column = _join([item["zone_column"] for item in items], np.int64)
    _check_range(zone_column, 0, spec.zone_columns, "zone column")
    global_column = _join([item["global_column"] for item in items], np.int64)
    _check_range(global_column, 0, spec.global_columns, "position column")
    action_column = _join([item["action_column"] for item in items], np.int64)
    _check_range(action_column, 0, spec.action_columns, "option column")
    zone_value = _join([item["zone_value"] for item in items], np.int32)
    zone_rows = zone_index + np.repeat(np.arange(count, dtype=np.int64) * zones,
                                       [len(item["zone_index"]) for item in items])
    if zone_rows.size > 1 and (zone_rows[1:] < zone_rows[:-1]).any():
        # The engine lists each position's answers zone by zone; another order is
        # put into bag order here, since a bag's answers must be consecutive.
        order = np.argsort(zone_rows, kind="stable")
        zone_rows, zone_column, zone_value = zone_rows[order], zone_column[order], zone_value[order]
    entries = np.concatenate([np.diff(item["action_offsets"]) for item in items]) if items else np.zeros(0, np.int64)
    global_counts = [len(item["global_column"]) for item in items]
    option_network = np.repeat(network, options)
    if several:
        # Each network's answers read its own rows of the tables laid end to end.
        zone_column = zone_column + network[zone_rows // zones] * spec.zone_columns
        global_column = global_column + np.repeat(network, global_counts) * spec.global_columns
        action_column = action_column + np.repeat(option_network, entries) * spec.action_columns
    integers = {"zone_bags": _bag_offsets(np.bincount(zone_rows, minlength=count * zones)), "zone_column": zone_column,
                "global_bags": _bag_offsets(global_counts),
                "global_column": global_column, "action_bags": _bag_offsets(entries), "action_column": action_column}
    if several:
        integers["position_network"] = network
    floats = {"zone_weight": _signed_log(zone_value),
              "global_weight": _signed_log(_join([item["global_value"] for item in items], np.int32)),
              "action_weight": _signed_log(_join([item["action_value"] for item in items], np.int32))}
    readout_sizes = [0] * (GROUP_LEVELS * len(networks))
    if sum(options):
        owner_position = np.repeat(np.arange(count, dtype=np.int64), options)

        def zone_slots(name: str) -> np.ndarray:
            values = _join([item[name] for item in items], np.int64)
            _check_range(values, -1, zones, "option zone")
            return np.where(values >= 0, values + owner_position * zones, count * zones + option_network)

        path_counts = _join([np.diff(item["path_offsets"]) for item in items], np.int64)
        path_zone = _join([item["path_zone"] for item in items], np.int64)
        _check_range(path_zone, 0, zones, "path zone")
        path_option = np.repeat(np.arange(len(path_counts), dtype=np.int64), path_counts)
        groups = np.concatenate([np.asarray(item["factor_groups"], dtype=np.int64).reshape(-1, GROUP_LEVELS)
                                 for item in items])
        if groups.shape[0] != sum(options) or groups.min() < 0:
            raise ValueError("Zone input policy groups do not match its options")
        integers.update(action_position=owner_position, action_source=zone_slots("action_source"),
                        action_target=zone_slots("action_target"),
                        path_zone=path_zone + owner_position[path_option] * zones, path_option=path_option)
        floats["path_scale"] = (1.0 / np.maximum(path_counts, 1)).astype(np.float32)[:, None]
        # Batch-wide group ids: each position's ids shifted past the earlier positions'.
        per_position = np.zeros((count, GROUP_LEVELS), dtype=np.int64)
        np.maximum.at(per_position, owner_position, groups + 1)
        shifts = np.cumsum(per_position, axis=0) - per_position
        owners = groups + shifts[owner_position]
        totals = per_position.sum(axis=0)
        # Then numbered across the levels, level 0 first.
        starts = np.cumsum(totals) - totals
        rows, segments = [], []
        for level in range(GROUP_LEVELS):
            if level == 0:
                parents = np.repeat(np.arange(count, dtype=np.int64), per_position[:, 0])
                rows.append(parents)
                segments.append(parents)
            else:
                parents = np.empty(int(totals[level]), dtype=np.int64)
                parents[owners[:, level]] = owners[:, level - 1]
                rows.append(rows[-1][parents])
                segments.append(count + starts[level - 1] + parents)
            readout_sizes[level * len(networks):(level + 1) * len(networks)] = np.bincount(
                network, weights=per_position[:, level], minlength=len(networks)).astype(np.int64).tolist()
        segments.append(count + starts[-1] + owners[:, -1])  # An option's parent is its last group.
        readout_owners = (owners + starts).T.ravel()  # Each option's group at each level, level by level.
        groups_total = int(totals.sum())
        integers.update(readout_owners=readout_owners, readout_rows=np.concatenate(rows),
                        readout_segments=np.concatenate(segments),
                        readout_terms=np.concatenate((readout_owners,
                                                      groups_total + np.arange(len(owners), dtype=np.int64))))
        floats["readout_counts"] = np.bincount(readout_owners, minlength=groups_total).astype(np.float32)[:, None]
    network_options = np.bincount(network, weights=options, minlength=len(networks)).astype(np.int64).tolist()
    return ZoneBatch(count, zones, options, networks, network_options, readout_sizes, integers, floats)


def pack_zone_inputs(inputs: Sequence[ZoneInput], spec: ZoneSpec) -> ZoneBatch:
    for item in inputs:
        validate_zone_input(item, spec.version)
    return pack_zone_arrays([item.arrays() for item in inputs], spec)
