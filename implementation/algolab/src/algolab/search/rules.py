"""Reusable, dimension-neutral building blocks shared by knowledge-loop
protocols (library extraction — GREAT Phase 1).

The knowledge-loop research line (protocols 230–236) kept repeating the
same three *concepts* across substrates:

- **DecisionRule** — the discovery gate (bounded-margin provenance) plus the
  promotion/commitment decision contract;
- **PriorFactor** — how prior knowledge is drawn down (pooled vs
  family-conditioned vs prior-size) for a substrate's task families;
- **SelectorObjective** — the selection score normalized to per-credit
  success (cost-aware Thompson / cost-rank / proportional allocation).

To make the next substrate (protocol 236 S2) a *transfer* rather than a
fork of the 235 harness, those three concepts are extracted here as small,
pure, substrate-agnostic building blocks. Neither this module nor its
consumers import sklearn or any toy planted-truth machinery; it depends
only on the stdlib.

**Regime of use (pre-registered):** deterministic by construction (no RNG,
no wall-clock inputs, no outcome access at selection time). Versions are
frozen constants; any semantic change bumps the version string and is
recorded in the protocol manifest's `library_versions` block.

Byte-reproducibility contract: this module must not change any randomized
selection or CV outcome that seeds protocol-230-v1 / 235-v1 bundles; it
only *resolves* margins and *shapes* selection scores that the workloads
already own categories for.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

# --- frozen library version (bump on any semantic change) -----------------

DECISION_RULE_LIBRARY_VERSION = "1.0.0"
PRIOR_FACTOR_LIBRARY_VERSION = "1.0.0"
SELECTOR_OBJECTIVE_LIBRARY_VERSION = "1.0.0"


# --- DecisionRule ---------------------------------------------------------

@dataclass(frozen=True)
class DecisionRuleSpec:
    """A registered discovery-gate / promotion rule, dimension-neutral.

    ``margin`` is the minimum absolute CV improvement a candidate must show
    on *both* replicate seeds to count as a validated discovery. Margins may
    be resolved per substrate family (e.g. the alpha lattice recalibration
    of protocol 235b) via :class:`FamilyMarginTable`.
    """

    rule_id: str
    version: str
    description: str
    promotion_bar: str  # human-readable bar text echoed into the manifest


@dataclass(frozen=True)
class FamilyMarginTable:
    """Per-family discovery margins with a documented global default.

    Resolution: ``margins[family]`` if present, else ``default_margin``.
    Exact equality to the lattice-derived constant is preserved to 6dp;
    lookups are deterministic and never consult outcomes.
    """

    default_margin: float
    margins: Mapping[str, float] = field(default_factory=dict)

    def for_family(self, family: str) -> float:
        return self.margins.get(family, self.default_margin)

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_margin": round(self.default_margin, 6),
            "per_family": {k: round(v, 6) for k, v in self.margins.items()},
            "resolution": "family-keyed exact match, else default",
        }


def phrase_discovery_gate(
    margin: float,
    *,
    margin_source: str,
) -> str:
    """Deterministic, prose discipline for the manifest ``discovery_gate``.

    Kept a pure string builder so all bundles share one verbatim format.
    """
    return (
        f"valid implementation AND effect_1 >= {margin:.4f} "
        f"AND effect_2 >= {margin:.4f} "
        f"(2-seed replication gate; margin source: {margin_source})"
    )


# --- PriorFactor ----------------------------------------------------------

@dataclass(frozen=True)
class PriorFactorPlan:
    """How prior knowledge is drawn down for a substrate.

    Mirrors protocol 232/233/234 arm structure without importing them:
    - ``pooled``        — one snapshot shared across all task families;
    - ``family``        — per-family conditioned snapshots (+ pooled fallback);
    - ``prior_size``    — number of pre-loop prior attempts per family that
                          seed the first knowledge snapshot (dose-response).
    """

    factor: str  # "pooled" | "family"
    version: str
    prior_attempts_per_family: int
    rotation: tuple[str, ...]  # episode-scoped family rotation
    held_out_family: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor": self.factor,
            "version": self.version,
            "prior_attempts_per_family": self.prior_attempts_per_family,
            "rotation": list(self.rotation),
            "held_out_family": self.held_out_family,
        }


# --- SelectorObjective -----------------------------------------------------

@dataclass(frozen=True)
class SelectorObjectiveSpec:
    """A deterministic selection objective: score operators from a snapshot.

    ``score`` is a pure function of the snapshot stats + cost table; no RNG,
    no outcome access, no wall clock. Exact score the policies already emit
    is preserved (the workload owns the exact lattice); this spec only
    documents the shared objective family so protocol 236 S2 can pre-register
    "same selector objective, new substrate".
    """

    objective_id: str
    version: str
    description: str
    per_credit: bool  # score is normalized by credit cost


def normalize_success_per_credit(
    success_count: float,
    attempts: float,
    credits: float,
    *,
    flat_cost: float = 10.0,
) -> float:
    """Deterministic per-credit success rate used by cost-aware selection.

    ``attempts`` from a frozen knowledge snapshot; divides by the operator's
    credit cost so selection tracks discoveries-per-credit rather than raw
    accuracy (protocols 231/C+, 235 §4). Pure and reproducible.
    """
    if attempts <= 0.0 or credits <= 0.0:
        return 0.0
    return round((success_count / attempts) / credits, 12)


__all__ = [
    "DECISION_RULE_LIBRARY_VERSION",
    "PRIOR_FACTOR_LIBRARY_VERSION",
    "SELECTOR_OBJECTIVE_LIBRARY_VERSION",
    "DecisionRuleSpec",
    "FamilyMarginTable",
    "PriorFactorPlan",
    "SelectorObjectiveSpec",
    "normalize_success_per_credit",
    "phrase_discovery_gate",
]
