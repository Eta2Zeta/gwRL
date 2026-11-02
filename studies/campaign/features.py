"""The network's input: the fixed zone encoding of a campaign decision.

The engine describes a decision as nonzero answers to fixed questions about
each zone of the map, about the position as a whole and about each legal
option (src/zone_encoding.cpp; docs/stage_a/zone_encoding_2026_11_02.md).
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


@dataclass
class ZoneBatch:
    """Several decisions as flat host arrays for one network pass.

    Entry rows say which bag an answer adds into: a zone of a position, a
    position, or an option. Option zones index the batch's zone vectors, with
    one extra slot, positions * zones, meaning "no zone". Policy-group ids are
    numbered across the batch; a level's parents are groups of the level above,
    and level 0's parents are the positions.
    """
    positions: int
    zones: int
    option_counts: list[int]
    group_counts: list[int]
    integers: dict[str, np.ndarray]
    floats: dict[str, np.ndarray]
    # Host copies a device transfer may still be reading; see neural.batch_tensors.
    host_buffers: list[Any] = field(default_factory=list)

    @property
    def options(self) -> int:
        return sum(self.option_counts)


def pack_zone_arrays(items: Sequence[Mapping[str, np.ndarray]], spec: ZoneSpec) -> ZoneBatch:
    """Lay decisions out for one pass, checking every index the network reads."""
    zones = len(spec.zones)
    count = len(items)
    none = count * zones
    options = [len(item["action_source"]) for item in items]
    zone_index = _join([item["zone_index"] for item in items], np.int64)
    _check_range(zone_index, 0, zones, "zone")
    zone_column = _join([item["zone_column"] for item in items], np.int64)
    _check_range(zone_column, 0, spec.zone_columns, "zone column")
    global_column = _join([item["global_column"] for item in items], np.int64)
    _check_range(global_column, 0, spec.global_columns, "position column")
    action_column = _join([item["action_column"] for item in items], np.int64)
    _check_range(action_column, 0, spec.action_columns, "option column")
    zone_rows = zone_index + np.repeat(np.arange(count, dtype=np.int64) * zones,
                                       [len(item["zone_index"]) for item in items])
    global_rows = np.repeat(np.arange(count, dtype=np.int64), [len(item["global_column"]) for item in items])
    entries = np.concatenate([np.diff(item["action_offsets"]) for item in items]) if items else np.zeros(0, np.int64)
    action_rows = np.repeat(np.arange(len(entries), dtype=np.int64), entries)
    integers = {"zone_rows": zone_rows, "zone_column": zone_column, "global_rows": global_rows,
                "global_column": global_column, "action_rows": action_rows, "action_column": action_column}
    floats = {"zone_weight": _signed_log(_join([item["zone_value"] for item in items], np.int32)),
              "global_weight": _signed_log(_join([item["global_value"] for item in items], np.int32)),
              "action_weight": _signed_log(_join([item["action_value"] for item in items], np.int32))}
    group_counts = [0] * GROUP_LEVELS
    if sum(options):
        owner_position = np.repeat(np.arange(count, dtype=np.int64), options)

        def zone_slots(name: str) -> np.ndarray:
            values = _join([item[name] for item in items], np.int64)
            _check_range(values, -1, zones, "option zone")
            return np.where(values >= 0, values + owner_position * zones, none)

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
        rows = None
        for level in range(GROUP_LEVELS):
            total = int(totals[level])
            if level == 0:
                parents = np.repeat(np.arange(count, dtype=np.int64), per_position[:, 0])
                rows = parents
            else:
                parents = np.empty(total, dtype=np.int64)
                parents[owners[:, level]] = owners[:, level - 1]
                rows = rows[parents]
            integers[f"group{level}_owners"] = np.ascontiguousarray(owners[:, level])
            integers[f"group{level}_parents"] = parents
            integers[f"group{level}_rows"] = rows
            floats[f"group{level}_counts"] = np.bincount(owners[:, level], minlength=total).astype(np.float32)[:, None]
            group_counts[level] = total
    return ZoneBatch(count, zones, options, group_counts, integers, floats)


def pack_zone_inputs(inputs: Sequence[ZoneInput], spec: ZoneSpec) -> ZoneBatch:
    for item in inputs:
        validate_zone_input(item, spec.version)
    return pack_zone_arrays([item.arrays() for item in inputs], spec)
