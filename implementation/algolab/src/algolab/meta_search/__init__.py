"""Meta-Search: bounded, auditable improvement of AlgoLab's *search policies*.

This package implements the DREAM-RSI-inspired capability of learning *how to
search* rather than only which candidates to accept.  It is AlgoLab-native by
design: it reuses the existing toy substrate, statistics module and artifact
conventions instead of creating a parallel framework.

Concepts adapted from DREAM-RSI (google-research/dream-rsi, Apache-2.0):
  * frozen discovery traces + replay environment (its ``TraceEnv`` / ``RawTrace``)
  * prefix-only decisions with recorded outcomes (no leaked future labels)
  * a small, versioned policy contract and deterministic baselines
  * qualification-gated, fail-closed promotion instead of "best on the traces
    that inspired it"

No DREAM-RSI source code is copied.  See
``docs/research/DREAM_RSI_INTEGRATION_AUDIT.md`` and ``THIRD_PARTY_NOTICES.md``.
"""

from algolab.meta_search.policies import (
    BASELINE_POLICY,
    CONTROL_POLICY,
    EVOLVED_POLICY,
    REPLAY_POLICY,
    SearchPolicy,
    Selection,
    Observation,
    propose_policy,
)
from algolab.meta_search.traces import (
    TRACE_SCHEMA_VERSION,
    DiscoveryTrace,
    TraceIntegrityError,
    TraceNode,
)
from algolab.meta_search.replay import (
    OutcomeKind,
    ReplayDecision,
    ReplayEnv,
    ReplayResult,
)
from algolab.meta_search.evaluation import (
    PromotionDecision,
    PromotionStatus,
    evaluate_policy,
    promote,
    replay_evaluation,
)

__all__ = [
    "BASELINE_POLICY",
    "CONTROL_POLICY",
    "EVOLVED_POLICY",
    "REPLAY_POLICY",
    "SearchPolicy",
    "Selection",
    "Observation",
    "propose_policy",
    "TRACE_SCHEMA_VERSION",
    "DiscoveryTrace",
    "TraceIntegrityError",
    "TraceNode",
    "OutcomeKind",
    "ReplayDecision",
    "ReplayEnv",
    "ReplayResult",
    "PromotionDecision",
    "PromotionStatus",
    "evaluate_policy",
    "promote",
    "replay_evaluation",
]
