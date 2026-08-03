"""Immutable event envelope for the audit log (MASTER_SPEC.md §12)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from algolab.core.ids import InvalidID, new_id, require

EntityType = Literal[
    "hypothesis",
    "candidate",
    "experiment",
    "run",
    "result",
    "discovery",
    "report",
    "budget",
]

Mutation = Literal[
    "created",
    "status_changed",
    "grant",
    "reserve",
    "charge",
    "release",
]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class EventEnvelope(BaseModel):
    """One immutable audit event. Fields are never mutated after insert."""

    model_config = {"extra": "forbid"}

    event_id: str = Field(default_factory=lambda: new_id("EVT"))
    entity_type: EntityType
    entity_id: str
    mutation: Mutation
    old_state: str | None = None
    new_state: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    producer: str = "unknown"
    trace_id: str | None = None
    created_at: str = Field(default_factory=_utc_now)

    def validate_references(self) -> None:
        """Fail fast on malformed entity/event IDs (fail closed)."""
        require(self.event_id, "EVT")
        try:
            if self.entity_type != "budget":
                require(self.entity_id)
        except InvalidID as exc:
            raise InvalidID(
                f"event {self.event_id} references malformed entity id: {exc}"
            ) from exc
