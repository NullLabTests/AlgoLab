"""Workload adapter contract (M1; see ``docs/WORKLOAD_ADAPTERS.md``).

A workload adapter maps a candidate's abstract changes onto a concrete,
deterministic, subprocess-isolated command line. The worker executes
``command()`` with ``shell=False``, a controlled environment, and an
explicit timeout, then validates the produced ``metrics.json``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class WorkloadError(RuntimeError):
    """Base class for workload adapter failures."""


class ConfigInvalid(WorkloadError):
    """A workload configuration is invalid (fail closed)."""


class MetricsInvalid(WorkloadError):
    """Produced metrics failed validation against the adapter schema."""


class ArtifactsInvalid(WorkloadError):
    """Expected artifacts are missing or corrupt."""


class WorkloadUnknownError(WorkloadError):
    """No adapter registered under the requested name."""


class WorkloadAdapter(ABC):
    """Typed interface every workload must implement."""

    name: str = ""
    version: str = "1.0.0"
    description: str = ""

    @abstractmethod
    def defaults(self) -> dict[str, Any]:
        """Deterministic default configuration (baseline behavior)."""

    @abstractmethod
    def config_from_changes(self, changes: list[dict[str, Any]]) -> dict[str, Any]:
        """Derive a workload config from a candidate manifest's ``changes``.

        Unrelated keys in ``changes`` are ignored; known keys are validated
        and override defaults. Raises :class:`ConfigInvalid` on bad values.
        """

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> None:
        """Fail closed on malformed configs."""

    @abstractmethod
    def command(self, run_dir: Path, config: dict[str, Any], seed: int
                ) -> list[str]:
        """Return the argv list for the workload subprocess.

        ``shell=False``; no interpolation, no user-controlled shell strings.
        The workload reads its config from ``run_dir/resolved_config.json``
        and must write ``run_dir/metrics.json``.
        """

    @abstractmethod
    def timeout_seconds(self, config: dict[str, Any]) -> float:
        """Explicit execution timeout for this config."""

    @abstractmethod
    def estimate_compute_units(self, config: dict[str, Any]) -> float:
        """Deterministic cost estimate used for budget reservations."""

    @abstractmethod
    def validate_metrics(self, metrics: dict[str, Any]) -> None:
        """Validate produced metrics; raise :class:`MetricsInvalid`."""

    @property
    @abstractmethod
    def expected_artifacts(self) -> tuple[str, ...]:
        """Files the workload must produce inside the run directory."""

    def validate_expected_artifacts(self, run_dir: Path) -> None:
        """Check that all expected artifacts exist."""
        for name in self.expected_artifacts:
            if not (run_dir / name).is_file():
                raise ArtifactsInvalid(
                    f"expected artifact {name!r} missing in {run_dir}"
                )


_registry: dict[str, WorkloadAdapter] = {}


def register_workload(adapter: WorkloadAdapter) -> None:
    """Register a workload adapter by its name."""
    if not adapter.name:
        raise WorkloadError("cannot register a workload without a name")
    _registry[adapter.name] = adapter


def get_workload(name: str) -> WorkloadAdapter:
    """Look up a registered adapter; raise :class:`WorkloadUnknownError`."""
    try:
        return _registry[name]
    except KeyError as exc:
        raise WorkloadUnknownError(
            f"no workload adapter named {name!r}; available: "
            f"{sorted(_registry)}"
        ) from exc


def list_workloads() -> list[str]:
    """Names of all registered adapters."""
    return sorted(_registry)
