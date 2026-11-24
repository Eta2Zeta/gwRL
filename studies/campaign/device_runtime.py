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


# Network calls between cache releases. A release synchronizes and drops every
# compiled graph and cached buffer, which the next calls rebuild. Releasing
# every 32 calls, three or four times a second with 120 shared games, cost 17%
# of a 128x4 network's evaluations in the 2 November 2026 probes; about every
# 2,048 calls the rebuilding is negligible and the cache still stays bounded.
DEFAULT_CLEAR_EVERY = 2048


class MPSGraphCachePolicy:
    """One persistent counter shared by a learner's successive evaluators.

    completed() must run only after complete inference or backward/Adam work.
    It synchronizes before public cache release; live weights, optimizer tensors,
    input snapshots and random generators are untouched. Counters/timings are
    derived process-local state and must not enter learning checkpoints. A fresh
    controller or explicit restore reset starts with an empty compilation cache.

    A release must not run while another thread works on the device: on PyTorch
    2.14 a synchronize from one thread while another encodes MPS work aborts the
    process (failed assertion in setCurrentCommandEncoder). While a network
    update trains beside self-play, hold() keeps completed() counting without
    releasing, and release(), called once that thread has ended, releases if one
    came due.
    """
    def __init__(self, *, clear_every: int = DEFAULT_CLEAR_EVERY):
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
        self.held = False
        self.requested_clears = 0  # Releases between a network update's training steps.
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
        if self.pending_actor_forwards >= self.clear_every and not self.held:
            self._clear()
            return True
        return False

    def hold(self) -> None:
        """Keep counting, without releasing, while another thread works on the device."""
        self.held = True

    def release(self) -> bool:
        """After hold(), once no other thread works on the device: release if one came due."""
        self.held = False
        if self.pending_actor_forwards >= self.clear_every:
            self._clear()
            return True
        return False

    def release_now(self) -> None:
        """Release at once, held or not: for a thread that knows no other thread works on
        the device meanwhile, as the inference server does while a network update's
        trainer waits for it (SharedEvaluatorServer.release_between_steps)."""
        self._clear()
        self.requested_clears += 1

    def reset(self) -> None:
        """Call at a completed restore boundary; no learning state is reset."""
        self._clear()
        self.resets += 1

    def stats(self) -> dict:
        return {"schema": "campaign-mps-graph-cache-policy-v1", "torch": str(torch.__version__),
                "device": "mps", "clear_every_actor_forwards": self.clear_every,
                "total_actor_forwards": self.total_actor_forwards,
                "pending_actor_forwards": self.pending_actor_forwards,
                "clears": self.clears, "resets": self.resets, "requested_clears": self.requested_clears,
                "clear_seconds": self.clear_seconds,
                "checkpoint_scope": "Derived process-local cache state; counters reset on fresh construction and pending count resets after restore"}


def runtime_policy_for_device(device, *, clear_every: int = DEFAULT_CLEAR_EVERY) -> MPSGraphCachePolicy | None:
    target = torch.device(device)
    if target.type in {"cpu", "cuda"}:
        return None
    if target.type != "mps" or target.index not in (None, 0):
        raise ValueError("Runtime cache policy supports explicit cpu, mps or cuda devices")
    return MPSGraphCachePolicy(clear_every=clear_every)
