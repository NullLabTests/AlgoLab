"""M4 operator catalog (MASTER_SPEC.md §3.3, §10.1).

The operator set AlgoLab may apply to a task. Each operator has:

- a one-line description (the *contract* of what it may do);
- eligibility: the file-path globs it may produce (its "jurisdiction");
- a per-attempt credit budget: applying the operator consumes credits from
  the search budget, so plans and proposals are implicitly price-gated.

Operator identity is the single source of truth for evidence records
(``evidence.operator_name``), plans (``plan.operator_name``), and proposal
targets (``<operator>-<proposal>-<step>-<variant>`` names).
"""

from __future__ import annotations

# name -> (description, eligibility)
OPERATOR_CATALOG: dict[str, tuple[str, list[str]]] = {
    "tune": (
        "modify run configuration (arguments, seeds, hyperparameters) to "
        "improve the primary metric",
        ["*.json", "*.jsonc", "*.toml", "*.yaml", "*.yml"],
    ),
    "reparameterize": (
        "change code-level constants and value parameters inside a file "
        "(not structure)",
        ["*.py"],
    ),
    "decompose": (
        "split a function or module into smaller functions or modules while "
        "preserving behavior",
        ["*.py"],
    ),
    "polyglot": (
        "port or translate a runnable unit into another language without "
        "changing its observable behavior",
        ["*.py", "*.c", "*.cpp", "*.rs", "*.go", "*.js"],
    ),
    "synthesize": (
        "rewrite a runnable unit from an original design (no reference "
        "implementation required)",
        ["*.py"],
    ),
    "validate": (
        "add input validation, assertions, or invariants without changing "
        "normal-path behavior",
        ["*.py"],
    ),
    "refresh": (
        "update a stale file (path exists but content is outdated) to a "
        "recent canonical version",
        ["*.py"],
    ),
    "rollback": (
        "revert a runnable unit to a recent last-known-good version "
        "(recovery, no novelty)",
        ["*.py", "*.json", "*.toml"],
    ),
}

# Roles that map a registered agent (M4) to the operators it may invoke.
M4_OPERATOR_ROLES: dict[str, set[str]] = {
    "tuner": {"tune", "rollback"},
    "coder": {"decompose", "polyglot", "synthesize", "refresh"},
    "critic": {"validate", "rollback"},
    "researcher": {"tune", "reparameterize", "decompose", "polyglot",
                   "synthesize", "validate", "refresh", "rollback"},
}

# Who may invoke each operator (bundles of the above + builders).
OPERATOR_ELIGIBILITY: dict[str, set[str]] = {
    "tune": {"tuner", "researcher"},
    "reparameterize": {"coder", "researcher"},
    "decompose": {"coder", "researcher"},
    "polyglot": {"coder", "researcher"},
    "synthesize": {"coder", "researcher"},
    "validate": {"critic", "researcher"},
    "refresh": {"coder", "researcher"},
    "rollback": {"tuner", "critic", "researcher"},
}

# Per-attempt credit budgets (credits charged per application).
OPERATOR_BUDGETS: dict[str, float] = {
    "tune": 10.0,
    "reparameterize": 10.0,
    "decompose": 20.0,
    "polyglot": 40.0,
    "synthesize": 40.0,
    "validate": 10.0,
    "refresh": 10.0,
    "rollback": 5.0,
}


def is_operator(name: str) -> bool:
    return name in OPERATOR_CATALOG


def operator_description(name: str) -> str | None:
    entry = OPERATOR_CATALOG.get(name)
    return entry[0] if entry else None


def operator_eligibility(name: str) -> list[str]:
    entry = OPERATOR_CATALOG.get(name)
    return list(entry[1]) if entry else []


def required_roles(operator: str) -> set[str]:
    """Roles allowed to invoke *operator* (empty if unknown operator)."""
    return set(OPERATOR_ELIGIBILITY.get(operator, set()))


def budget_for_operator(operator: str) -> float:
    return OPERATOR_BUDGETS.get(operator, 0.0)


__all__ = [
    "OPERATOR_CATALOG",
    "M4_OPERATOR_ROLES",
    "OPERATOR_ELIGIBILITY",
    "OPERATOR_BUDGETS",
    "is_operator",
    "operator_description",
    "operator_eligibility",
    "required_roles",
    "budget_for_operator",
]
