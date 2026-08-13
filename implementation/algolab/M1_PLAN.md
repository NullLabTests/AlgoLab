# AlgoLab M1 — Implementation Plan

**Milestone:** M1 — Deterministic execution core (see `planning/MILESTONES.md`)
**Canonical sources:** `MASTER_SPEC.md`, `spec/foundation/001_CORE_ONTOLOGY.md`,
`spec/architecture/100_SYSTEM_ARCHITECTURE.md`, M1 kickoff prompt
**Status:** Plan for M1 only. LLM agents, literature retrieval, evolutionary
search, distributed execution, self-improvement, publication, external APIs,
Ray/K8s/Celery/Redis remain out of scope (M2+).

## 1. Architecture Changes

M0 delivered the contracts layer: entities, state machines, append-only event
store, budget ledger, manifest validation, CLI. M1 adds the **execution
plane** on top of the same SQLite database:

- **Runs leave the `entities` table.** A new structured `runs` table carries
  the run lifecycle plus queue mechanics (worker id, leases, heartbeats,
  attempts, priority, next-eligible time, cancellation flag, reservation id,
  artifact dir). Entity-based lineage stays for hypothesis/candidate/
  experiment/result/discovery/report.
- **Persistent run queue.** Runs are *created* in `CREATED`, immediately
  `QUEUED`, and claimed by worker processes through atomic single-statement
  claims inside `BEGIN IMMEDIATE` transactions. No double claim is possible.
- **Worker processes.** `algolab worker` (CLI subcommand) claims a run and
  executes it as an isolated subprocess: argv list, `shell=False`, no
  environment inheritance beyond an explicit allowlist, `cwd` = run artifact
  directory, explicit timeout, stdout/stderr captured with byte limits,
  cancellation via SIGTERM/SIGKILL.
- **Workload adapter contract.** A typed interface (`command() -> list[str]`,
  explicit timeout, config derivation from candidate manifests, metrics
  validation, artifact validation). One built-in adapter:
  `quadratic_optimizer` — a standalone, dependency-free Python script that is
  fast, CPU-only, deterministic per seed, pass/fail capable (converged flag
  + exit behavior), multi-metric, and supports test hooks for timeout and
  cancellation.
- **Deterministic expansion.** `expand-experiment` materializes one run per
  (candidate × seed) plus one per (baseline × seed). Each run carries a
  content fingerprint (`config_fingerprint`, UNIQUE) — re-expansion is
  idempotent and cannot create duplicates. Identical config + seed implies
  identical scientific metrics (no wall-clock dependence).
- **Budget integration.** Expansion reserves estimated credits per run
  (all-or-nothing; insufficient budget blocks the whole expansion). The
  worker charges *actual* compute units on completion and releases unused
  reservations; overruns are recorded as ledger + audit events, never silent.
- **Recovery.** `recover-runs` finds workers that died (lease expiry),
  finalizes runs whose artifacts are complete and hash-verified, requeues
  retryable orphans with backoff, and fails the rest — never double-charging.
- **Aggregation.** `aggregate-experiment` computes per-seed tables, per-metric
  statistics, and baseline-vs-candidate effects from run metrics; output is
  machine-readable JSON. It cannot declare a discovery (refused explicitly).
- **Observability.** JSON-line structured logging for the worker, an error
  taxonomy (`execution/errors.py`) mapped 1:1 to `docs/ERROR_CODES.md`, and a
  full audit trail via the existing append-only `events` table (including
  **rejected transitions** as audit events).

## 2. Exact Files to Create/Modify

