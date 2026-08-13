"""Entity repositories enforcing the Core Ontology invariants
(spec/foundation/001_CORE_ONTOLOGY.md).

Every mutation writes the data row AND an audit event in the same
transaction. Payloads (manifests) are immutable; the ``status`` column is the
only mutable field and changes only through an allowed state-machine
transition.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from algolab.core.events import EventEnvelope
from algolab.core.ids import require
from algolab.core.models import (
    Candidate,
    Discovery,
    Experiment,
    Hypothesis,
    Report,
    Result,
)
from algolab.core.state import EXPERIMENT_MACHINE, StateMachine
from algolab.storage.event_store import EventStore
from algolab.validation.schema_validator import validate_manifest

_SCHEMA_VERSION = "1.0.0"

_ENTITY_WITH_SCHEMA = ("hypothesis", "candidate", "experiment")


class RepositoryError(RuntimeError):
    """Base class for repository failures."""


class EntityNotFound(RepositoryError):
    """No such entity."""


class InvariantViolation(RepositoryError):
    """An ontology invariant or referential integrity rule was violated."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _kind_to_type(prefix: str) -> str:
    return {
        "HYP": "hypothesis",
        "CAND": "candidate",
        "EXP": "experiment",
        "RUN": "run",
        "RES": "result",
        "DISC": "discovery",
        "REP": "report",
    }[prefix]


