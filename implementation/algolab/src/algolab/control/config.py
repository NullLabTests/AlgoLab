"""Strict configuration loading (YAML -> Pydantic).

Unknown keys fail validation (fail closed on misconfiguration).
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class BudgetConfig(BaseModel):
    """Budget caps. Monetary limits override compute-credit limits."""

    model_config = ConfigDict(extra="forbid")

    weekly_credits: float = Field(default=100.0, ge=0)
    lifetime_cap_credits: float = Field(default=5000.0, ge=0)
    max_run_credits: float = Field(default=200.0, ge=0)
    max_cost: float = Field(default=500.0, ge=0)
    currency: str = "USD"
    compute_credit_rate: float = Field(default=0.001, gt=0)


class StorageConfig(BaseModel):
    """Where the SQLite database and run artifacts live."""

    model_config = ConfigDict(extra="forbid")

    path: Path = Field(default=Path("data/algolab.sqlite3"))
    artifacts_dir: Path = Field(default=Path("artifacts"))


class ExecutionConfig(BaseModel):
    """Execution-plane tunables (M1)."""

    model_config = ConfigDict(extra="forbid")

    workload: str = "quadratic_optimizer"
    max_attempts: int = Field(default=2, ge=1)
    lease_seconds: float = Field(default=60.0, gt=0)
    heartbeat_interval_seconds: float = Field(default=10.0, gt=0)
    default_timeout_seconds: float = Field(default=120.0, gt=0)
    max_stdout_bytes: int = Field(default=1_048_576, gt=0)
    max_stderr_bytes: int = Field(default=1_048_576, gt=0)
    max_artifact_bytes: int = Field(default=10_485_760, gt=0)
    env_allowlist: list[str] = Field(
        default_factory=lambda: ["PATH", "PYTHONPATH", "LANG", "LC_ALL", "TMPDIR", "TZ"]
    )
    priority_default: int = 0


class RecoveryConfig(BaseModel):
    """Recovery behavior for orphaned runs (M1)."""

    model_config = ConfigDict(extra="forbid")

    requeue_backoff_seconds: float = Field(default=5.0, ge=0)


class AlgolabConfig(BaseModel):
    """Top-level configuration. Maps 1:1 to ``configs/algolab.yaml``."""

    model_config = ConfigDict(extra="forbid")

    storage: StorageConfig = Field(default_factory=StorageConfig)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    recovery: RecoveryConfig = Field(default_factory=RecoveryConfig)
    producer: str = "algolab"

    @model_validator(mode="after")
    def _consistency(self) -> AlgolabConfig:
        if self.budget.lifetime_cap_credits < self.budget.weekly_credits:
            raise ValueError(
                "budget.lifetime_cap_credits must be >= budget.weekly_credits"
            )
        if self.budget.max_run_credits > self.budget.lifetime_cap_credits:
            raise ValueError(
                "budget.max_run_credits must be <= budget.lifetime_cap_credits"
            )
        if (
            self.execution.max_attempts < 1
            or self.execution.lease_seconds <= 0
            or self.execution.heartbeat_interval_seconds <= 0
            or self.execution.default_timeout_seconds <= 0
        ):
            raise ValueError("execution limits must be positive")
        return self


def default_config() -> AlgolabConfig:
    return AlgolabConfig()


def load_config(path: Path | str) -> AlgolabConfig:
    """Load and validate a YAML config file.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: on invalid YAML or unknown/invalid keys.
    """
    p = Path(path)
    with open(p, encoding="utf-8") as fh:
        try:
            raw = yaml.safe_load(fh) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"invalid YAML in {p}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"config {p} must contain a mapping at the top level")
    try:
        return AlgolabConfig.model_validate(raw)
    except Exception as exc:  # pydantic.ValidationError
        raise ValueError(f"invalid config {p}: {exc}") from exc