```text
implementation/algolab/
├── M1_PLAN.md                         (this file — new)
├── M1_COMPLETION_REPORT.md            (new, final step)
├── README.md                          (modify: M1 quickstart + reference lifecycle)
├── pyproject.toml                     (modify: version 0.2.0; description)
├── configs/algolab.yaml               (modify: execution/recovery/storage.artifacts_dir)
├── src/algolab/
│   ├── core/
│   │   ├── models.py                  (modify: Run = M1 statuses + workload/is_baseline/candidate_id)
│   │   └── state.py                   (modify: RUN_TRANSITIONS -> M1 lifecycle; keep fail-closed)
│   ├── control/
│   │   ├── budget.py                  (modify: partial charge, overrun events)
│   │   └── config.py                  (modify: ExecutionConfig, RecoveryConfig, artifacts_dir)
│   ├── storage/
│   │   ├── db.py                      (modify: SCHEMA_VERSION=2, migrations, runs DDL)
│   │   ├── repositories.py            (modify: drop entity-based RunRepository; ResultRepository
│   │   │                               run-existence now checks the runs table)
│   │   └── run_repository.py          (new: runs table persistence + queue primitives)
│   ├── execution/
│   │   ├── __init__.py                (new)
│   │   ├── errors.py                  (new: ErrorCode enum, error taxonomy)
│   │   ├── artifacts.py               (new: RunArtifacts — layout, hashing, manifests)
│   │   ├── queue.py                   (new: claim/heartbeat/cancel/eligibility)
│   │   ├── expansion.py               (new: ExperimentExpansion)
│   │   ├── worker.py                  (new: Worker execution loop)
│   │   ├── recovery.py                (new: recover_runs)
│   │   ├── aggregation.py             (new: aggregate_experiment)
│   │   └── logging.py                 (new: JSON-line structured logger)
│   ├── workloads/
│   │   ├── __init__.py                (new: registry: register/get/list)
│   │   ├── base.py                    (new: WorkloadAdapter Protocol + workload errors)
│   │   └── quadratic_optimizer.py     (new: adapter + standalone __main__ script)
│   └── cli/
│       └── main.py                    (modify: 12 new commands; --json output)
├── docs/
│   ├── M1_EXECUTION_MODEL.md          (new)
│   ├── WORKLOAD_ADAPTERS.md           (new)
│   ├── RECOVERY.md                    (new)
│   ├── ARTIFACT_FORMAT.md             (new)
│   ├── ERROR_CODES.md                 (new)
│   └── decisions/
│       ├── ADR-0005-m1-execution-model.md     (new)
│       ├── ADR-0006-persistent-queue-leases.md (new)
│       ├── ADR-0007-artifact-store.md         (new)
│       └── ADR-0008-recovery-protocol.md      (new)
└── tests/
    ├── test_run_machine.py            (new)
    ├── test_queue.py                  (new)
    ├── test_expansion.py              (new)
    ├── test_budget_partial_charge.py  (new)
    ├── test_workloads.py              (new)
    ├── test_artifacts.py              (new)
    ├── test_worker.py                 (new; subprocess integration)
    ├── test_recovery.py               (new)
    ├── test_aggregation.py            (new)
    ├── test_cli_execution.py          (new)
    ├── test_migration_v1_to_v2.py     (new)
    ├── test_lifecycle.py              (new: full lifecycle end-to-end)
    ├── test_determinism.py            (new: second identical run -> identical metrics)
    ├── test_state_machine.py          (modify: M1 run lifecycle)
    ├── test_repositories.py           (modify: run flows via expansion)
    └── test_invariants.py             (modify: run references via expansion; invariant 4 intact)
```

No new runtime dependencies (stdlib + pydantic/jsonschema/PyYAML only).

## 3. Lifecycle Transitions (Run)

Replaces the M0 provisional run machine (`pending/running/completed/failed/
cancelled`). All transitions go through `StateMachine.require_transition`
before any write; a **rejected transition appends an audit event**
(`mutation="transition_rejected"`) and raises `InvalidStateTransition`.

```text
CREATED  -> QUEUED
QUEUED   -> CLAIMED | CANCELLED
CLAIMED  -> STARTING | FAILED | CANCELLED
STARTING -> RUNNING | FAILED | CANCELLED
RUNNING  -> SUCCEEDED | FAILED | CANCELLED | ORPHANED
ORPHANED -> QUEUED | FAILED | SUCCEEDED   (recovery only)
SUCCEEDED / FAILED / CANCELLED are terminal.
```

Semantics:

- `QUEUED -> CANCELLED` is immediate (queued cancellation); cancellations
  requested while `CLAIMED/STARTING/RUNNING` set `cancellation_requested=1`
  and the worker transitions to `CANCELLED` after terminating the subprocess
  (a lease-conflicted cancellation is never applied by a stale worker).
- `RUNNING -> ORPHANED` happens only in recovery when the lease expired
  (worker considered dead).
