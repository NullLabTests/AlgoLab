"""Workload adapter registry (M1).

Importing this package registers the built-in workloads; custom adapters can
be added in the future via ``register_workload``.
"""

from __future__ import annotations

from algolab.workloads.base import (
    ArtifactsInvalid,
    ConfigInvalid,
    MetricsInvalid,
    WorkloadAdapter,
    WorkloadError,
    WorkloadUnknownError,
    get_workload,
    list_workloads,
    register_workload,
)
from algolab.workloads.quadratic_optimizer import QuadraticOptimizerAdapter

register_workload(QuadraticOptimizerAdapter())

__all__ = [
    "ArtifactsInvalid",
    "ConfigInvalid",
    "MetricsInvalid",
    "WorkloadAdapter",
    "WorkloadError",
    "WorkloadUnknownError",
    "get_workload",
    "list_workloads",
    "register_workload",
]
