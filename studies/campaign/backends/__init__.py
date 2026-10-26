"""Optional execution backends; the existing C++ CPU reference is the default.

Selecting a future GPU engine is separate from moving a neural network to a GPU.
No GPU implementation or dependency is imported or simulated by this registry.
"""
from .cpu import CPUBatchBackend, CPUScalarView
from .protocol import (BackendBuffer, BackendInfo, BackendSnapshot, CampaignBackend,
                       DecisionBatch, DecisionInspection, SNAPSHOT_SCHEMA)


def create_backend(envs, backend="cpu"):
    if backend != "cpu":
        raise ValueError(f"Campaign engine backend is unavailable: {backend!r}; available: cpu")
    return CPUBatchBackend(envs)


__all__ = ["BackendBuffer", "BackendInfo", "BackendSnapshot", "CampaignBackend", "CPUBatchBackend",
           "CPUScalarView", "DecisionBatch", "DecisionInspection", "SNAPSHOT_SCHEMA", "create_backend"]
