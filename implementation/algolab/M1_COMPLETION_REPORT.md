# M1 Completion Report

- **Milestone:** M1 — Deterministic Execution Core
- **Status:** COMPLETE
- **Date:** 2026-08-03
- **Canonical sources:** `MASTER_SPEC.md` §2/§9/§14, `planning/MILESTONES.md`
- **Plan:** `implementation/algolab/M1_PLAN.md`

## 1. Scope delivered

| Deliverable | Location |
|---|---|
| Run state machine: `QUEUED -> CLAIMED -> STARTING -> RUNNING -> {SUCCEEDED, FAILED, CANCELLED}`, `ORPHANED` via recovery | `src/algolab/core/state.py` |
| Experiment expansion: per-seed baseline + candidate runs, content fingerprints, idempotent keys, all-or-nothing | `src/algolab/execution/expansion.py` |
| Persistent queue with leases, heartbeats, priority/FIFO, backoff, cooperative cancellation | `src/algolab/execution/queue.py` |
| Worker: claim → prepare artifacts → allowlisted-env subprocess → capture → validate → seal → charge | `src/algolab/execution/worker.py` |
| Recovery: lease expiry → verify/requeue/fail, abandoned reservations, audited reconciliation | `src/algolab/execution/recovery.py` |
| Artifact store: per-run dir, write-once files, sha256 manifest, completion record, size caps | `src/algolab/execution/artifacts.py` |
| Aggregation: per-seed table, baseline vs candidate stats, warnings, JSON output | `src/algolab/execution/aggregation.py` |
| Typed workload adapter + built-in deterministic `quadratic_optimizer` (v1.0.0) | `src/algolab/workloads/` |
| Error taxonomy (16 codes) | `src/algolab/execution/errors.py`, `docs/ERROR_CODES.md` |
| Structured observability (JSON log events) | `src/algolab/execution/logging.py` |
| Schema migration v1→v2 (runs queue mechanics, reservations) with triggers | `src/algolab/storage/db.py` |
| CLI: 16 commands incl. `approve-experiment`, `expand-experiment`, `worker`, `recover-runs`, `budget-grant`, `aggregate-experiment`, `list-runs`, `show-run`, `cancel-run` | `src/algolab/cli/` |
| Tests: 192 tests (M0 98 + M1 94), hermetic, stdlib-only runtime | `tests/` |
| Docs: 5 milestone docs + ADRs ADR-0005..0008 | `docs/`, `docs/decisions/` |
| Config: `execution`/`recovery`/`storage.artifacts_dir` sections | `configs/algolab.yaml` |

## 2. Acceptance criteria — verification

| MILESTONES.md M1 item | Status | Evidence |
|---|---|---|
| Deterministic local execution, no external deps | PASS | `tests/test_workloads.py` (17), `tests/test_determinism.py`; stdlib-only runtime |
| Persistent, crash-safe SQLite run queue | PASS | `tests/test_queue.py`, `tests/test_migration_v1_to_v2.py` |
| Workers claim with leases; no double claim | PASS | `tests/test_queue.py` (concurrent connections), `tests/test_worker.py` |
| Subprocess isolation, env allowlist, no shell, cwd=run dir | PASS | `tests/test_worker.py`, `tests/test_workloads.py` |
| No arbitrary shell strings | PASS | `WorkloadAdapter.command()` returns argv list; unit-tested |
| Typed workload adapters | PASS | `tests/test_workloads.py`, `docs/WORKLOAD_ADAPTERS.md` |
| Built-in quadratic_optimizer | PASS | fast, CPU-only, deterministic, pass/fail + multi-metric, timeout/cancel testable via hooks |
| Full lifecycle end-to-end | PASS | `tests/test_lifecycle.py` (12 runs: 3 candidates × 3 seeds + 3 baselines) |
| Budget reserve/charge/release, no double charge, insufficient budget blocks | PASS | `tests/test_expansion.py`, `tests/test_worker.py`, `tests/test_recovery.py`, `tests/test_budget_partial_charge.py` |
| Artifacts: required files, hashes, immutable manifests | PASS | `tests/test_artifacts.py`, `tests/test_worker.py` |
| Recovery: orphans, verify/requeue/fail, no double charge | PASS | `tests/test_recovery.py` |
| Aggregation: per-seed table, stats, baseline vs candidate, JSON, refuse discovery | PASS | `tests/test_aggregation.py` |
| CLI: commands, JSON output, exit codes, audit log, no invariant bypass | PASS | `tests/test_cli_execution.py`, `tests/test_lifecycle.py` |
| Error taxonomy documented | PASS | `src/algolab/execution/errors.py`, `docs/ERROR_CODES.md` |
| Structured observability | PASS | `tests/test_worker.py` (JSON event assertions) |
| Second identical run → identical metrics | PASS | `tests/test_determinism.py` (bit-identical metrics + stdout) |
| No network / no LLM in tests | PASS | all 192 tests run offline |
| Docs + ADRs + completion report | PASS | this report; `docs/*.md`; `docs/decisions/ADR-0005..0008` |
| Stop after M1 | PASS | no M2 features implemented (see out-of-scope below) |