- `ORPHANED -> QUEUED` re-queues with attempt +1 and backoff;
  `ORPHANED -> FAILED` when attempts are exhausted or artifacts are corrupt;
  `ORPHANED -> SUCCEEDED | FAILED` finalizes a lease-lost run whose artifacts
  hash-verified (recovery-only, budget charged exactly once).
- Experiment lifecycle is unchanged (M0). Expansion moves the experiment
  `approved -> running` only after all runs are durably inserted.

## 4. Database Migrations

`SCHEMA_VERSION` 1 -> 2. `init_schema` becomes a versioned migration runner
(`PRAGMA user_version`), applying `_MIGRATIONS` in order; fresh databases get
v2 directly. Migration v2 adds:

```sql
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES entities(entity_id),
    candidate_id TEXT REFERENCES entities(entity_id),   -- NULL for baselines
    is_baseline INTEGER NOT NULL DEFAULT 0,
    seed INTEGER NOT NULL,
    workload TEXT NOT NULL,
    config TEXT NOT NULL,                -- resolved config (JSON)
    config_fingerprint TEXT NOT NULL UNIQUE,            -- dedupe/idempotency
    status TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    attempt_number INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 1,
    next_eligible_at TEXT NOT NULL,
    worker_id TEXT,
    claim_timestamp TEXT,
    lease_expires_at TEXT,
    heartbeat_at TEXT,
    cancellation_requested INTEGER NOT NULL DEFAULT 0,
    credits_reserved REAL NOT NULL DEFAULT 0,
    cost_reserved REAL NOT NULL DEFAULT 0,
    credits_charged REAL NOT NULL DEFAULT 0,
    cost_charged REAL NOT NULL DEFAULT 0,
    reservation_id TEXT,
    artifact_dir TEXT,
    error_code TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    trace_id TEXT
);
CREATE INDEX idx_runs_queue ON runs (status, next_eligible_at, priority);
CREATE INDEX idx_runs_experiment ON runs (experiment_id, status);

CREATE TABLE expansions (
    expansion_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    run_ids TEXT NOT NULL,               -- JSON array
    producer TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (experiment_id, idempotency_key)
);
```

Notes: M0 never persisted runs outside tests, so no entity-based run rows are
migrated; the legacy `entities.run` path is retired (documented in
`docs/M1_EXECUTION_MODEL.md` and ADR-0005). The append-only triggers,
`entities_provenance_frozen`, and `events`/`ledger_entries` schemas are
unchanged. A v1 -> v2 upgrade test builds the v1 schema first and asserts v2
objects exist after migration.

## 5. Worker-Process Design

`algolab worker [--once] [--poll-interval N]` runs the execution loop in its
own process (its own SQLite connection to the configured DB file):

1. **Claim.** `BEGIN IMMEDIATE`; select the highest-priority eligible run
   (`status='QUEUED'`, `next_eligible_at <= now`,
   `cancellation_requested=0`, ordered by priority desc, next_eligible_at,
   rowid); atomically set `CLAIMED` + `worker_id` + `claim_timestamp` +
   `lease_expires_at`. Zero rows affected -> `CLAIM_CONFLICT` (no double
   claim possible). Audit event appended in the same transaction.
2. **Setup.** Create `artifacts/runs/<RUN_ID>/`; write `manifest.json`
   (run record + experiment/candidate snapshot), `resolved_config.json`
   (workload config), `environment.json` (pinned: python, platform, sqlite
   version, adapter version, allowlisted env vars). Transition `STARTING`.
3. **Launch.** Build argv from the workload adapter; spawn with
   `subprocess.Popen(argv, shell=False, cwd=run_dir, env=<allowlist + ALGOLAB_*>)`.
   Transition `RUNNING`.
4. **Supervise.** A monitor thread enforces: adapter timeout (SIGTERM,
   5 s grace, SIGKILL -> `TIMEOUT`); cancellation flag (-> `CANCELLED`);
   stdout/stderr byte limits (overflow -> kill -> `ARTIFACT_LIMIT_EXCEEDED`);
   a heartbeat loop extends the lease every `heartbeat_interval_seconds`.
