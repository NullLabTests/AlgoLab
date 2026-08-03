# M0 Completion Report

- **Milestone:** M0 — Repository and contracts
- **Status:** COMPLETE
- **Date:** 2026-08-03
- **Canonical sources:** `MASTER_SPEC.md`, `spec/foundation/001_CORE_ONTOLOGY.md`,
  `spec/architecture/100_SYSTEM_ARCHITECTURE.md`, `schemas/*.json`,
  `planning/MILESTONES.md`
- **Plan:** `implementation/algolab/PLAN.md`

## 1. Scope delivered

| Deliverable | Location |
|---|---|
| Package layout (`src/algolab/{core,control,storage,validation,cli}`) | `src/algolab/` |
| Typed ID helpers (`HYP-/CAND-/EXP-/RUN-/RES-/DISC-/REP-/EVT-`) | `src/algolab/core/ids.py` |
| Entity models (Hypothesis, Candidate, Experiment, Run, Result, Discovery, Report) | `src/algolab/core/models.py` |
| Lifecycle state machines (experiment, run), fail-closed transitions | `src/algolab/core/state.py` |
| Append-only SQLite event store + DB-level UPDATE/DELETE triggers | `src/algolab/storage/{db,event_store}.py` |
| Budget ledger (grant/reserve/charge/release, idempotency, monetary override) | `src/algolab/control/budget.py` |
| JSON-schema validation against canonical schemas (byte-identical copies) | `src/algolab/{schemas,validation}/` |
| Strict YAML configuration | `src/algolab/control/config.py` |
| CLI: `init-db`, `validate-manifest`, `budget-state` (+ `python -m algolab.cli`) | `src/algolab/cli/` |
| Tests: 98 tests incl. one per ontology invariant | `tests/` |
| CI workflow (ruff, mypy, pytest on 3.11/3.12) | `.github/workflows/ci.yml` |
| Reproducible setup (`scripts/setup.sh`, Makefile) | `scripts/`, `Makefile` |
| Architecture decision records | `docs/decisions/ADR-0001..0004` |

## 2. M0 acceptance criteria — verification

| MILESTONES.md M0 item | Status | Evidence |
|---|---|---|
| package layout | PASS | import smoke test; `algolab --help` works |
| schemas validate examples | PASS | `tests/test_schema_validation.py` (12 tests); canonical byte-identity test |
| state machine tests | PASS | `tests/test_state_machine.py` (6 tests) |
| append-only event store | PASS | `tests/test_event_store.py` (7 tests) incl. trigger-level UPDATE/DELETE rejection |
| budget ledger | PASS | `tests/test_budget_ledger.py` (13 tests) incl. monetary-override and idempotency |
| CI passes | PASS | local equivalents of every CI step pass; workflow file ready |

Ontology invariants (kickoff obligation): each of the 6 invariants from
`001_CORE_ONTOLOGY.md` has a dedicated test in `tests/test_invariants.py`
(+ 2 supporting tests).

## 3. Test output (local run, Python 3.14)

```text
$ make lint
All checks passed!

$ make type
Success: no issues found in 19 source files

$ make test
98 passed in 1.02s
```

CI matrix runs the identical commands on Python 3.11 and 3.12.

## 4. Operator commands (reproducible)

```bash
cd implementation/algolab
bash scripts/setup.sh                    # venv + editable install + dev deps

# Initialize a database
algolab init-db --config configs/algolab.yaml
algolab init-db --path /tmp/demo.sqlite3 # path override needs no config

# Validate manifests against canonical schemas
algolab validate-manifest --type hypothesis  --file hyp.json
algolab validate-manifest --type candidate   --file cand.json
algolab validate-manifest --type experiment  --file exp.json   # exit 1 on invalid

# Budget position
algolab budget-state --config configs/algolab.yaml
```

## 5. Key design decisions recorded

- ADR-0001: M0 foundation architecture (package layout, SQLite, immutable
  payloads, state-machine-gated status).
- ADR-0002: append-only enforced by SQLite triggers (fail closed), events in
  the same transaction as data.
- ADR-0003: JSON Schema at the boundary (byte-identical canonical copies +
  identity test), Pydantic for runtime models.
- ADR-0004: budget ledger model (append-only entries + derived reservations,
  idempotency keys, monetary-override rule).

## 6. Remaining risks (tracked for M1+)

| Risk | Severity | Notes |
|---|---|---|
| Event ordering relies on SQLite `rowid` (insertion order) | Low | Revisit if PostgreSQL migration or partitioned logs arrive |
| `credits_spent` on Run is a plain float; no ledger writeback in M0 | Medium | M1: charge runs against reservations via `BudgetLedger.charge` |
| Experiment manifest `status` can drift from the lifecycle `status` column (payload is immutable by design) | Low | Documented; lifecycle column is authoritative; report `get()` reflects column |
| Baseline IDs are free-form strings (e.g. `small_mlp/gelu`) | Low | Intended for v1 (baselines may be external); revisit in M2 |
| No PostgreSQL / FastAPI / governance API in M0 | Expected | Out of scope by kickoff; M1+ |
| CI workflow unexercised on GitHub (no repo push yet) | Low | Workflow mirrors local commands 1:1 |

## 7. Deviations from plan

None material. Two clarifications recorded:

1. `python -m algolab.cli` requires `cli/__main__.py` (added).
2. `baseline_ids` are identifiers/names, not entity IDs — the Pydantic model
   validates only `hypothesis_ids`/`candidate_ids` as IDs.

## 8. What is NOT in M0 (deliberately)

Orchestrator, experiment execution, benchmarking, statistics, LLM agents,
evolutionary search, distributed execution, publication, self-improvement,
governance API endpoints, artifact store. First next step: M1 — deterministic
execution core (`planning/MILESTONES.md`).
