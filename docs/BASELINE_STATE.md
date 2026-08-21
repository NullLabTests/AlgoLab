# AlgoLab Baseline State

- **Date:** 2026-08-13
- **Audited commit:** `5b302a5` (M1 deterministic execution core)
- **Auditor:** OpenCode (master-mission baseline audit, step 1)
- **Scope:** `master/AlgoLab-v1-Master-Spec/` (canonical spec + `implementation/algolab`)

This document records what actually exists in the repository, what does not,
where documentation and implementation disagree, and the recommended next
implementation sequence. It is the reference point for all subsequent
milestones.

---

## 1. Implemented capabilities

### M0 — Contracts layer (commits `7c63791`, `a484691`, `a31c814`)
- Typed ID helpers (`HYP- CAND- EXP- RUN- RES- DISC- REP- EVT-`).
- Pydantic runtime models for Hypothesis, Candidate, Experiment, Run, Result,
  Discovery, Report (core/models.py).
- Fail-closed lifecycle state machines (Experiment, Run) — invalid transitions
  raise before any write and append a `transition_rejected` audit event.
- Append-only SQLite event store with DB-level UPDATE/DELETE triggers on
  `events` and `ledger_entries`; immutable entity provenance columns.
- Compute-credit budget ledger: grant / reserve / charge / release with
  idempotency keys, partial charges, overrun recording, monetary-over-credit
  override.
- Canonical JSON-Schema manifest validation (schemas copied byte-identical
  into the package; a test asserts byte identity).
- Strict YAML config (unknown keys fail).
- CLI: `init-db`, `validate-manifest`, `budget-state`, `budget-grant`,
  `create-{hypothesis,candidate,experiment}`, `approve-experiment`.

### M1 — Deterministic execution core (commit `5b302a5`)
- Run state machine: `CREATED → QUEUED → CLAIMED → STARTING → RUNNING →
  {SUCCEEDED, FAILED, CANCELLED}` plus recovery-only `ORPHANED`.
- Persistent SQLite run queue with atomic claims (`BEGIN IMMEDIATE`), leases,
  heartbeats, priority/FIFO ordering, backoff, cooperative cancellation.
- Worker process: isolated subprocess execution (`shell=False`, argv lists,
  environment allowlist, `cwd` = run dir), byte-capped stdout/stderr, explicit
  timeouts (SIGTERM→SIGKILL), heartbeat lease renewal.
- Hash-sealed artifact store per run (`artifact_manifest.json`, sha256 per
  file, `completion.json` written last).
- Experiment expansion: deterministic content fingerprints
  (`experiment_id + workload + config + seed + is_baseline`), idempotent
  (experiment, key) re-expansion, all-or-nothing budget reservation, no
  duplicate runs even across keys.
- Crash recovery: lease expiry → ORPHANED → verify artifacts → finalize /
  requeue / fail; no double budget charge.
- Aggregation: per-seed tables, per-metric mean/median/std/min/max,
  baseline-vs-candidate delta and relative delta; explicitly refuses to
  declare discoveries.
- One built-in workload: `quadratic_optimizer` (deterministic, dependency-free,
  multi-metric, pass/fail-capable, test hooks for timeout/cancel).
- Error taxonomy (16 `ErrorCode`s), structured JSON-line logging.
- Schema migration framework (`PRAGMA user_version`, v1 → v2).
- CLI: 16 commands total (adds `expand-experiment`, `worker`, `recover-runs`,
  `aggregate-experiment`, `list-runs`, `show-run`, `cancel-run`,
  `audit-log`).

### Test/quality status (verified 2026-08-13)
- `make test`: **192 passed** (M0 98 + M1 94), hermetic, offline.
- `make lint` (ruff): clean. `make type` (mypy strict): clean (32 files).
- Determinism test: identical config + seed → byte-identical metrics.
- Concurrent claim race test: 8 threads, exactly one claim.

---

## 2. Unimplemented capabilities (gap list)

Everything from M2 onward of `planning/MILESTONES.md`, plus core elements of
the cumulative-discovery research program:

| Capability | Status | Notes |
|---|---|---|
| Statistical inference (CI, effect size, p-value, FDR) | MISSING | Aggregation reports descriptive stats + delta only |
| Discovery gate | MISSING | `declare_discovery` deliberately refuses; no promotion logic |
| Failure taxonomy for research outcomes | MISSING | `ErrorCode` covers execution failures only, not NO_EFFECT etc. |
| Model provider abstraction (LLM) | MISSING | No LLM layer at all; M3 not started |
| Structured evidence archive | MISSING | No tasks/evidence/operator entities; `LineageQuery` walks `parent_ids` only |
| Knowledge/evidence retrieval | MISSING | No query layer over outcomes |
| Search operators | MISSING | No typed operators; candidate generation is manual manifests |
| Adaptive search policy | MISSING | No policy layer; selection is human-driven |
| Cross-task transfer | MISSING | No multi-task machinery |
| Baseline/benchmark suite | MISSING | One synthetic workload; no rediscovery/negative-control tasks |
| Discovery-efficiency metrics | MISSING | No metric family |
| Meta-improvement / generations | MISSING | M5 not started |
| Controlled A/B/C comparison harness | MISSING | No compute-matched comparison runner |
| Trajectory dataset | MISSING | Events are audit log only, not search trajectories |
| Report automation | MISSING | `Report` model exists, no generation |
| End-to-end reproducibility entry point | MISSING | `setup.sh` exists; no single `algolab run ...` reproduction command |
| Schema for `task`/`search_operator`/`episode` | MISSING | Not in ontology |

## 3. Current test inventory

| File | Covers |
|---|---|
| test_ids.py | ID format/prefix invariants |
| test_models.py | Pydantic entity validation |
| test_state_machine.py | experiment/run transitions, fail-closed |
| test_schemas_match_canonical.py | byte identity of copied schemas |
| test_schema_validation.py | manifest validation valid/invalid |
| test_config.py | strict config, caps |
| test_event_store.py | append-only, replay |
| test_budget_ledger.py | grant/reserve/charge/release, caps, idempotency |
| test_repositories.py | ontology invariants, referential integrity |
| test_invariants.py | one test per ontology invariant |
| test_cli.py | CLI surface, exit codes |
| test_expansion.py | idempotent expansion, budget gating |
| test_queue.py | atomic claims, leases, priority |
| test_worker.py | subprocess supervision, limits, env isolation |
| test_recovery.py | orphan reconciliation, no double charge |
| test_aggregation.py | aggregation semantics, refuses discovery |
| test_artifacts.py | layout, hashing, immutability |
| test_budget_partial_charge.py | partial charge / overrun |
| test_determinism.py | byte-identical reruns |
| test_migration_v1_to_v2.py | schema upgrade |
| test_lifecycle.py | full CLI lifecycle |
| test_cli_execution.py | CLI error handling |

## 4. Current CLI

```
algolab init-db | validate-manifest | budget-state | budget-grant |
create-hypothesis | create-candidate | create-experiment | approve-experiment |
expand-experiment | list-runs | show-run | cancel-run | worker | recover-runs |
aggregate-experiment | audit-log
```
Exit codes: 0 success, 1 business failure, 2 usage error.

## 5. Current schemas (canonical, `schemas/`)
- `hypothesis.schema.json`, `candidate.schema.json`, `experiment.schema.json`
  (Draft 2020-12, `additionalProperties: false`).
- No schemas for run/result/discovery/report/task/evidence/operator/episode
  (models are "provisional v1 contract").

## 6. Current persistence model
- Single SQLite file (`data/algolab.sqlite3` default), schema `user_version=2`.
- `events` (append-only, triggers), `entities` (immutable payload + mutable
  status), `ledger_entries` (append-only), `reservations` (derived state),
  `runs` (structured queue rows, unique config fingerprints), `expansions`
  (idempotency records).
- Artifacts on local disk under `artifacts/runs/<RUN_ID>/`, hash-sealed.

## 7. Current experiment model
- Experiment manifest: hypothesis_ids, candidate_ids, baseline_ids (names,
  not IDs), primary/secondary metrics, seeds (≥3), budget, stages,
  stop_conditions, status machine.
- **Weakness:** baselines are *names* resolved by the workload adapter to its
  *default* config. There is no way to specify a custom baseline config — a
  hard blocker for ground-truth benchmark tasks.

## 8. Current budget model
- Credits granted → reserved (per run, at expansion) → charged (actual, on
  completion) with partial-charge release; monetary caps override credit caps.
- One compute credit = one A100-80GB GPU-hour equivalent; normalization via
  `compute_credit_rate` (default 0.001).

## 9. Current provenance model
- Every mutation appends an audit event in the same transaction; rejected
  transitions are audited too. Lineage traversal exists only over
  `parent_ids`. Evidence chains (hypothesis → candidate → experiment → runs →
  results → discovery) exist structurally but nothing *produces* them
  automatically: aggregation → discovery → report is not wired.

## 10. Current extension points
- `WorkloadAdapter` protocol + registry (`workloads/base.py`) — clean place to
  add benchmark workloads.
- `SchemaVersion` migration runner (`db.py`) — clean v3 addition.
- CLI parser is additive.
- Event types are a `Literal` — must be extended for new mutations.