## 3. Commands

```bash
make lint type test          # all green (ruff, mypy strict, 192 pytest)
make lint                    # ruff — "All checks passed!"
make type                    # mypy — "Success: no issues found in 32 source files"
make test                    # 192 passed

# end-to-end smoke (see README for full flow):
algolab init-db --config configs/algolab.yaml
algolab create-hypothesis --config configs/algolab.yaml --file h.json
algolab create-candidate  --config configs/algolab.yaml --file c.json
algolab create-experiment --config configs/algolab.yaml --file e.json
algolab approve-experiment --config configs/algolab.yaml EXP-XXXXXXXX
algolab budget-grant --config configs/algolab.yaml --credits 5000
algolab expand-experiment --config configs/algolab.yaml EXP-XXXXXXXX --key run-1
algolab worker --config configs/algolab.yaml --poll-interval 0.5
algolab recover-runs --config configs/algolab.yaml
algolab aggregate-experiment --config configs/algolab.yaml EXP-XXXXXXXX --json
```

## 4. Notable design points

- **Expansion is all-or-nothing and content-addressed**: a run is keyed by
  sha256 of `experiment_id + workload + resolved config + seed + is_baseline`; a
  different idempotency key that maps to the same fingerprints reuses existing
  runs (never duplicates).
- **The run set is the queue** (ADR-0006): no broker; `claim_next` is a
  transactional, priority-then-FIFO UPDATE; leases + heartbeats bound claim
  ownership; recovery owns the expired-lease hand-off (ADR-0008).
- **Artifacts are sealed by hash** (ADR-0007): `artifact_manifest.json`
  written last; recovery only ever completes an orphan whose manifest
  verifies.
- **Determinism is enforced**: identical inputs → byte-identical
  `resolved_config.json` and metrics; verified across clean projects and
  repeated CLI invocations.
- **Budget is reserved before scheduling and charged after completion**;
  partial charges release the remainder; the ledger stays append-only and
  idempotent (ADR-0004).

## 5. Remaining risks (post-M1)

- **Single-node assumption**: one worker per node; lease-based claiming scales
  to M2 distributed workers but needs cross-node coordination for
  cancellation/priority.
- **Artifacts on local disk**: hash-sealed but not object-stored; large
  artifacts and node loss of artifact files are M2+ concerns (recovery
  currently fails runs whose artifacts are lost before sealing).
- **`quadratic_optimizer` is a synthetic workload**: it proves the contract;
  real workloads (M2) must honor the adapter contract
  (`docs/WORKLOAD_ADAPTERS.md`).
- **DB-level contention**: single SQLite file is the serialization point; M1
  mitigates with `busy_timeout` + short transactions, but multi-worker M2
  traffic needs WAL/batching tuning.
- **Timeouts are process-kill based**: SIGKILL is abrupt; graceful
  termination/cancellation on request is a refinement candidate.

## 6. Out of scope (M2+, recorded here to prove we stopped)

No LLM agents, no evolutionary search, no distributed workers, no object
storage, no workload orchestration beyond the single-node worker, no
publication/report automation, no web/API surface.