class _BaseRepository:
    """Shared persistence helpers. All methods operate on an open connection
    and are executed inside the caller's transaction."""

    def __init__(self, conn: sqlite3.Connection, producer: str = "algolab",
                 trace_id: str | None = None) -> None:
        self._conn = conn
        self._producer = producer
        self._trace_id = trace_id

    # -- persistence primitives ------------------------------------------

    def _insert_entity(self, *, entity_type: str, schema_version: str,
                       status: str, payload: dict[str, Any]) -> None:
        entity_id = payload["id"]
        require(entity_id)
        self._conn.execute(
            """
            INSERT INTO entities
                (entity_id, entity_type, schema_version, status, payload,
                 created_at, creator, trace_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity_id,
                entity_type,
                schema_version,
                status,
                json.dumps(payload, sort_keys=True),
                _now(),
                self._producer,
                self._trace_id,
            ),
        )

    def _entity(self, entity_id: str) -> sqlite3.Row:
        row: sqlite3.Row | None = self._conn.execute(
            "SELECT * FROM entities WHERE entity_id = ?", (entity_id,)
        ).fetchone()
        if row is None:
            raise EntityNotFound(f"no entity {entity_id}")
        return row

    def _load_payload(self, entity_id: str) -> dict[str, Any]:
        payload = json.loads(self._entity(entity_id)["payload"])
        assert isinstance(payload, dict)
        return payload

    def _expect_type(self, entity_id: str, expected: str) -> None:
        row = self._entity(entity_id)
        if row["entity_type"] != expected:
            raise InvariantViolation(
                f"entity {entity_id} is a {row['entity_type']}, expected {expected}"
            )

    def _require_exists(self, entity_id: str, expected_type: str | None = None,
                        what: str = "referenced entity") -> None:
        if expected_type == "run":
            # M1: runs live in the structured `runs` table, not `entities`.
            row = self._conn.execute(
                "SELECT run_id FROM runs WHERE run_id = ?", (entity_id,)
            ).fetchone()
            if row is None:
                raise InvariantViolation(
                    f"{what} {entity_id} does not exist"
                )
            return
        try:
            row = self._entity(entity_id)
        except EntityNotFound as exc:
            raise InvariantViolation(
                f"{what} {entity_id} does not exist"
            ) from exc
        if expected_type is not None and row["entity_type"] != expected_type:
            raise InvariantViolation(
                f"{what} {entity_id} is a {row['entity_type']}, "
                f"expected {expected_type}"
            )

    def _require_status(self, entity_id: str, expected: str, what: str) -> None:
        row = self._entity(entity_id)
        if row["status"] != expected:
            raise InvariantViolation(
                f"{what} {entity_id} has status {row['status']!r}, "
                f"expected {expected!r}"
            )

    def _transition(self, entity_id: str, machine: StateMachine, target: str,
                    *, expected_type: str) -> None:
        """Apply a lifecycle transition atomically with its audit event."""
        row = self._entity(entity_id)
        self._expect_type(entity_id, expected_type)
        current = row["status"]
        machine.require_transition(current, target)  # raises before any write
        self._conn.execute(
            "UPDATE entities SET status = ? WHERE entity_id = ?",
            (target, entity_id),
        )
        EventStore(self._conn).append(
            EventEnvelope(
                entity_type=expected_type,
                entity_id=entity_id,
                mutation="status_changed",
                old_state=current,
                new_state=target,
                producer=self._producer,
                trace_id=self._trace_id,
            )
        )

    def _current_status(self, entity_id: str) -> str:
        return str(self._entity(entity_id)["status"])

    def _get_payload(self, entity_id: str, expected_type: str) -> dict[str, Any]:
        self._expect_type(entity_id, expected_type)
        return self._load_payload(entity_id)


class HypothesisRepository(_BaseRepository):
    def create(self, hypothesis: Hypothesis) -> str:
        manifest = hypothesis.model_dump(mode="json")
        validate_manifest(manifest, "hypothesis")

        for parent in hypothesis.parent_ids:
            self._require_exists(parent, "hypothesis", what="parent hypothesis")
        self._insert_entity(
            entity_type="hypothesis",
            schema_version=_SCHEMA_VERSION,
            status=hypothesis.status,
            payload=manifest,
        )
        EventStore(self._conn).append(
            EventEnvelope(
                entity_type="hypothesis",
                entity_id=hypothesis.id,
                mutation="created",
                new_state=hypothesis.status,
                payload={"schema_version": _SCHEMA_VERSION},
                producer=self._producer,
                trace_id=self._trace_id,
            )
        )
        return hypothesis.id

    def get(self, hypothesis_id: str) -> Hypothesis:
        return Hypothesis.model_validate(
            self._get_payload(hypothesis_id, "hypothesis")
        )


class CandidateRepository(_BaseRepository):
    def create(self, candidate: Candidate) -> str:
        manifest = candidate.model_dump(mode="json")
        validate_manifest(manifest, "candidate")
        for hid in candidate.hypothesis_ids:
            self._require_exists(hid, "hypothesis",
                                 what="motivating hypothesis")
        for pid in candidate.parent_ids:
            self._require_exists(pid, "candidate", what="parent candidate")
        self._insert_entity(
            entity_type="candidate",
            schema_version=_SCHEMA_VERSION,
            status="draft",
            payload=manifest,
        )
        EventStore(self._conn).append(
            EventEnvelope(
                entity_type="candidate",
                entity_id=candidate.id,
                mutation="created",
                new_state="draft",
                payload={"schema_version": _SCHEMA_VERSION},
                producer=self._producer,
                trace_id=self._trace_id,
            )
        )
        return candidate.id

    def get(self, candidate_id: str) -> Candidate:
        return Candidate.model_validate(
            self._get_payload(candidate_id, "candidate")
        )


class ExperimentRepository(_BaseRepository):
    def create(self, experiment: Experiment) -> str:
        manifest = experiment.model_dump(mode="json")
        validate_manifest(manifest, "experiment")
        for hid in experiment.hypothesis_ids:
            self._require_exists(hid, "hypothesis",
                                 what="tested hypothesis")
        for cid in experiment.candidate_ids:
            self._require_exists(cid, "candidate", what="tested candidate")
        self._insert_entity(
            entity_type="experiment",
            schema_version=_SCHEMA_VERSION,
            status=experiment.status,
            payload=manifest,
        )
        EventStore(self._conn).append(
            EventEnvelope(
                entity_type="experiment",
                entity_id=experiment.id,
                mutation="created",
                new_state=experiment.status,
                payload={"schema_version": _SCHEMA_VERSION},
                producer=self._producer,
                trace_id=self._trace_id,
            )
        )
        return experiment.id

    def get(self, experiment_id: str) -> Experiment:
        payload = self._get_payload(experiment_id, "experiment")
        payload["status"] = self._current_status(experiment_id)
        return Experiment.model_validate(payload)

    def transition(self, experiment_id: str, target: str) -> str:
        self._transition(experiment_id, EXPERIMENT_MACHINE, target,
                         expected_type="experiment")
        return target

    def status(self, experiment_id: str) -> str:
        self._expect_type(experiment_id, "experiment")
        return self._current_status(experiment_id)


class ResultRepository(_BaseRepository):
    def create(self, result: Result) -> str:
        self._require_exists(result.run_id, "run", what="run of result")
        self._insert_entity(
            entity_type="result",
            schema_version=_SCHEMA_VERSION,
            status=result.status,
            payload=result.model_dump(mode="json"),
        )
        EventStore(self._conn).append(
            EventEnvelope(
                entity_type="result",
                entity_id=result.id,
                mutation="created",
                new_state=result.status,
                payload={"run_id": result.run_id},
                producer=self._producer,
                trace_id=self._trace_id,
            )
        )
        return result.id

    def get(self, result_id: str) -> Result:
        return Result.model_validate(
            self._get_payload(result_id, "result")
        )


class DiscoveryRepository(_BaseRepository):
    def create(self, discovery: Discovery) -> str:
        for rid in discovery.result_ids:
            self._require_exists(rid, "result", what="supporting result")
        # Ontology invariant 4: replication evidence = results from >= 2
        # distinct runs.
        run_ids = {self._result_run_id(rid) for rid in discovery.result_ids}
        if len(run_ids) < 2:
            raise InvariantViolation(
                f"discovery {discovery.id} lacks replication evidence: all "
                f"supporting results come from a single run ({run_ids})"
            )
        for cid in discovery.candidate_ids:
            self._require_exists(cid, "candidate", what="discovered candidate")
        self._insert_entity(
            entity_type="discovery",
            schema_version=_SCHEMA_VERSION,
            status="declared",
            payload=discovery.model_dump(mode="json"),
        )
        EventStore(self._conn).append(
            EventEnvelope(
                entity_type="discovery",
                entity_id=discovery.id,
                mutation="created",
                new_state="declared",
                payload={"result_ids": discovery.result_ids,
                         "run_ids": sorted(run_ids)},
                producer=self._producer,
                trace_id=self._trace_id,
            )
        )
        return discovery.id

    def get(self, discovery_id: str) -> Discovery:
        return Discovery.model_validate(
            self._get_payload(discovery_id, "discovery")
        )

    def _result_run_id(self, result_id: str) -> str:
        row = self._entity(result_id)
        return str(json.loads(row["payload"])["run_id"])


class ReportRepository(_BaseRepository):
    def create(self, report: Report) -> str:
        for claim in report.claims:
            for evidence_id in claim.evidence:
                self._require_exists(evidence_id, "result",
                                     what="evidence for claim")
        self._insert_entity(
            entity_type="report",
            schema_version=_SCHEMA_VERSION,
            status="draft",
            payload=report.model_dump(mode="json"),
        )
        EventStore(self._conn).append(
            EventEnvelope(
                entity_type="report",
                entity_id=report.id,
                mutation="created",
                new_state="draft",
                payload={"claims": len(report.claims)},
                producer=self._producer,
                trace_id=self._trace_id,
            )
        )
        return report.id

    def get(self, report_id: str) -> Report:
        return Report.model_validate(
            self._get_payload(report_id, "report")
        )


class LineageQuery:
    """Read-only lineage traversal (MASTER_SPEC.md §12)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def ancestors(self, entity_id: str, *, depth: int = 0) -> list[str]:
        """Walk ``parent_ids`` fields upward. *depth* 0 = unlimited."""
        require(entity_id)
        seen: list[str] = []
        frontier = [entity_id]
        level = 0
        while frontier and (depth == 0 or level < depth):
            level += 1
            next_frontier: list[str] = []
            for current in frontier:
                try:
                    payload = json.loads(
                        self._conn.execute(
                            "SELECT payload FROM entities WHERE entity_id = ?",
                            (current,),
                        ).fetchone()["payload"]
                    )
                except (TypeError, KeyError):
                    continue
                for parent in payload.get("parent_ids", []):
                    if parent not in seen and parent != entity_id:
                        seen.append(parent)
                        next_frontier.append(parent)
            frontier = next_frontier
        return seen
