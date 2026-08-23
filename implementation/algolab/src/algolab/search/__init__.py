"""Cumulative-search policy comparison (protocol 230).

Exposes the deterministic toy environment, the four search policies, and
the A/B/C comparison harness used to test the cumulative-knowledge-loop
hypothesis.
"""

from algolab.search.harness import (
    ExperimentConfig,
    HarnessError,
    PolicyComparison,
    freeze_manifest,
    main,
)
from algolab.search.policies import (
    ADAPTIVE_COST_AWARE_POLICY_VERSION,
    ADAPTIVE_POLICY_VERSION,
    COST_RANKED_KNOWLEDGE_POLICY_VERSION,
    KNOWLEDGE_INFORMED_POLICY_VERSION,
    RANDOM_POLICY_VERSION,
    STATIC_POLICY_VERSION,
    AdaptiveCostAwarePolicy,
    AdaptivePolicy,
    CostRankedKnowledgePolicy,
    KnowledgeInformedPolicy,
    KnowledgeSnapshot,
    PolicyError,
    RandomPolicy,
    SelectionRecord,
    StaticPolicy,
    build_prior_snapshot,
)
from algolab.search.toy import (
    DEFAULT_OPERATORS,
    DISCOVERY_GATE_VERSION,
    HELD_OUT_FAMILY,
    PROMOTION_THRESHOLD,
    TASK_FAMILIES,
    TASK_SUITE_VERSION,
    TOY_ENVIRONMENT_VERSION,
    Attempt,
    ground_truth_effect,
    is_harmful,
    is_useful,
    operator_cost,
    run_attempt,
)

__all__ = [
    "ExperimentConfig",
    "HarnessError",
    "PolicyComparison",
    "freeze_manifest",
    "main",
    "ADAPTIVE_POLICY_VERSION",
    "ADAPTIVE_COST_AWARE_POLICY_VERSION",
    "COST_RANKED_KNOWLEDGE_POLICY_VERSION",
    "KNOWLEDGE_INFORMED_POLICY_VERSION",
    "RANDOM_POLICY_VERSION",
    "STATIC_POLICY_VERSION",
    "AdaptivePolicy",
    "AdaptiveCostAwarePolicy",
    "CostRankedKnowledgePolicy",
    "KnowledgeInformedPolicy",
    "KnowledgeSnapshot",
    "PolicyError",
    "RandomPolicy",
    "SelectionRecord",
    "StaticPolicy",
    "build_prior_snapshot",
    "DISCOVERY_GATE_VERSION",
    "HELD_OUT_FAMILY",
    "TASK_FAMILIES",
    "TASK_SUITE_VERSION",
    "TOY_ENVIRONMENT_VERSION",
    "Attempt",
    "DEFAULT_OPERATORS",
    "PROMOTION_THRESHOLD",
    "ground_truth_effect",
    "is_harmful",
    "is_useful",
    "operator_cost",
    "run_attempt",
]
