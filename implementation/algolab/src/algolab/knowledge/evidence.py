"""Evidence records: the scientific backbone of AlgoLab (MASTER_SPEC.md §8).

An Evidence record is an immutable, append-only observation created by the
M1 experimental pipeline when an operator is applied to a task: candidate
vs baseline measurements on the task's primary metric, the statistical
analysis (delta, CI, p-value, effect size), the promotion outcome against
the task's evidence threshold, and the credits charged to the search
budget.

Records carry novelty status (novel = the proposal target was untested at
record time for this task-family) and replication status (exact replication
of an earlier record), which the cooperative layer uses to answer "has
anyone already tried this?".

Integrity: every Evidence is append-only (DB-level triggers), requires a
per-task direction-consistent outcome, and is keyed by a deterministic UUID
for idempotent replay.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..storage.db import DatabaseError
from ..util import utc_now

PROMOTE = "promote"
REJECT = "reject"
OUTCOMES = (PROMOTE, REJECT)


class EvidenceIntegrityError(DatabaseError):
    """An evidence record violates an integrity constraint."""


@dataclass(frozen=True)
class Evidence:
    """One immutable experimental observation on a task's primary metric.

    ``payload`` carries the raw per-seed measurements and any other
    provenance (always as a JSON-encodable dict).
    """

    task_id: str
    experiment_id: str
    hypothesis_id: str
    candidate_id: str
    operator_name: str
    policy: str
    primary_metric: str
    direction: str
    outcome: str
    promotion_threshold: float
    credits_charged: float
    novel: bool
    replication_status: str
    payload: dict[str, Any] = field(default_factory=dict)
    baseline_mean: float = 0.0
    candidate_mean: float = 0.0
    relative_delta: float = 0.0
    ci_low: float = 0.0
    ci_high: float = 0.0
    p_value: float = 0.0
    effect_size: float = 0.0
    episode_id: str | None = None
    evidence_id: str | None = None
    created_at: str | None = None
    producer: str | None = None

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOMES:
            raise EvidenceIntegrityError(
                f"outcome must be one of {OUTCOMES}, got {self.outcome!r}"
            )
        if self.direction not in ("minimize", "maximize"):
            raise EvidenceIntegrityError(
                f"direction must be minimize or maximize, got {self.direction!r}"
            )
        if self.credits_charged < 0:
            raise EvidenceIntegrityError("credits_charged must be non-negative")
        if self.promotion_threshold <= 0:
            raise EvidenceIntegrityError(
                "promotion_threshold must be positive"
            )
        if self.novel and self.replication_status:
            raise EvidenceIntegrityError(
                "novel records must have replication_status ''"
            )
        if not self.novel and not self.replication_status:
            raise EvidenceIntegrityError(
                "non-novel records require a replication_status"
            )

    @property
    def is_promotion(self) -> bool:
        """True if this record promoted the proposal to default."""
        return self.outcome == PROMOTE

    def sign(self) -> float:
        """+1 if the outcome favors improvement, -1 otherwise, in the
        metric's direction."""
        improved = self.relative_delta * (
            -1.0 if self.direction == "minimize" else 1.0
        )
        return 1.0 if improved > 0 and self.is_promotion else -1.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "task_id": self.task_id,
            "experiment_id": self.experiment_id,
            "hypothesis_id": self.hypothesis_id,
            "candidate_id": self.candidate_id,
            "episode_id": self.episode_id,
            "operator_name": self.operator_name,
            "policy": self.policy,
            "primary_metric": self.primary_metric,
            "direction": self.direction,
            "baseline_mean": self.baseline_mean,
            "candidate_mean": self.candidate_mean,
            "relative_delta": self.relative_delta,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "p_value": self.p_value,
            "effect_size": self.effect_size,
            "promotion_threshold": self.promotion_threshold,
            "outcome": self.outcome,
            "credits_charged": self.credits_charged,
            "novel": self.novel,
            "replication_status": self.replication_status,
            "created_at": self.created_at,
            "producer": self.producer,
            "payload": self.payload,
        }


