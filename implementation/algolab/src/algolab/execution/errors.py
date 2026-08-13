"""M1 error taxonomy (documented in ``docs/ERROR_CODES.md``).

Every failing run and every operation-level failure carries exactly one
``ErrorCode`` so operators and automation can branch on a stable enum rather
than message text.
"""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    """Stable, machine-readable failure taxonomy for AlgoLab M1."""
    INVALID_TRANSITION = "INVALID_TRANSITION"
    """A state transition was rejected by the run state machine."""

    CLAIM_CONFLICT = "CLAIM_CONFLICT"
    """A run could not be claimed because another worker already owns it."""

    LEASE_EXPIRED = "LEASE_EXPIRED"
    """A worker's claim lease expired; the run is considered orphaned."""

    TIMEOUT = "TIMEOUT"
    """The workload exceeded its configured timeout and was terminated."""

    CANCELLED = "CANCELLED"
    """The run was cancelled before completion."""

    # -- inputs / workloads ----------------------------------------------
    MANIFEST_INVALID = "MANIFEST_INVALID"
    """A manifest failed validation against its canonical JSON schema."""

    WORKLOAD_UNKNOWN = "WORKLOAD_UNKNOWN"
    """No workload adapter is registered under the requested name."""

    EXPERIMENT_NOT_APPROVED = "EXPERIMENT_NOT_APPROVED"
    """An experiment must be approved before it can be expanded."""

    # -- execution --------------------------------------------------------
    SUBPROCESS_FAILURE = "SUBPROCESS_FAILURE"
    """The workload subprocess exited with a non-zero exit code."""

    METRICS_MISSING = "METRICS_MISSING"
    """The workload did not produce a ``metrics.json`` file."""

    METRICS_INVALID = "METRICS_INVALID"
    """``metrics.json`` failed validation against the adapter schema."""

    ARTIFACT_MISSING = "ARTIFACT_MISSING"
    """Expected artifacts are absent or fail hash verification."""

    ARTIFACT_LIMIT_EXCEEDED = "ARTIFACT_LIMIT_EXCEEDED"
    """stdout/stderr or total artifact size exceeded configured limits."""

    # -- budget -----------------------------------------------------------
    BUDGET_INSUFFICIENT = "BUDGET_INSUFFICIENT"
    """Expansion was refused because credits or monetary caps were exceeded."""

    # -- recovery / infrastructure ----------------------------------------
    RECOVERY_CONFLICT = "RECOVERY_CONFLICT"
    """Recovery could not safely reconcile a run's persisted state."""

    ATTEMPTS_EXHAUSTED = "ATTEMPTS_EXHAUSTED"
    """An orphaned run exhausted its retry attempts and was failed."""

    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    """The referenced run does not exist."""

    DATABASE_ERROR = "DATABASE_ERROR"
    """A database-level failure occurred (schema, integrity, connection)."""


def describe(code: ErrorCode) -> str:
    """Human-readable one-line description of *code*."""
    return code.value.replace("_", " ").title()
