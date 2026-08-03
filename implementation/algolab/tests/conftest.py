"""Shared fixtures: in-memory SQLite database and valid manifest factories."""

from __future__ import annotations

from pathlib import Path

import pytest

from algolab.core.ids import new_id
from algolab.core.models import (
    Candidate,
    Discovery,
    Experiment,
    Hypothesis,
    Report,
    ReportClaim,
    Result,
    Run,
)
from algolab.storage.db import check_append_only, connect
from algolab.storage.repositories import (
    CandidateRepository,
    DiscoveryRepository,
    ExperimentRepository,
    HypothesisRepository,
    ReportRepository,
    ResultRepository,
    RunRepository,
)

CANONICAL_SCHEMAS_DIR = (
    Path(__file__).resolve().parents[3] / "schemas"
)
PACKAGE_SCHEMAS_DIR = (
    Path(__file__).resolve().parents[1] / "src" / "algolab" / "schemas"
)


@pytest.fixture
def conn():
    c = connect(":memory:", initialize=True)
    check_append_only(c)
    yield c
    c.close()


@pytest.fixture
def hyp_repo(conn) -> HypothesisRepository:
    return HypothesisRepository(conn, producer="test")


@pytest.fixture
def cand_repo(conn) -> CandidateRepository:
    return CandidateRepository(conn, producer="test")


@pytest.fixture
def exp_repo(conn) -> ExperimentRepository:
    return ExperimentRepository(conn, producer="test")


@pytest.fixture
def run_repo(conn) -> RunRepository:
    return RunRepository(conn, producer="test")


@pytest.fixture
def res_repo(conn) -> ResultRepository:
    return ResultRepository(conn, producer="test")


@pytest.fixture
def disc_repo(conn) -> DiscoveryRepository:
    return DiscoveryRepository(conn, producer="test")


@pytest.fixture
def rep_repo(conn) -> ReportRepository:
    return ReportRepository(conn, producer="test")


# -- factories -----------------------------------------------------------

def make_hypothesis(**overrides) -> Hypothesis:
    defaults: dict = {
        "id": new_id("HYP"),
        "schema_version": "1.0.0",
        "statement": "Replacing GELU with SwiGLU in small MLPs improves "
                     "validation accuracy on MNIST.",
        "mechanism": "Gating conditions the forward pass on input magnitude "
                     "and reduces dead neurons.",
        "baseline": "small_mlp/gelu",
        "primary_metric": "validation_accuracy",
        "predicted_effect": {"direction": "increase",
                             "minimum_relative_change": 0.005},
        "disconfirmation": "Validation accuracy fails to improve by at least "
                           "0.5% relative over five seeds.",
        "confounders": ["learning rate", "seed variation"],
        "status": "draft",
        "parent_ids": [],
    }
    defaults.update(overrides)
    return Hypothesis.model_validate(defaults)


def make_candidate(hypothesis_id: str, **overrides) -> Candidate:
    defaults: dict = {
        "id": new_id("CAND"),
        "schema_version": "1.0.0",
        "hypothesis_ids": [hypothesis_id],
        "parent_ids": [],
        "kind": "architecture",
        "changes": [{"component": "activation", "from": "gelu", "to": "swiglu"}],
        "expected_mechanism": "Gating reduces dead neurons and speeds "
                              "convergence.",
        "resource_delta": {"params": 0.01, "flops": 0.05},
        "validators": ["static_validation", "smoke_test"],
        "risks": [],
    }
    defaults.update(overrides)
    return Candidate.model_validate(defaults)


def make_experiment(hypothesis_id: str, candidate_id: str | None = None,
                    **overrides) -> Experiment:
    defaults: dict = {
        "id": new_id("EXP"),
        "schema_version": "1.0.0",
        "hypothesis_ids": [hypothesis_id],
        "candidate_ids": [candidate_id] if candidate_id else [],
        "baseline_ids": ["small_mlp/gelu"],
        "primary_metric": "validation_accuracy",
        "secondary_metrics": ["training_time", "peak_memory"],
        "seeds": [11, 23, 37, 41, 59],
        "budget": {"max_compute_credits": 1.0, "max_cost": 10.0,
                   "currency": "USD"},
        "stages": ["static_validation", "smoke_test",
                   "baseline_reproduction", "screening", "confirmation"],
        "stop_conditions": ["nan_loss", "budget_exceeded"],
        "status": "draft",
    }
    defaults.update(overrides)
    return Experiment.model_validate(defaults)


def make_run(experiment_id: str, **overrides) -> Run:
    defaults: dict = {
        "id": new_id("RUN"),
        "experiment_id": experiment_id,
        "seed": 11,
        "config": {"optimizer": "adamw", "lr": 1e-3},
        "environment_digest": "sha256:deadbeef",
    }
    defaults.update(overrides)
    return Run.model_validate(defaults)


def make_result(run_id: str, **overrides) -> Result:
    defaults: dict = {
        "id": new_id("RES"),
        "run_id": run_id,
        "metrics": {"validation_accuracy": 0.97},
        "anomalies": [],
    }
    defaults.update(overrides)
    return Result.model_validate(defaults)


def make_discovery(result_ids: list[str], candidate_id: str | None = None,
                   **overrides) -> Discovery:
    defaults: dict = {
        "id": new_id("DISC"),
        "candidate_ids": [candidate_id] if candidate_id else [new_id("CAND")],
        "result_ids": result_ids,
        "verdict": "tier_b",
        "justification": "Candidate passes improvement and replication gates "
                         "with bootstrap CI excluding zero.",
    }
    defaults.update(overrides)
    return Discovery.model_validate(defaults)


def make_report(evidence: list[str], **overrides) -> Report:
    defaults: dict = {
        "id": new_id("REP"),
        "title": "SwiGLU improves small MLPs on MNIST",
        "claims": [
            ReportClaim(
                statement="SwiGLU improves validation accuracy over GELU.",
                claim_type="discovery",
                evidence=evidence,
            )
        ],
    }
    defaults.update(overrides)
    return Report.model_validate(defaults)


def approve_experiment(exp_repo: ExperimentRepository, exp_id: str) -> None:
    exp_repo.transition(exp_id, "planned")
    exp_repo.transition(exp_id, "approved")
