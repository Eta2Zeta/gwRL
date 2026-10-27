"""Exact container builder using independently validated source records.

The original target/mode/value checks and writers remain unchanged. Full source
grammar validation runs on every call in parallel; no source proof is cached.
The caller's existing torch.zeros initialization replaces a duplicate serial
zero loop. Value validation stays lazy in the original native-order branches.
"""
import threading

import torch

from .device_map_edits import SOURCE as REFERENCE_SOURCE


def _source():
    replacements=(
        ("device const long* suffix_usage[[buffer(20)]],uint thread_index[[thread_position_in_grid]]){",
         "device const long* suffix_usage[[buffer(20)]],device const bool* source_validated[[buffer(21)]],uint thread_index[[thread_position_in_grid]]){"),
        ("for(long i=0;i<R*5;++i)out[i]=0;", "// The public builder already initialized this complete buffer with torch.zeros."),
        ("!edit_tree(src,ends,remaining,previous)","!source_validated[lane]"),
    )
    source=REFERENCE_SOURCE
    for old,new in replacements:
        if source.count(old)!=1:raise RuntimeError("Audited container builder source changed")
        source=source.replace(old,new)
    return source


_lock=threading.Lock()
_library=None


def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:_library=torch.mps.compile_shader(_source())
    return _library
