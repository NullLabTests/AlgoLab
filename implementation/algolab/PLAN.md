# AlgoLab M0 — Implementation Plan

**Milestone:** M0 — Repository and contracts (see `planning/MILESTONES.md`)
**Canonical sources:** `MASTER_SPEC.md`, `spec/foundation/000_PROJECT_CHARTER.md`,
`spec/foundation/001_CORE_ONTOLOGY.md`, `spec/architecture/100_SYSTEM_ARCHITECTURE.md`,
`schemas/*.json`
**Status:** Plan for M0 only. M1+ (execution, orchestration, LLM agents, evolution,
distributed execution, publication, self-improvement) are explicitly out of scope.

## 1. Goal

A tested Python package providing the *contracts layer* of AlgoLab:

- typed ID helpers;
- Pydantic entity models (Hypothesis, Candidate, Experiment, Run, Result,
  Discovery, Report);
- lifecycle state machines (fail closed on invalid transitions);
- append-only SQLite event store (every state mutation appends an audit event);
- budget ledger (compute credits + monetary caps, reservations, idempotency);
- JSON-schema manifest validation against the canonical schemas;
- configuration loading from YAML;
- CLI: `init-db`, `validate-manifest`, `budget-state`;
- tests for **every invariant** in `001_CORE_ONTOLOGY.md`;
- CI workflow and a reproducible local setup command.

## 2. Architecture Decisions

| # | Decision | Rationale |
|---|---|---|
| AD-1 | Package layout mirrors `100_SYSTEM_ARCHITECTURE.md`: `src/algolab/{core,control,storage,validation,cli}` | Later milestones map 1:1 to the same layout |
| AD-2 | SQLite (single file) for M0; schema versioned via `PRAGMA user_version` | Zero-ops, atomic transactions; PostgreSQL comes later |
| AD-3 | Every mutation appends an event to an append-only `events` table, **in the same transaction** as the data change | Audit integrity; replayability; MASTER_SPEC §12 |
| AD-4 | Append-only enforcement at the database level with `BEFORE UPDATE/DELETE` triggers that `RAISE(ABORT)` | API-level discipline is not enough; triggers fail closed |
| AD-5 | Entities stored as immutable JSON payloads (content-addressed provenance); the only mutable column is `status`, and it changes only through an allowed state-machine transition | Ontology invariant 6 (no provenance overwrite) |
| AD-6 | Canonical JSON Schemas are copied byte-for-byte into `src/algolab/schemas/`; a test asserts byte-identity with the canonical files | "Copy ... without changing their meaning" is enforced mechanically |
| AD-7 | Dual validation: `jsonschema` (Draft 2020-12) for interchange manifests; Pydantic v2 for runtime models | Schemas are the canonical contract; Pydantic gives ergonomic runtime types |
| AD-8 | Budget ledger = append-only `ledger_entries` (grant/reserve/charge/release) + a derived `reservations` state table | Money movements immutable; reservation lifecycle is derived state |
| AD-9 | Configuration via strict YAML → Pydantic; unknown keys fail; budget caps are non-negative | Fail closed on misconfiguration |
| AD-10 | CLI on stdlib `argparse`; `pyproject.toml` entry point | Zero extra runtime deps for the operator |

## 3. Dependencies

Runtime (small, per kickoff constraint):

- `pydantic>=2.6` — runtime models and config
- `jsonschema>=4.20` — interchange manifest validation
- `PyYAML>=6.0` — config files
- stdlib: `sqlite3`, `secrets`, `re`, `argparse`, `json`, `datetime`, `hashlib`

Dev:

- `pytest>=8`, `ruff>=0.4`, `mypy>=1.9`

No network calls, no credentials, no background loops in M0.

## 4. Exact Files to Create

