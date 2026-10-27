"""Original RNG-install checks/writes after a complete parallel device copy.

The caller initializes every output word, including unused padding, using a
bit-exact tensor clone. This variant removes only the original per-lane copy
loop; its validation, lazy errors, changed-word checks and writes are identical.
Publication and selected-cohort rollback remain in resident_chance_io.
"""
import threading

import torch

from .resident_chance_io import SOURCE as REFERENCE_SOURCE, _dummy


_MARKER = "kernel void install_chance_randomness("
_COPY = "device long* out=output+ulong(lane)*ulong(A)*5;for(long i=0;i<A*5;++i)out[i]=now[i];errors[lane]=0;"
if REFERENCE_SOURCE.count(_MARKER) != 1 or REFERENCE_SOURCE.count(_COPY) != 1:
    raise RuntimeError("Audited chance RNG installation kernel changed")
_PREFIX, _KERNEL = REFERENCE_SOURCE.split(_MARKER, 1)
SOURCE = _PREFIX + _MARKER + _KERNEL.replace(
    _COPY, "device long* out=output+ulong(lane)*ulong(A)*5;errors[lane]=0;", 1)

_library = None
_lock = threading.Lock()


def install(args, lanes):
    global _library
    if _library is None:
        with _lock:
            if _library is None:
                _library = torch.mps.compile_shader(SOURCE)
    _library.install_chance_randomness(
        *(value if value.numel() else _dummy() for value in args), threads=lanes)
