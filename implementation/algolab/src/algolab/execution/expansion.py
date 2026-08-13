"""Experiment expansion service (M1).

Deterministically materializes one run per (candidate x seed) plus one per
(baseline x seed) for an approved experiment, reserves budget up front
(all-or-nothing), and transitions the experiment to ``running``.

Idempotency: an expansion is keyed by (experiment, idempotency_key); a
repeat call returns the previously created runs. Config fingerprints
(prehashed in the ``runs.config_fingerprint`` UNIQUE column) additionally
prevent duplicate runs even across different keys.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from algolab.control.budget import BudgetLedger
from algolab.control.config import AlgolabConfig
from algolab.core.events import EventEnvelope
from algolab.core.ids import new_id
from algolab.storage.event_store import EventStore
from algolab.storage.repositories import CandidateRepository, ExperimentRepository
from algolab.storage.run_repository import RunNotFound, RunRepository, RunSpec
from algolab.workloads import get_workload


class ExpansionError(RuntimeError):
    """Base class for expansion failures."""


class ExperimentNotApproved(ExpansionError):
    """Only approved experiments can be expanded."""


class BudgetInsufficient(ExpansionError):
    """Expansion refused: credits or monetary caps would be exceeded."""


@dataclass(frozen=True)
class ExpansionResult:
    """Outcome of an expansion."""

    experiment_id: str
    idempotency_key: str
    run_ids: tuple[str, ...]
    created: int
    existing: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "idempotency_key": self.idempotency_key,
            "run_ids": list(self.run_ids),
            "created": self.created,
            "existing": self.existing,
        }


@dataclass(frozen=True)
class _RunPlan:
    seed: int
    config: dict[str, Any]
    fingerprint: str
    candidate_id: str | None
    is_baseline: bool


def config_fingerprint(*, experiment_id: str, workload: str, config: dict[str, Any],
                       seed: int, is_baseline: bool) -> str:
    """Deterministic content fingerprint for one run."""
    canonical = json.dumps(
        {
            "experiment_id": experiment_id,
            "workload": workload,
            "config": config,
            "seed": seed,
            "is_baseline": is_baseline,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class ExperimentExpansion:
    """All methods run inside the caller's transaction unless noted."""

    def __init__(self, conn: sqlite3.Connection, config: AlgolabConfig,
                 producer: str | None = None, trace_id: str | None = None) -> None:
        self._conn = conn
        self._config = config
        self._producer = producer or config.producer
        self._trace_id = trace_id

    def expand(self, experiment_id: str, idempotency_key: str) -> ExpansionResult:
        """Expand *experiment_id*; see module docstring for semantics.

        All-or-nothing: if any step (including budget reservation) fails,
        nothing is persisted.
        """
        if not idempotency_key or not isinstance(idempotency_key, str):
            raise ExpansionError("idempotency_key must be a non-empty string")

        existing = self._existing_expansion(experiment_id, idempotency_key)
        if existing is not None:
            return existing

        experiments = ExperimentRepository(self._conn, producer=self._producer)
        from algolab.storage.repositories import EntityNotFound

        try:
            status = experiments.status(experiment_id)
        except EntityNotFound as exc:
            raise RunNotFound(
                f"experiment {experiment_id} does not exist; "
                "cannot expand it into runs"
            ) from exc
        if status not in ("approved", "running"):
            raise ExperimentNotApproved(
                f"experiment {experiment_id} is not approved "
                f"(status {status!r}); only approved experiments can be "
                "expanded"
            )
        experiment = experiments.get(experiment_id)
        adapter = get_workload(self._config.execution.workload)

        plans = self._build_plans(experiment_id, experiment)

        # A *different* idempotency key that maps to the same fingerprints is
        # still idempotent: reuse the existing runs (never duplicate).
        existing_fingerprints = {
            str(row[0]) for row in self._conn.execute(
                "SELECT config_fingerprint FROM runs WHERE experiment_id = ?",
                (experiment_id,),
            )
        }
        new_plans = [
            p for p in plans if p.fingerprint not in existing_fingerprints
        ]
        if not new_plans:
            if not plans:
                raise ExpansionError("no runs to plan for this experiment")
            existing_run_ids = tuple(
                str(row[0]) for row in self._conn.execute(
                    "SELECT run_id FROM runs WHERE experiment_id = ? "
                    "ORDER BY rowid",
                    (experiment_id,),
                )
            )
            return ExpansionResult(
                experiment_id=experiment_id,
                idempotency_key=idempotency_key,
                run_ids=existing_run_ids,
                created=0,
                existing=len(plans),
            )
        self._plan_budget(new_plans, experiment)

        with self._conn:  # all-or-nothing
            ledger = BudgetLedger(self._conn, producer=self._producer)
            runs = RunRepository(self._conn, producer=self._producer,
                                 trace_id=self._trace_id)
            run_ids: list[str] = []
            for plan in plans:
                run_id = new_id("RUN")
                credits = self._estimate_credits(plan.config, adapter)
                reservation_id = ledger.reserve(
                    credits,
                    cost=0.0,
                    key=f"expand:{run_id}",
                    entity_id=run_id,
                    trace_id=self._trace_id,
                )
                runs.create(
                    RunSpec(
                        run_id=run_id,
                        experiment_id=experiment_id,
                        seed=plan.seed,
                        workload=self._config.execution.workload,
                        config=plan.config,
                        config_fingerprint=plan.fingerprint,
                        next_eligible_at=_now(),
                        candidate_id=plan.candidate_id,
                        is_baseline=plan.is_baseline,
                        priority=self._config.execution.priority_default,
                        max_attempts=self._config.execution.max_attempts,
                        reservation_id=reservation_id,
                        credits_reserved=credits,
                        cost_reserved=0.0,
                        trace_id=self._trace_id,
                    )
                )
                run_ids.append(run_id)
            self._record_expansion(experiment_id, idempotency_key, run_ids)
            self._append_expanded_event(
                experiment_id, idempotency_key, run_ids
            )
            if experiments.status(experiment_id) == "approved":
                experiments.transition(experiment_id, "running")
        return ExpansionResult(
            experiment_id=experiment_id,
            idempotency_key=idempotency_key,
            run_ids=tuple(run_ids),
            created=len(run_ids),
            existing=0,
        )

    # -- planning ---------------------------------------------------------

    def _build_plans(self, experiment_id: str, experiment: Any) -> list[_RunPlan]:
        adapter = get_workload(self._config.execution.workload)
        candidates = CandidateRepository(self._conn, producer=self._producer)
        plans: list[_RunPlan] = []
        seen: set[str] = set()
        workload = self._config.execution.workload

        def add(seed: int, config: dict[str, Any], candidate_id: str | None,
                is_baseline: bool) -> None:
            fingerprint = config_fingerprint(
                experiment_id=experiment_id,
                workload=workload,
                config=config,
                seed=seed,
                is_baseline=is_baseline,
            )
            if fingerprint in seen:
                return
            seen.add(fingerprint)
            plans.append(_RunPlan(
                seed=seed,
                config=config,
                fingerprint=fingerprint,
                candidate_id=candidate_id,
                is_baseline=is_baseline,
            ))

        for baseline_id in experiment.baseline_ids:
            changes = experiment.baseline_configs.get(baseline_id)
            if changes is None:
                changes = [{"baseline": baseline_id}]
            config = adapter.config_from_changes(changes)
            for seed in experiment.seeds:
                add(seed, config, None, True)
        for candidate_id in experiment.candidate_ids:
            candidate = candidates.get(candidate_id)
            config = adapter.config_from_changes(candidate.changes)
            for seed in experiment.seeds:
                add(seed, config, candidate_id, False)
        return plans

    def _plan_budget(self, plans: list[_RunPlan], experiment: Any) -> None:
        adapter = get_workload(self._config.execution.workload)
        total = 0.0
        for plan in plans:
            credits = self._estimate_credits(plan.config, adapter)
            if credits > self._config.budget.max_run_credits:
                raise BudgetInsufficient(
                    f"run for config {plan.fingerprint[:12]} needs {credits} "
                    f"credits, exceeding budget.max_run_credits "
                    f"({self._config.budget.max_run_credits})"
                )
            total += credits
        max_compute = experiment.budget.get("max_compute_credits")
        if isinstance(max_compute, (int, float)) and total > float(max_compute):
            raise BudgetInsufficient(
                f"expansion needs {total} credits, exceeding experiment "
                f"budget.max_compute_credits ({max_compute})"
            )
        ledger = BudgetLedger(self._conn, producer=self._producer)
        available = ledger.balance()["available_credits"]
        if total > available + 1e-9:
            raise BudgetInsufficient(
                f"expansion needs {total} credits; only {available} available"
            )

    def _estimate_credits(self, config: dict[str, Any], adapter: Any) -> float:
        units = float(adapter.estimate_compute_units(config))
        return round(units * self._config.budget.compute_credit_rate, 6)

    # -- idempotency ------------------------------------------------------

    def _existing_expansion(self, experiment_id: str,
                            idempotency_key: str) -> ExpansionResult | None:
        row = self._conn.execute(
            "SELECT run_ids FROM expansions WHERE experiment_id = ? "
            "AND idempotency_key = ?",
            (experiment_id, idempotency_key),
        ).fetchone()
        if row is None:
            return None
        run_ids = json.loads(row["run_ids"])
        assert isinstance(run_ids, list)
        return ExpansionResult(
            experiment_id=experiment_id,
            idempotency_key=idempotency_key,
            run_ids=tuple(str(r) for r in run_ids),
            created=0,
            existing=len(run_ids),
        )

    def _record_expansion(self, experiment_id: str, idempotency_key: str,
                          run_ids: list[str]) -> None:
        self._conn.execute(
            """
            INSERT INTO expansions
                (expansion_id, experiment_id, idempotency_key, run_ids,
                 producer, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (new_id("EVT"), experiment_id, idempotency_key,
             json.dumps(run_ids), self._producer, _now()),
        )

    def _append_expanded_event(self, experiment_id: str, idempotency_key: str,
                               run_ids: list[str]) -> None:
        EventStore(self._conn).append(
            EventEnvelope(
                entity_type="experiment",
                entity_id=experiment_id,
                mutation="expanded",
                new_state="running",
                payload={"idempotency_key": idempotency_key,
                         "run_ids": run_ids},
                producer=self._producer,
                trace_id=self._trace_id,
            )
        )


__all__ = [
    "ExpansionError",
    "ExperimentNotApproved",
    "BudgetInsufficient",
    "ExpansionResult",
    "ExperimentExpansion",
    "config_fingerprint",
]
