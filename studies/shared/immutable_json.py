"""JSON-compatible immutable source snapshots shared by inference and replay.

Only source data is retained here. Model outputs and tensors must be recomputed
after every parameter update.
"""
from __future__ import annotations

import json
from typing import Any


def _read_only(*_args: Any, **_kwargs: Any) -> None:
    raise TypeError("Immutable JSON snapshots are read-only")


class FrozenDict(dict):
    """An immutable JSON object with its complete canonical text cached lazily."""

    __slots__ = ("_canonical_json",)
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _read_only
    __setattr__ = __delattr__ = _read_only

    def __init__(self, value: Any = ()) -> None:
        if hasattr(self, "_canonical_json"):
            _read_only()
        dict.__init__(self, {key: freeze_json(item) for key, item in dict(value).items()})
        object.__setattr__(self, "_canonical_json", None)

    @property
    def canonical_json(self) -> str:
        text = self._canonical_json
        if text is None:
            text = json.dumps(self, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            object.__setattr__(self, "_canonical_json", text)
        return text

    def __reduce_ex__(self, _protocol: int) -> Any:
        return type(self), (dict(self),)

    def __deepcopy__(self, _memo: dict[int, Any]) -> FrozenDict:
        return self


class FrozenList(list):
    """An immutable JSON array, including its nested objects and arrays."""

    __slots__ = ("_initialized",)
    __setitem__ = __delitem__ = append = clear = extend = insert = pop = remove = reverse = sort = _read_only
    __iadd__ = __imul__ = __setattr__ = __delattr__ = _read_only

    def __init__(self, value: Any = ()) -> None:
        if hasattr(self, "_initialized"):
            _read_only()
        list.__init__(self, (freeze_json(item) for item in value))
        object.__setattr__(self, "_initialized", True)

    def __reduce_ex__(self, _protocol: int) -> Any:
        return type(self), (list(self),)

    def __deepcopy__(self, _memo: dict[int, Any]) -> FrozenList:
        return self


def freeze_json(value: Any) -> Any:
    """Detach mutable source containers once; retain existing frozen snapshots."""
    if isinstance(value, (FrozenDict, FrozenList)):
        return value
    if isinstance(value, dict):
        return FrozenDict(value)
    if isinstance(value, list):
        return FrozenList(value)
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"Unsupported immutable JSON value: {type(value).__name__}")
