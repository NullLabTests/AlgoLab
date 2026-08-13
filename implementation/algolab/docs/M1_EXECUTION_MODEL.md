# M1 Execution Model

- **Milestone:** M1 — Deterministic Execution Core
- **Related ADRs:** ADR-0005, ADR-0006, ADR-0007, ADR-0008

## Overview

M1 turns an approved experiment into a set of concrete, reproducible runs,
executes them in isolated subprocesses, records everything needed to audit and
reproduce them, and recovers safely from crashes and infrastructure failures.
The design goals are:

1. **Determinism** — identical experiment + config + seed must produce
   bit-identical scientific metrics and logs.
2. **Auditability** — every state change and every artifact is recorded and
   hash-verified; nothing is rewritten after the fact.
3. **Crash safety** — a worker crash, a lost lease, or a full node loss can be
   detected and reconciled without violating invariants.

## Pipeline stages

```
experiment (draft)
   │  approve
   ▼
experiment (planned)
   │  expand  ──►  runs (QUEUED, reservation reserved)
   ▼
worker claim   ──►  CLAIMED (+ lease)
   │
   ▼
RUNNING ──► SUCCEEDED | FAILED | CANCELLED
   │              │
   │ (crash)      └─► artifacts sealed: manifest.json, resolved_config.json,
   ▼                  environment.json, stdout.log, stderr.log, metrics.json,
ORPHANED             resource_usage.json, artifact_manifest.json, completion.json
   │  recovery
   ▼
QUEUED (attempt+1) | FAILED (attempts exhausted) | SUCCEEDED (verified artifacts)
```

### 1. Approval

`approve-experiment` moves an experiment `draft -> planned -> approved`. Only
approved experiments can be expanded.

### 2. Expansion (planner)

`expand-experiment EXP-... --key <key>` plans runs for a whole experiment
all-or-nothing:

- One baseline run per seed and one candidate run per (candidate × seed),
  using the candidate's declared config changes merged over the adapter's
  defaults.
- Each planned run is fingerprinted by content: a sha256 of
  `experiment_id + workload + resolved config + seed + is_baseline`
  (canonical JSON, sorted keys). Expansion is idempotent **per key**, and
  a *different* key that maps to identical fingerprints reuses the existing
  runs instead of duplicating them.
- Budget: the total estimated compute units of all new runs must fit the
  experiment's `budget.max_compute_credits`; every run reserves its credits
  in the ledger (`reserve` entry, idempotency key per run). If anything
  fails, nothing is persisted.

### 3. Claiming and leases (ADR-0006)

The run queue is a set in SQLite (no fan-out, no external broker):

- `claim_next(worker_id)` pops the highest-priority eligible run in FIFO
  order, atomically moving it `QUEUED -> CLAIMED` and stamping
  `lease_expires_at = now + lease_seconds`. A run whose `next_eligible_at`
  is in the future is not eligible (recovery backoff).
- Leases are heartbeated by the owning worker
  (`heartbeat_interval_seconds`); heartbeats extend the lease. A worker can
  only claim or heartbeat runs it owns; a different worker receives
  `CLAIM_CONFLICT`.
- **Cancellation** is cooperative: a queued run is cancelled immediately
  (reservation released); a claimed/running run is flagged `CANCEL_REQUESTED`
  and the owning worker aborts it at the next poll
  (outcome `CANCELLED`, reservation released).

### 4. Worker execution

`worker --poll-interval 0.1` runs the loop until no run is eligible:

1. **Claim** — `QUEUED -> CLAIMED` with lease.
2. **Prepare** — the run directory is created under
   `<artifacts_dir>/runs/<RUN_ID>/`; the worker writes `manifest.json` and
   `resolved_config.json` (final, immutable), and pins
   `environment.json` (python executable/version, platform, sqlite version,
   allowlisted environment variables, workload version).
3. **Run** — `STARTING -> RUNNING`, then launches the workload subprocess
   with a clean allowlisted environment (only `env_allowlist` keys pass
   through), cwd = the run directory. The adapter provides the argv,
   workload-level timeout, and metric schema.
4. **Finish** — stdout/stderr are captured to `stdout.log`/`stderr.log`
   with hard byte limits (`max_stdout_bytes`, `max_stderr_bytes`,
   `max_artifact_bytes`). After exit:
   - exit 0 → verify `metrics.json` against the adapter schema and
     `expected_artifacts` → `SUCCEEDED`;
   - non-zero exit → `FAILED` with `SUBPROCESS_FAILURE`;
   - timeout exceeded → process killed → `TIMEOUT`;
   - missing/invalid metrics or artifacts → the corresponding error code.
   The run's reservation is charged exactly the reported compute units
   (`charge` entry); a partial charge releases the remainder.
5. **Seal** — `resource_usage.json`, then `artifact_manifest.json`
   (sha256 of every file), then `completion.json` are written. Files are
   never modified after they are written; recovery re-verifies hashes.

### 5. Recovery (ADR-0008)

The recovery pass runs periodically (CLI `recover` or embedded in worker
startup) and fixes inconsistencies without racing live workers:

- **Orphaned runs** (CLAIMED with an expired lease and no heartbeat) are
  failed to `ORPHANED` with `LEASE_EXPIRED`, then:
  - artifacts verified (`artifact_manifest.json` hashes) → `SUCCEEDED`
    (verified completion), reservation charged;
  - otherwise, if attempts remain → `QUEUED` with
    `next_eligible_at = now + requeue_backoff_seconds` and `attempt_number+1`;
  - attempts exhausted → `FAILED` with `ATTEMPTS_EXHAUSTED`.
- **Abandoned reservations** (active reservation whose run is not in a live
  state) are released.
- **Interrupted states** (`STARTING`, `RUNNING` with live lease) are skipped:
  the owning worker may still be alive.
- Every reconciliation writes an audit event; recovery is idempotent.

### 6. Aggregation

`aggregate-experiment EXP-... --json` reports, per candidate and per baseline:
run counts by status, mean/std of the primary and secondary metrics,
`metric_warnings` when a candidate is missing runs (e.g. all failed), and
the experiment-level budget summary. Baseline statistics are computed across
baseline runs, candidate statistics across that candidate's runs, always
keyed by seed.

## Determinism contract

- The built-in `quadratic_optimizer` workload draws every random number from
  `random.Random(seed)` in a fixed order (see `docs/WORKLOAD_ADAPTERS.md`).
- The resolved config written before execution is byte-identical for
  identical inputs (canonical JSON with sorted keys), so the same
  experiment/seed always yields the same subprocess inputs.
- Verification: two clean projects initialized from the same inputs produce
  identical metric snapshots and byte-identical `stdout.log` files
  (`tests/test_determinism.py`), and repeated CLI runs are identical
  (`tests/test_cli_execution.py`).

## Configuration

All execution tunables live in `configs/algolab.yaml` (see
`src/algolab/control/config.py`): `execution.{max_attempts, lease_seconds,
heartbeat_interval_seconds, default_timeout_seconds, max_stdout_bytes,
max_stderr_bytes, max_artifact_bytes, env_allowlist, priority_default}` and
`recovery.requeue_backoff_seconds`. Relative storage paths in the config are
resolved to absolute paths when the CLI opens a project so that workers and
adapters agree on artifact locations regardless of cwd.