5. **Finalize.** Validate `metrics.json` against the adapter schema
   (`METRICS_MISSING`/`METRICS_INVALID`); build `artifact_manifest.json`
   (sha256 per file); enforce total artifact size limit; write
   `completion.json`; charge **actual** compute units via partial ledger
   charge (overrun recorded, never more than reserved), release remainder;
   transition to `SUCCEEDED` or `FAILED` with an `error_code`.
6. **Idempotence.** `--once` exits after one claim; `--poll-interval N`
   loops until no eligible runs remain, then exits 0.

No network access; no secrets in the env allowlist; no shell interpolation
anywhere (argv lists only).

## 6. Artifact Layout

Per run, under `<artifacts_dir>/runs/<RUN_ID>/`:

```text
manifest.json           run + experiment + candidate metadata snapshot
resolved_config.json    workload config actually used (input pin)
environment.json        pinned environment (written before launch)
stdout.log              captured stdout (byte-limited)
stderr.log              captured stderr (byte-limited)
metrics.json            workload-produced metrics (validated against schema)
resource_usage.json     wall-clock s, user/system CPU s, max RSS, exit code
artifact_manifest.json  {schema_version, run_id, artifacts:[{path,size,sha256,
                        media_type,created_at}]} — written last
completion.json         status, error_code, timestamps, credits, cost, hashes
```

- `metrics.json` is written by the workload itself (single writer: the
  subprocess); every other file is written by the worker before/after.
- All manifest files are immutable after completion; `artifact_manifest.json`
  is written once, last.
- `resource_usage.json` uses stdlib `resource` (POSIX) — documented.

## 7. Failure and Recovery Behavior

| Failure | Detection | Handling |
|---|---|---|
| Subprocess nonzero exit | worker | `FAILED` / `SUBPROCESS_FAILURE`, exit code in payload |
| Timeout | worker (timer) | SIGTERM→SIGKILL, `FAILED` / `TIMEOUT` |
| Cancellation requested | worker (flag poll) | terminate subprocess, `CANCELLED` |
| stdout/stderr overflow | worker (limit reader) | kill, `FAILED` / `ARTIFACT_LIMIT_EXCEEDED` |
| Artifact dir too large | worker (post-run scan) | `FAILED` / `ARTIFACT_LIMIT_EXCEEDED` |
| Metrics missing/invalid | worker | `FAILED` / `METRICS_MISSING` or `METRICS_INVALID` |
| Worker death (crash/kill) | `recover-runs`: lease expired | `RUNNING -> ORPHANED` (audited) |
| Orphan with complete, hash-verified artifacts | `recover-runs` | finalize `SUCCEEDED`/`FAILED` per `completion.json`, charge exactly once |
| Orphan, incomplete, attempts remain | `recover-runs` | requeue `ORPHANED -> QUEUED`, attempt +1, backoff |
| Orphan, incomplete, attempts exhausted | `recover-runs` | `FAILED` / `ATTEMPTS_EXHAUSTED` |
| Budget at expansion | expansion service | all-or-nothing; insufficient funds block the entire expansion |
| Actual > reserved | worker | charge reserved only; overrun ledger + audit event |
| Double charge | worker/recovery guard | `credits_charged == 0` and reservation still active required |

Recovery is idempotent and re-runnable; every decision is audit-logged with a
reason payload.

## 8. Test Strategy

- No network, no external LLM calls; all tests hermetic (temp dirs,
  file-based SQLite).
- **Unit:** run machine (all transitions, fail-closed, rejected-transition
  audit event); fingerprints; adapter config derivation/validation; partial
  charge/overrun accounting; environment allowlist filtering.
- **Repository/queue:** claim atomicity (8 threads race one run -> exactly
  one claim), heartbeat/lease expiry, priority ordering, attempts/backoff.
- **Subprocess integration (real processes):** worker success path, timeout
  kill, cancel kill, stream overflow kill, invalid metrics, budget charge
  correctness — using the built-in `quadratic_optimizer` test hooks
  (`sleep_seconds`, `raise_on_start`).
- **Recovery:** crafted rows with expired leases; complete-artifact orphan
  finalizes without double charge; retryable orphan requeues; exhausted
  attempts fail.
