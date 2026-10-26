"""Derived MPS compilation-cache housekeeping for long-running neural work.

PyTorch 2.13 added MPSGraph cache release to the public empty_cache API. Earlier
MPS runtimes can retain native compilation graphs for each distinct shape even
after their tensor/Python caches are cleared. CPU and CUDA execution are unchanged.
"""
from __future__ import annotations

import os
import re
import time

import torch


def mps_graph_cache_supported(version: str | None = None) -> bool:
    """Require a stable release with the public graph-cache cleanup fix."""
    value = str(torch.__version__ if version is None else version)
    matched = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:\+[^\s]+)?", value)
    return matched is not None and tuple(map(int, matched.groups())) >= (2, 13, 0)


class MPSGraphCachePolicy:
    """One persistent counter shared by a learner's successive evaluators.

    completed() must run only after complete inference or backward/Adam work.
    It synchronizes before public cache release; live weights, optimizer tensors,
    input snapshots and random generators are untouched. Counters/timings are
    derived process-local state and must not enter learning checkpoints. A fresh
    controller or explicit restore reset starts with an empty compilation cache.
    """
    def __init__(self, *, clear_every: int = 32):
        if type(clear_every) is not int or clear_every <= 0:
            raise ValueError("MPS cache interval must be a positive integer")
        if not mps_graph_cache_supported():
            raise ValueError("Long-running MPS execution requires stable PyTorch 2.13+ with public graph-cache cleanup; use the isolated GPU environment")
        if not torch.backends.mps.is_available():
            raise ValueError("The requested MPS runtime is unavailable")
        for name in ("PYTORCH_ENABLE_MPS_FALLBACK", "PYTORCH_MPS_FAST_MATH"):
            if os.environ.get(name, "0") not in {"", "0"}:
                raise ValueError(f"Long-running MPS execution requires {name}=0")
        self.device = torch.device("mps")
        self.clear_every = clear_every
        self.total_actor_forwards = 0
        self.pending_actor_forwards = 0
        self.clears = 0
        self.resets = 0
        self.clear_seconds = 0.0
        self.reset()

    def _clear(self) -> None:
        started = time.perf_counter()
        torch.mps.synchronize()
        torch.mps.empty_cache()
        self.clear_seconds += time.perf_counter() - started
        self.clears += 1
        self.pending_actor_forwards = 0

    def completed(self, actor_forwards: int = 1) -> bool:
        if type(actor_forwards) is not int or actor_forwards <= 0:
            raise ValueError("Completed MPS actor forwards must be a positive integer")
        self.total_actor_forwards += actor_forwards
        self.pending_actor_forwards += actor_forwards
        if self.pending_actor_forwards >= self.clear_every:
            self._clear()
            return True
        return False

    def reset(self) -> None:
        """Call at a completed restore boundary; no learning state is reset."""
        self._clear()
        self.resets += 1

    def stats(self) -> dict:
        return {"schema": "campaign-mps-graph-cache-policy-v1", "torch": str(torch.__version__),
                "device": "mps", "clear_every_actor_forwards": self.clear_every,
                "total_actor_forwards": self.total_actor_forwards,
                "pending_actor_forwards": self.pending_actor_forwards,
                "clears": self.clears, "resets": self.resets, "clear_seconds": self.clear_seconds,
                "checkpoint_scope": "Derived process-local cache state; counters reset on fresh construction and pending count resets after restore"}


def runtime_policy_for_device(device, *, clear_every: int = 32) -> MPSGraphCachePolicy | None:
    target = torch.device(device)
    if target.type in {"cpu", "cuda"}:
        return None
    if target.type != "mps" or target.index not in (None, 0):
        raise ValueError("Runtime cache policy supports explicit cpu, mps or cuda devices")
    return MPSGraphCachePolicy(clear_every=clear_every)
