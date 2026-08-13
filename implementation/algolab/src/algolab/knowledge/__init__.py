"""Knowledge package: M4 agent-role commitments, operator catalog,
evidence-led micro-evaluations, and skill-registry enforcement of the
AlgoLab contract.

This package implements the *"knowledge"* layer referenced in
MASTER_SPEC.md (the shared body of Scientific Evidence records, operator
history, agent-role registrations, and skill metadata that governs who may
call which operators and what counts as novelty).
"""

from .evidence import Evidence, EvidenceIntegrityError, EvidenceRepo
from .operators import (
    M4_OPERATOR_ROLES,
    OPERATOR_BUDGETS,
    OPERATOR_CATALOG,
    OPERATOR_ELIGIBILITY,
    budget_for_operator,
    is_operator,
    operator_description,
    required_roles,
)
from .registry import (
    CooperativeRegistry,
    Registry,
    RegistryEntry,
    RegistryError,
    validate_skill_toml,
)

__all__ = [
    "Evidence",
    "EvidenceRepo",
    "EvidenceIntegrityError",
    "OPERATOR_CATALOG",
    "OPERATOR_ELIGIBILITY",
    "OPERATOR_BUDGETS",
    "M4_OPERATOR_ROLES",
    "is_operator",
    "required_roles",
    "operator_description",
    "budget_for_operator",
    "RegistryError",
    "RegistryEntry",
    "Registry",
    "CooperativeRegistry",
    "validate_skill_toml",
]
