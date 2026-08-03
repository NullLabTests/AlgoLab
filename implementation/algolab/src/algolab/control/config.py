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


class StorageConfig(BaseModel):
    """Where the SQLite database lives."""

    model_config = ConfigDict(extra="forbid")

    path: Path = Field(default=Path("data/algolab.sqlite3"))


class AlgolabConfig(BaseModel):
    """Top-level configuration. Maps 1:1 to ``configs/algolab.yaml``."""

    model_config = ConfigDict(extra="forbid")

    storage: StorageConfig = Field(default_factory=StorageConfig)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
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
