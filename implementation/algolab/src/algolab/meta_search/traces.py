"""Append-only, content-addressed discovery traces (Phase 3).

A :class:`DiscoveryTrace` is the durable record of *how* AlgoLab searched:
each node records one decision together with its policy version, evaluation,
compute spend and provenance.  Records are immutable and content-addressed:
mutating an existing node breaks the checksum chain and is detected by
:meth:`DiscoveryTrace.verify_integrity`.  Serialization is canonical (sorted
keys, compact separators) so identical logical traces hash identically.

Observations, derived metrics and hypotheses are kept in separate fields so a
replay consumer can never mistake an interpretation for a measurement.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

TRACE_SCHEMA_VERSION = "meta-trace/1.0"

# Kinds of statement a node may carry.  Keeping these separate is a hard
# requirement: derived metrics and hypotheses must not be read as observations.
OBSERVATION = "observation"
DERIVED_METRIC = "derived_metric"
HYPOTHESIS = "hypothesis"


class TraceIntegrityError(RuntimeError):
    """Raised when a trace fails checksum, ordering or identity validation."""


def canonical_bytes(payload: Any) -> bytes:
    """Deterministic UTF-8 JSON encoding (sorted keys, no incidental spaces)."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True)
class TraceNode:
    """One immutable discovery decision record.

    ``node_id`` is derived from the canonical content of the record (excluding
    the id/checksum themselves), giving stable identifiers without a mutable
    counter.  ``previous_checksum`` links nodes into an append-only chain.
    """

    experiment_id: str
    parent_id: str | None
    policy_id: str
    policy_version: str
    candidate_id: str
    candidate_generation_method: str
    search_parameters: dict[str, Any] = field(default_factory=dict)
    selection_decision: str = ""
    refinement_decision: str = ""
    evaluation_result: dict[str, Any] = field(default_factory=dict)
    rejection_reasons: tuple[str, ...] = ()
    compute_credits: float = 0.0
    stopping_decision: str = ""
    artifact_refs: tuple[str, ...] = ()
    seed: int = 0
    dataset_id: str = ""
    eval_split_id: str = ""
    observation: dict[str, Any] = field(default_factory=dict)
    derived_metrics: dict[str, Any] = field(default_factory=dict)
    hypotheses: tuple[str, ...] = ()
    execution_provenance: dict[str, Any] = field(default_factory=dict)
    created_at_utc: str = ""
    schema_version: str = TRACE_SCHEMA_VERSION
    previous_checksum: str = ""
    statement_kind: str = OBSERVATION
    node_id: str = ""
    checksum: str = ""

    def content(self) -> dict[str, Any]:
        """Canonical content used for identity and checksum computation."""
        payload = asdict(self)
        payload.pop("node_id", None)
        payload.pop("checksum", None)
        return payload

    def seal(self, previous_checksum: str) -> TraceNode:
        """Return a node with stable id and checksum set (pure function)."""
        base = replace(
            self, previous_checksum=previous_checksum, node_id="", checksum=""
        )
        digest = _sha256(base.content())
        return replace(base, node_id=f"trn_{digest[:20]}", checksum=digest)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> TraceNode:
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(raw) - known
        if unknown:
            raise TraceIntegrityError(f"unknown trace-node fields: {sorted(unknown)}")
        if raw.get("schema_version") != TRACE_SCHEMA_VERSION:
            raise TraceIntegrityError(
                f"unsupported trace schema: {raw.get('schema_version')!r}"
            )
        node = cls(**raw)
        digest = _sha256(node.content())
        if node.node_id != f"trn_{digest[:20]}" or node.checksum != digest:
            raise TraceIntegrityError(f"node checksum mismatch: {node.node_id}")
        return node


@dataclass
class DiscoveryTrace:
    """An append-only sequence of :class:`TraceNode` records."""

    trace_id: str
    experiment_id: str
    nodes: list[TraceNode] = field(default_factory=list)
    schema_version: str = TRACE_SCHEMA_VERSION

    @property
    def head_checksum(self) -> str:
        return self.nodes[-1].checksum if self.nodes else "0" * 64

    def append(self, node: TraceNode) -> TraceNode:
        """Append and seal a node; the parent must already be in the trace."""
        if node.parent_id is not None and node.parent_id not in self._ids():
            raise TraceIntegrityError(f"unknown parent: {node.parent_id}")
        if node.experiment_id != self.experiment_id:
            raise TraceIntegrityError("node belongs to a different experiment")
        sealed = node.seal(self.head_checksum)
        if sealed.node_id in self._ids():
            raise TraceIntegrityError(f"duplicate node id: {sealed.node_id}")
        self.nodes.append(sealed)
        return sealed

    def children(self, node_id: str | None) -> list[TraceNode]:
        """Direct children of ``node_id`` in append order (roots if None)."""
        return [n for n in self.nodes if n.parent_id == node_id]

    def _ids(self) -> set[str]:
        return {n.node_id for n in self.nodes}

    def verify_integrity(self) -> bool:
        """Verify the checksum chain, identities, parents and schema versions."""
        previous = "0" * 64
        seen: set[str] = set()
        for node in self.nodes:
            if node.schema_version != TRACE_SCHEMA_VERSION:
                return False
            if node.previous_checksum != previous:
                return False
            digest = _sha256(node.content())
            if node.checksum != digest or node.node_id != f"trn_{digest[:20]}":
                return False
            if node.node_id in seen:
                return False
            if node.parent_id is not None and node.parent_id not in seen:
                return False
            seen.add(node.node_id)
            previous = node.checksum
        return True

    def to_canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trace_id": self.trace_id,
            "experiment_id": self.experiment_id,
            "nodes": [n.to_dict() for n in self.nodes],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> DiscoveryTrace:
        if raw.get("schema_version") != TRACE_SCHEMA_VERSION:
            raise TraceIntegrityError(
                f"unsupported trace schema: {raw.get('schema_version')!r}"
            )
        trace = cls(
            trace_id=str(raw["trace_id"]),
            experiment_id=str(raw["experiment_id"]),
            nodes=[TraceNode.from_dict(n) for n in raw.get("nodes", [])],
        )
        if not trace.verify_integrity():
            raise TraceIntegrityError("trace failed integrity verification on load")
        return trace

    def write(self, path: str | Path) -> Path:
        """Atomically-ish write the canonical trace plus a sidecar checksum."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = self.to_canonical_json().encode("utf-8")
        target.write_bytes(payload)
        Path(str(target) + ".sha256").write_text(
            hashlib.sha256(payload).hexdigest() + "\n", encoding="utf-8"
        )
        return target

    @classmethod
    def load(cls, path: str | Path) -> DiscoveryTrace:
        target = Path(path)
        payload = target.read_bytes()
        sidecar = Path(str(target) + ".sha256")
        if sidecar.exists():
            expected = sidecar.read_text(encoding="utf-8").strip()
            if hashlib.sha256(payload).hexdigest() != expected:
                raise TraceIntegrityError("trace file checksum mismatch")
        return cls.from_dict(json.loads(payload.decode("utf-8")))


__all__ = [
    "TRACE_SCHEMA_VERSION",
    "OBSERVATION",
    "DERIVED_METRIC",
    "HYPOTHESIS",
    "TraceIntegrityError",
    "canonical_bytes",
    "TraceNode",
    "DiscoveryTrace",
]
