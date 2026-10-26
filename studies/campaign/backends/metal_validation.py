"""Measured exactness gates for privileged integer state on Apple GPUs.

Some installed MPS runtimes round int64 index_select payloads through float32.
Version guesses cannot establish lossless state support. Probe actual fixed bit
patterns once at explicit GPU initialization; CPU execution never needs a probe.
"""
from __future__ import annotations

from functools import lru_cache
import os

import torch


@lru_cache(maxsize=1)
def _probe():
    report = {"schema": "campaign-mps-int64-indexing-capability-v1", "torch": str(torch.__version__),
              "supported": False, "reason": "MPS unavailable"}
    if not torch.backends.mps.is_available():
        return report
    if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK", "0") not in {"", "0"}:
        return {**report, "reason": "MPS CPU fallback must be disabled before starting the process"}
    values = torch.tensor([0, 1, -1, 2**24 + 1, 2**31 + 1, 2**32 - 1,
                           -(2**31), 2**63 - 1, -(2**63)], dtype=torch.int64)
    indices = torch.tensor([5, 4, 3, 7, 8, 6, 2, 1, 0, 5], dtype=torch.int64)
    expected = values.index_select(0, indices)
    try:
        uploaded = values.to("mps")
        actual = uploaded.index_select(0, indices.to("mps"))
        torch.mps.synchronize()
        uploaded_cpu, actual_cpu = uploaded.cpu(), actual.cpu()
        upload_exact, gather_exact = torch.equal(values, uploaded_cpu), torch.equal(expected, actual_cpu)
        return {**report, "supported": upload_exact and gather_exact,
                "reason": "exact" if upload_exact and gather_exact else "MPS int64 upload/index_select changes integer payload bits",
                "upload_exact": upload_exact, "index_select_exact": gather_exact,
                "expected": expected.tolist(), "actual": actual_cpu.tolist()}
    except (RuntimeError, TypeError, NotImplementedError) as error:
        return {**report, "reason": f"MPS exact integer probe failed: {type(error).__name__}: {error}"}


def mps_int64_indexing_capability():
    """Explicit startup inspection; returns a detached cached probe witness."""
    report = _probe()
    return {key: list(value) if isinstance(value, list) else value for key, value in report.items()}


def mps_int64_indexing_supported():
    return bool(_probe()["supported"])


def require_lossless_mps_indexing():
    report = _probe()
    if not report["supported"]:
        raise RuntimeError("Lossless GPU campaign state requires exact MPS int64 indexing; "
            f"installed PyTorch {report['torch']} failed the measured capability check ({report['reason']}). "
            "Use the tested isolated GPU environment tmp/gpu-mps-env/bin/python, or select CPU explicitly. "
            "No CPU fallback or lossy integer cast is allowed.")