- **Migration:** v1 database upgrades to v2.
- **CLI:** every command, exit codes, `--json` output, audit-log contents.
- **Full lifecycle:** CLI-driven end-to-end in a temp dir: create
  hypothesis/candidate/experiment -> approve -> expand -> `worker --once`
  loop -> aggregate -> assert artifacts, audit trail, balanced budget.
- **Determinism:** the same experiment expanded in two clean directories
  yields byte-identical scientific metrics per (config, seed).
- Existing M0 tests updated where the run contract changed (state machine,
  repositories, invariants).

## 9. Security Boundaries

- Subprocess isolation: argv lists only, `shell=False`, `cwd` = run dir; no
  shell interpolation of any manifest/config content.
- Environment allowlist: workers inherit only configured variables
  (defaults: PATH, PYTHONPATH, LANG, LC_ALL, TMPDIR, TZ) plus
  `ALGOLAB_RUN_ID`, `ALGOLAB_EXPERIMENT_ID`, `ALGOLAB_SEED`,
  `ALGOLAB_WORKLOAD`, `ALGOLAB_CONFIG_PATH`, `ALGOLAB_OUT_DIR`. Secrets and
  credentials cannot leak into subprocesses by construction.
- Resource bounds: subprocess timeout, stdout/stderr byte caps, artifact
  size cap, one workload per worker, no network.
- Integrity: append-only `events`/`ledger_entries` triggers; immutable
  entity provenance columns; artifact manifests hashed with sha256 and
  verified by recovery; run configs pinned by fingerprint; budget charging
  guarded against double-apply; fail-closed state machines.
- Audit: every mutation (including rejected transitions) appends an event
  with producer + trace id in the same transaction.

## 10. Acceptance-Criterion -> Test Mapping (M1)

| M1 kickoff criterion | Satisfied by |
|---|---|
| Deterministic local execution, no external deps | `test_workloads.py`, `test_determinism.py`; stdlib-only runtime |
| Persistent, crash-safe SQLite run queue | `test_queue.py`, `test_migration_v1_to_v2.py` |
| Workers claim with leases; no double claim | `test_queue.py` (thread race), `test_worker.py` |
| Subprocess isolation, env allowlist, no shell interpolation, cwd=run dir | `test_worker.py`, `test_workloads.py` (argv only) |
| No arbitrary shell strings | `test_worker.py` (command builder unit tests) |
| Typed workload adapters (argv, timeout, pass/fail, multi-metric) | `test_workloads.py`, `docs/WORKLOAD_ADAPTERS.md` |
| Built-in quadratic_optimizer (fast, CPU-only, deterministic, pass/fail, multi-metric, timeout/cancel testable) | `test_workloads.py`, `test_worker.py` |
| Full lifecycle (13 runs end-to-end) | `test_lifecycle.py` |
| Budget reserve/charge/release, overrun records, no double charge, insufficient budget blocks | `test_budget_partial_charge.py`, `test_expansion.py`, `test_worker.py`, `test_recovery.py` |
| Artifacts: required files, hashes, deterministic metrics, immutable manifests | `test_artifacts.py`, `test_worker.py` |
| Recovery: orphans, finalize/requeue/fail, no double charge | `test_recovery.py` |
| Aggregation: per-seed table, stats, baseline vs candidate, machine-readable, refuse discovery | `test_aggregation.py` |
| CLI: 12 commands, JSON output, exit codes, audit log, no invariant bypass | `test_cli_execution.py`, `test_lifecycle.py` |
| Error taxonomy (16 codes) documented | `execution/errors.py`, `docs/ERROR_CODES.md` |
| Structured observability | `execution/logging.py`, `test_worker.py` |
| Second identical run -> identical metrics | `test_determinism.py` |
| No network / no external LLM calls in tests | CI (pytest) runs hermetic |
| Docs + ADRs + M1_COMPLETION_REPORT | `docs/`, `docs/decisions/`, `M1_COMPLETION_REPORT.md` |
| Stop after M1 | No M2 features implemented; out-of-scope list recorded in this plan |

## 11. Exit Criteria

1. `make lint type test` green on a clean checkout (Python 3.11/3.12 CI).
2. Full lifecycle + determinism tests pass with real subprocesses.
3. `M1_COMPLETION_REPORT.md` documents results, commands, and remaining risks.