## 11. Architectural weaknesses
1. **No statistical layer** — deltas without uncertainty; cannot support any
   discovery claim.
2. **No discovery path** — `declare_discovery` is a hard refusal; the
   `Discovery`/`Result`/`Report` repositories exist but nothing calls them.
3. **Baseline config cannot be specified** (see §7).
4. **Global UNIQUE on `config_fingerprint`** — re-attempting an identical
   config across experiments raises IntegrityError; needs an explicit
   duplicate path (DUPLICATE classification) instead of a crash.
5. **No archive of scientific outcomes** — every experiment is an isolated
   episode; nothing accumulates across runs.
6. **No multi-task machinery** — `workload` is global config; tasks cannot
   vary workload config per benchmark.
7. **Version drift** — `src/algolab/__init__.py.__version__` is `0.1.0`
   while `pyproject.toml` is `0.2.0`.
8. `_SCHEMA_VERSION = "1.0.0"` is duplicated in repositories.py and conftest
   (drift risk, not currently broken).
9. `test_lifecycle.py` claims "12 runs" while M1 report says 13; minor doc
   inconsistency.
10. Read-side SQL is inline everywhere (no query layer) — acceptable at this
    size; becomes a liability as the archive grows.

## 12. Contradictions between documentation and implementation
- README says `algolab recover` in the CLI listing; the actual subcommand is
  `recover-runs` (README.md line ~53).
- `M1_COMPLETION_REPORT.md` says "12 runs" in the acceptance table for
  `test_lifecycle.py`; the summary table says 13. Cosmetic.
- `__version__` mismatch (see §11.7).
- MASTER_SPEC §9 lists `Priority = P(success) * EstimatedValue *
  InformationGain / ExpectedCost` — not implemented (no planner).
- MASTER_SPEC §4 discovery gates — specified, not implemented (by design,
  M2+).
- `workflows/reference_rediscovery.yaml` describes an MNIST rediscovery
  workflow; no MNIST workload exists and no workflow engine runs it. The file
  is aspirational.
- `prompts/agents/*.md` define research roles; no agent layer exists. All
  aspirational (M3+).

## 13. Recommended next implementation sequence

Following the mission priority (P0–P8) and the vertical-slice principle
(mission §16), without an LLM provider in this environment:

1. **P0 — baseline audit** (this document). ✅
2. **P1 — schema v3 + baseline-config fix + duplicate-path fix.** Adds
   `tasks`, `evidence`, `operator_uses`, `operator_stats`, `search_episodes`
   tables; adds `experiment.baseline_configs` (optional) to the canonical
   schema; turns the global fingerprint collision into an explicit
   DUPLICATE classification.
3. **P2 — statistical layer + discovery gate.** Seeded bootstrap CI, Welch
   t-test, Cohen's d, Benjamini-Hochberg FDR; gate with the mission failure
   taxonomy (INVALID_IMPLEMENTATION, NO_EFFECT, NEGATIVE_EFFECT,
   HIGH_VARIANCE, NON_REPLICABLE, DUPLICATE, INSUFFICIENT_EVIDENCE,
   BENCHMARK_SPECIFIC, COMPUTATIONALLY_UNVIABLE, CONFOUNDED); deterministic
   replication check via fresh subprocess rerun; Discovery/Result entities
   created automatically on promotion.
4. **P3 — evidence archive + retrieval.** Append-only evidence records with
   lineage to hypothesis/candidate/experiment; best-known-config queries per
   task family.
5. **P4 — benchmark suite + metrics.** Rediscovery, composition, negative
   control, and synthetic (exhaustive ground-truth) tasks on the existing
   deterministic workload; discovery-efficiency metric family.
6. **P5 — search operators + adaptive policy.** Deterministic typed operators
   with per-operator statistics; static (uniform) vs adaptive (UCB1) policy.
7. **P6 — controlled comparison + cross-task transfer.** Compute-matched
   static-vs-adaptive experiment across task families and dimensions;
   transfer-rate measurement.
8. **P7 — LLM provider abstraction (model-agnostic).** OpenAI/Anthropic/
   local adapters for candidate *ideation* feeding the same gate+archive
   machinery; System A/B/C comparison.
9. **P8 — meta-improvement.** Versioned proposals, shadow evaluation,
   generation tracking (mission §12–§13).

Milestones M2–M5 in `planning/MILESTONES.md` remain the canonical long-term
roadmap; the sequence above reorders work so that empirical value accrues at
every step without LLM dependence.

## 14. Baseline verification commands

```bash
cd master/AlgoLab-v1-Master-Spec/implementation/algolab
make lint type test   # ruff clean, mypy clean, 192 passed
```
