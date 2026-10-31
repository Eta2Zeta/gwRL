"""Lossless bounded graph frames inside trusted local training checkpoints.

Only immutable compiled graph buffers and reference metadata enter these
frames. A private byte tensor carries compressed storage; it is not a learned
tensor. No board JSON or learned tensor is generated here. The surrounding
checkpoint already uses trusted-local pickle (``weights_only=False``); this
compression envelope does not turn pickle into an untrusted input format.
"""
from __future__ import annotations

import io
import pickle
from typing import Any
import zlib

BYTES_SCHEMA = "campaign-numeric-graph-zlib-v1"
SCHEMA = "campaign-numeric-graph-zlib-storage-v2"
MAX_RAW_BYTES = 256 * 1024 * 1024
_PACK_AS_BYTES = False


def pack_as_bytes() -> None:
    """For a process sending graphs through a pipe, not writing a checkpoint.

    A tensor crossing processes starts a PyTorch shared-memory manager, which
    inherits the sender's open pipes and keeps them open after the sender exits.
    """
    global _PACK_AS_BYTES
    _PACK_AS_BYTES = True


def pack_graph(state: dict[str, Any]) -> dict[str, Any] | tuple[str, int, Any]:
    """Keep the outer pickle memo compact, freeing each graph's raw buffers.

    The bound applies to compressed frames, not valid graph size: an unusually
    large graph retains the existing dictionary representation. Native restore
    remains responsible for complete graph-field and array validation.
    """
    if type(state) is not dict:
        raise TypeError("Numeric graph checkpoint state must be a dictionary")
    raw = pickle.dumps(state, protocol=5)
    if len(raw) > MAX_RAW_BYTES:
        return state
    compressed = zlib.compress(raw, level=1)
    if _PACK_AS_BYTES:
        return BYTES_SCHEMA, len(raw), compressed
    try:
        import torch
    except ImportError:
        # Plain Python/NumPy use can still pickle a graph without PyTorch.
        return BYTES_SCHEMA, len(raw), compressed
    # torch.save writes tensor storage as a streamed zip record. Keeping every
    # blob inside the outer data.pkl would duplicate the entire compressed
    # replay in its in-memory BytesIO buffer. The bytearray owns a separate
    # snapshot; changing this private wire tensor cannot mutate the graph.
    storage = torch.frombuffer(bytearray(compressed), dtype=torch.uint8)
    return SCHEMA, len(raw), storage


def unpack_graph(state: Any) -> dict[str, Any]:
    """Accept legacy dictionaries and validate one bounded compressed frame."""
    if isinstance(state, dict):
        return state
    if type(state) is not tuple or len(state) != 3:
        raise ValueError("Invalid compressed numeric graph envelope")
    schema, size, payload = state
    if type(schema) is not str or schema not in {SCHEMA, BYTES_SCHEMA}:
        raise ValueError("Unsupported compressed numeric graph schema")
    if type(size) is not int or not 0 < size <= MAX_RAW_BYTES:
        raise ValueError("Invalid compressed numeric graph raw length")
    if schema == BYTES_SCHEMA:
        if type(payload) is not bytes or not payload:
            raise ValueError("Compressed numeric graph payload must be immutable bytes")
    else:
        import torch
        if (type(payload) is not torch.Tensor or payload.device.type != "cpu"
                or payload.dtype != torch.uint8 or payload.ndim != 1 or payload.layout != torch.strided
                or payload.is_conj() or payload.is_neg()
                or not payload.is_contiguous() or not payload.numel()):
            raise ValueError("Compressed numeric graph storage must be a nonempty contiguous CPU uint8 vector")
        payload = memoryview(payload.numpy())
    decoder = zlib.decompressobj()
    try:
        raw = decoder.decompress(payload, size + 1)
    except zlib.error as error:
        raise ValueError("Corrupt compressed numeric graph payload") from error
    if len(raw) != size or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError("Compressed numeric graph length or stream boundary differs")
    stream = io.BytesIO(raw)
    try:
        value = pickle.Unpickler(stream).load()
    except (pickle.UnpicklingError, EOFError, ValueError, TypeError, AttributeError, ImportError) as error:
        raise ValueError("Invalid packed numeric graph pickle") from error
    if stream.read(1) or type(value) is not dict:
        raise ValueError("Numeric graph frame must contain exactly one dictionary")
    return value