class EvidenceRepo:
    """Append-only store for Evidence records.

    Enforces the per-task invariant: exactly the promotion_threshold
    configuration and direction must match the task the record claims; the
    caller passes the task's config explicitly.
    """

    def __init__(self, conn: sqlite3.Connection, producer: str = "m1"):
        self._conn = conn
        self._producer = producer

    def _insert_dict(self, d: dict[str, Any]) -> dict[str, Any]:
        c = self._conn.cursor()
        try:
            c.execute(
                "INSERT INTO evidence (evidence_id, task_id, experiment_id,"
                " hypothesis_id, candidate_id, episode_id, operator_name,"
                " policy, primary_metric, direction, baseline_mean,"
                " candidate_mean, relative_delta, ci_low, ci_high, p_value,"
                " effect_size, promotion_threshold, outcome, credits_charged,"
                " novelty, replication_status, created_at, producer, payload)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    d["evidence_id"],
                    d["task_id"],
                    d["experiment_id"],
                    d["hypothesis_id"],
                    d["candidate_id"],
                    d["episode_id"],
                    d["operator_name"],
                    d["policy"],
                    d["primary_metric"],
                    d["direction"],
                    d["baseline_mean"],
                    d["candidate_mean"],
                    d["relative_delta"],
                    d["ci_low"],
                    d["ci_high"],
                    d["p_value"],
                    d["effect_size"],
                    d["promotion_threshold"],
                    d["outcome"],
                    d["credits_charged"],
                    int(d["novel"]),
                    d["replication_status"],
                    d["created_at"],
                    d["producer"],
                    json.dumps(d["payload"]),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise EvidenceIntegrityError(
                f"append-only violation or duplicate record: {exc}"
            ) from exc
        return d

    def insert(
        self,
        task_id: str,
        experiment_id: str,
        operator_name: str,
        policy: str,
        primary_metric: str,
        direction: str,
        outcome: str,
        promotion_threshold: float,
        credits_charged: float,
        novel: bool,
        replication_status: str = "",
        *,
        hypothesis_id: str = "",
        candidate_id: str = "",
        baseline_mean: float = 0.0,
        candidate_mean: float = 0.0,
        relative_delta: float = 0.0,
        ci_low: float = 0.0,
        ci_high: float = 0.0,
        p_value: float = 1.0,
        effect_size: float = 0.0,
        episode_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Evidence:
        """Insert one evidence record (append-only)."""
        rec = Evidence(
            task_id=task_id,
            experiment_id=experiment_id,
            hypothesis_id=hypothesis_id or f"h-{uuid.uuid4().hex[:8]}",
            candidate_id=candidate_id or f"c-{uuid.uuid4().hex[:8]}",
            operator_name=operator_name,
            policy=policy,
            primary_metric=primary_metric,
            direction=direction,
            outcome=outcome,
            promotion_threshold=promotion_threshold,
            credits_charged=credits_charged,
            novel=novel,
            replication_status=replication_status,
            payload=payload or {},
            baseline_mean=baseline_mean,
            candidate_mean=candidate_mean,
            relative_delta=relative_delta,
            ci_low=ci_low,
            ci_high=ci_high,
            p_value=p_value,
            effect_size=effect_size,
            episode_id=episode_id,
            evidence_id=f"ev-{uuid.uuid4().hex[:24]}",
            created_at=utc_now(),
            producer=self._producer,
        )
        self._insert_dict(rec.as_dict())
        return rec

    def by_id(self, evidence_id: str) -> Evidence | None:
        row = self._conn.execute(
            "SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)
        ).fetchone()
        return self._row_to_evidence(row) if row else None

    def latest(self, task_id: str | None = None) -> Evidence | None:
        if task_id is None:
            row = self._conn.execute(
                "SELECT * FROM evidence ORDER BY created_at DESC, rowid DESC"
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM evidence WHERE task_id = ?"
                " ORDER BY created_at DESC, rowid DESC",
                (task_id,),
            ).fetchone()
        return self._row_to_evidence(row) if row else None

    def history(self, task_id: str, limit: int = 100) -> list[Evidence]:
        rows = self._conn.execute(
            "SELECT * FROM evidence WHERE task_id = ?"
            " ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (task_id, limit),
        ).fetchall()
        return [self._row_to_evidence(r) for r in rows]

    def _row_to_evidence(self, row: sqlite3.Row) -> Evidence:
        cols = [
            c[0]
            for c in self._conn.execute("SELECT * FROM evidence").description
        ]
        d = dict(zip(cols, row, strict=True))
        return Evidence(
            task_id=d["task_id"],
            experiment_id=d["experiment_id"],
            hypothesis_id=d["hypothesis_id"],
            candidate_id=d["candidate_id"],
            episode_id=d["episode_id"],
            operator_name=d["operator_name"],
            policy=d["policy"],
            primary_metric=d["primary_metric"],
            direction=d["direction"],
            outcome=d["outcome"],
            promotion_threshold=float(d["promotion_threshold"]),
            credits_charged=float(d["credits_charged"]),
            novel=bool(d["novelty"]),
            replication_status=d["replication_status"],
            payload=json.loads(d["payload"] or "{}"),
            baseline_mean=float(d["baseline_mean"] or 0.0),
            candidate_mean=float(d["candidate_mean"] or 0.0),
            relative_delta=float(d["relative_delta"] or 0.0),
            ci_low=float(d["ci_low"] or 0.0),
            ci_high=float(d["ci_high"] or 0.0),
            p_value=float(d["p_value"] or 0.0),
            effect_size=float(d["effect_size"] or 0.0),
            evidence_id=d["evidence_id"],
            created_at=d["created_at"],
            producer=d["producer"],
        )

    def supports(self) -> str:
        """Whether the evidences are used to support the claim."""
        return "scientific-evidence"