```text
implementation/algolab/
├── PLAN.md                          (this file)
├── README.md                        operator quickstart
├── pyproject.toml                   build config, entry point, ruff/mypy/pytest config
├── Makefile                         setup / lint / type / test targets
├── scripts/setup.sh                 reproducible local setup (venv + editable install)
├── .github/workflows/ci.yml         CI: ruff, mypy, pytest on Python 3.11
├── configs/algolab.yaml             default configuration template
├── src/algolab/
│   ├── __init__.py                  version
│   ├── core/
│   │   ├── __init__.py
│   │   ├── ids.py                   typed ID helpers (HYP-/CAND-/EXP-/RUN-/RES-/DISC-/REP-/EVT-)
│   │   ├── events.py                EventEnvelope model + mutation naming
│   │   ├── models.py                entity models (Hypothesis…Report)
│   │   └── state.py                 StateMachine + transition tables + InvalidStateTransition
│   ├── control/
│   │   ├── __init__.py
│   │   ├── config.py                AlgolabConfig (YAML → Pydantic, strict)
│   │   └── budget.py                BudgetLedger (grant/reserve/charge/release)
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── db.py                    SQLite connection factory, schema DDL, append-only triggers
│   │   ├── event_store.py           append-only event store (read + write)
│   │   └── repositories.py          entity repositories enforcing ontology invariants
│   ├── schemas/
│   │   ├── __init__.py              schema registry loader
│   │   ├── hypothesis.schema.json   (copied verbatim from canonical schemas/)
│   │   ├── candidate.schema.json    (copied verbatim)
│   │   └── experiment.schema.json   (copied verbatim)
│   ├── validation/
│   │   ├── __init__.py
│   │   └── schema_validator.py      validate_manifest() against canonical schemas
│   └── cli/
│       ├── __init__.py
│       └── main.py                  init-db | validate-manifest | budget-state
├── tests/
│   ├── conftest.py                  in-memory DB fixtures, canonical schema paths
│   ├── test_ids.py
│   ├── test_models.py
│   ├── test_state_machine.py
│   ├── test_schemas_match_canonical.py
│   ├── test_schema_validation.py
│   ├── test_config.py
│   ├── test_event_store.py
│   ├── test_budget_ledger.py
│   ├── test_repositories.py
│   └── test_invariants.py           one test per ontology invariant (001_CORE_ONTOLOGY.md)
└── docs/decisions/
    ├── ADR-0001-m0-foundation.md
    ├── ADR-0002-append-only-enforcement.md
    ├── ADR-0003-validation-strategy.md
    └── ADR-0004-budget-ledger.md
```

## 5. Acceptance-Test Mapping (M0)

| MILESTONES.md M0 item | Where it is satisfied |
|---|---|
| package layout | `src/algolab/` tree; verified by import smoke test |
| schemas validate examples | `test_schema_validation.py` (valid + invalid fixtures); canonical byte-identity test |
| state machine tests | `test_state_machine.py` (allowed transitions, fail-closed, no persistence on invalid transition) |
| append-only event store | `test_event_store.py` + trigger-level UPDATE/DELETE rejection tests |
| budget ledger | `test_budget_ledger.py` (grant/reserve/charge/release, caps, idempotency, append-only) |
| CI passes | `.github/workflows/ci.yml` runs ruff, mypy, pytest |

Additional kickoff obligations: ontology invariants → `test_invariants.py`;
CLI → `test_cli.py` (folded into `test_repositories.py`/`test_event_store.py` or
its own file — final: `tests/test_cli.py` via `subprocess` on the entry point
`python -m algolab.cli`); config → `test_config.py`.

## 6. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Schema drift between copied and canonical schemas | Medium | Byte-identity test + CI |
| Append-only discipline violated in future milestones | Medium | DB triggers fail closed; events written in the same transaction |
| Pydantic v2 validation semantics differ from JSON Schema | Medium | Manifests validated by JSON Schema at the boundary (canonical); Pydantic is runtime-only |
| Test DB shared state across tests | High | Per-test in-memory SQLite fixtures |
| Budget arithmetic drift (float) | Low | Credits stored as `REAL` with explicit checks; comparison helper with epsilon; monetary override checked per reservation |
| Invalid transitions partially applied | High | Transition applies status + event in one transaction; state machine checked *before* any write |

## 7. Out of Scope for M0 (recorded)

Orchestrator, scheduler, run execution, FastAPI, benchmarking, statistics,
LLM agents, evolution, distributed execution, publication, self-improvement,
PostgreSQL, artifact store, governance API endpoints. These begin in M1+.

## 8. Exit Criteria

1. All M0 acceptance items in §5 pass on a clean checkout (`scripts/setup.sh`
   then `make lint type test`).
2. `M0_COMPLETION_REPORT.md` written with test output, remaining risks, and
   operator commands.
