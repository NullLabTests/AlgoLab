"""Pydantic runtime models for canonical entities (MASTER_SPEC.md §3).

Interchange manifests (Hypothesis, Candidate, Experiment) mirror the canonical
JSON Schemas exactly — the schemas are the authoritative contract and are
enforced by ``algolab.validation.schema_validator`` at the boundary. These
models add runtime ergonomics only.

Run, Result, Discovery, and Report have no canonical JSON Schema yet; their
models define the provisional v1 contract and enforce the ontology invariants
in ``algolab.storage.repositories``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from algolab.core.ids import InvalidID, require

SchemaVersion = Literal["1.0.0"]

HypothesisStatus = Literal[
    "draft", "vetting", "approved", "rejected", "tested", "archived"
]
CandidateKind = Literal[
    "architecture",
    "optimizer",
    "objective",
    "data",
    "inference",
    "memory",
    "routing",
    "compression",
    "composition",
]
EffectDirection = Literal["increase", "decrease"]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class _Provenance(BaseModel):
    """Immutable provenance attached at creation (never overwritten)."""

    model_config = {"extra": "forbid"}

    created_at: str = Field(default_factory=_utc_now)
    creator: str = "unknown"
    trace_id: str | None = None


class Hypothesis(BaseModel):
    """A falsifiable statement (schemas/hypothesis.schema.json)."""

    model_config = {"extra": "forbid"}

    id: str
    schema_version: SchemaVersion
    statement: str = Field(min_length=20)
    mechanism: str = Field(min_length=20)
    baseline: str
    primary_metric: str
    predicted_effect: dict[str, Any]
    disconfirmation: str
    confounders: list[str] = Field(default_factory=list)
    status: HypothesisStatus = "draft"
    parent_ids: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        return require(v, "HYP")

    @field_validator("predicted_effect")
    @classmethod
    def _effect(cls, v: dict[str, Any]) -> dict[str, Any]:
        if v.get("direction") not in ("increase", "decrease"):
            raise ValueError(
                "predicted_effect.direction must be "
                "'increase' or 'decrease'"
            )
        if not isinstance(v.get("minimum_relative_change"), (int, float)):
            raise ValueError(
                "predicted_effect.minimum_relative_change must "
                "be a number"
            )
        return v


class Candidate(BaseModel):
    """A versioned method change (schemas/candidate.schema.json)."""

    model_config = {"extra": "forbid"}

    id: str
    schema_version: SchemaVersion
    hypothesis_ids: list[str] = Field(min_length=1)
    parent_ids: list[str] = Field(default_factory=list)
    kind: CandidateKind
    changes: list[dict[str, Any]] = Field(min_length=1)
    expected_mechanism: str
    resource_delta: dict[str, Any] = Field(default_factory=dict)
    validators: list[str] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        return require(v, "CAND")

    @field_validator("hypothesis_ids", "parent_ids")
    @classmethod
    def _ids(cls, v: list[str]) -> list[str]:
        for item in v:
            require(item)
        return v


class Experiment(BaseModel):
    """A controlled comparison (schemas/experiment.schema.json)."""

    model_config = {"extra": "forbid"}

    id: str
    schema_version: SchemaVersion
    hypothesis_ids: list[str] = Field(min_length=1)
    candidate_ids: list[str] = Field(default_factory=list)
    baseline_ids: list[str] = Field(min_length=1)
    primary_metric: str
    secondary_metrics: list[str] = Field(default_factory=list)
    seeds: list[int] = Field(min_length=3)
    budget: dict[str, Any]
    stages: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)
    status: Literal[
        "draft", "planned", "approved", "running", "analyzing", "completed",
        "failed", "cancelled", "archived",
    ] = "draft"

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        return require(v, "EXP")

    @field_validator("hypothesis_ids", "candidate_ids")
    @classmethod
    def _ids(cls, v: list[str]) -> list[str]:
        # baseline_ids are identifiers/names (e.g. "small_mlp/sgd"), not IDs.
        for item in v:
            require(item)
        return v

    @model_validator(mode="after")
    def _budget(self) -> Experiment:
        budget = self.budget
        for key in ("max_compute_credits", "max_cost"):
            value = budget.get(key)
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"budget.{key} must be a non-negative number")
        return self


class Run(BaseModel):
    """One pinned execution (MASTER_SPEC.md §3). Provisional v1 contract."""

    model_config = {"extra": "forbid"}

    id: str
    experiment_id: str
    seed: int
    config: dict[str, Any] = Field(default_factory=dict)
    environment_digest: str | None = None
    status: Literal[
        "pending", "running", "completed", "failed", "cancelled"
    ] = "pending"
    credits_spent: float = 0.0
    notes: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        return require(v, "RUN")

    @field_validator("experiment_id")
    @classmethod
    def _exp_id(cls, v: str) -> str:
        return require(v, "EXP")

    @field_validator("credits_spent")
    @classmethod
    def _credits(cls, v: float) -> float:
        if v < 0:
            raise ValueError("credits_spent must be non-negative")
        return v


class Result(BaseModel):
    """Structured output of a run (MASTER_SPEC.md §3). Provisional v1 contract."""

    model_config = {"extra": "forbid"}

    id: str
    run_id: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    anomalies: list[str] = Field(default_factory=list)
    status: Literal["valid", "invalid", "flagged"] = "valid"

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        return require(v, "RES")

    @field_validator("run_id")
    @classmethod
    def _run_id(cls, v: str) -> str:
        return require(v, "RUN")


class Discovery(BaseModel):
    """A claim that passed all discovery gates (MASTER_SPEC.md §4). Provisional."""

    model_config = {"extra": "forbid"}

    id: str
    candidate_ids: list[str] = Field(min_length=1)
    result_ids: list[str] = Field(min_length=2)
    verdict: Literal["tier_a", "tier_b", "tier_c"] = "tier_b"
    justification: str = Field(min_length=10)

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        return require(v, "DISC")

    @field_validator("candidate_ids", "result_ids")
    @classmethod
    def _ids(cls, v: list[str]) -> list[str]:
        for item in v:
            require(item)
        return v


class ReportClaim(BaseModel):
    """A single claim inside a report (MASTER_SPEC.md §12: claims cite results)."""

    model_config = {"extra": "forbid"}

    statement: str = Field(min_length=10)
    claim_type: Literal["discovery", "negative_result", "observation"] = "observation"
    evidence: list[str] = Field(min_length=1)

    @field_validator("evidence")
    @classmethod
    def _evidence(cls, v: list[str]) -> list[str]:
        for item in v:
            require(item, "RES")
        return v


class Report(BaseModel):
    """A report whose claims are directly linked to evidence. Provisional."""

    model_config = {"extra": "forbid"}

    id: str
    title: str = Field(min_length=3)
    claims: list[ReportClaim] = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        return require(v, "REP")


__all__ = [
    "Hypothesis",
    "Candidate",
    "Experiment",
    "Run",
    "Result",
    "Discovery",
    "Report",
    "ReportClaim",
    "InvalidID",
]
