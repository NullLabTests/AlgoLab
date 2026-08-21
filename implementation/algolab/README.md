# AlgoLab — deterministic execution core & knowledge layer

AlgoLab is an autonomous AI algorithm discovery laboratory (see
`../../planning/MILESTONES.md` and `../../MASTER_SPEC.md`). This package is
the executable core of the platform, delivered in three milestones:

- **M0 — Contracts.** IDs, domain models, state machines, an append-only
  audit/event store, the budget ledger, canonical JSON-Schema manifest
  validation, configuration, and the CLI.
- **M1 — Deterministic execution.** Experiment expansion into runs, a
  persistent queue with worker leases, isolated subprocess execution, a
  hash-sealed write-once artifact store, budget reservation on plan and
  charge on completion, crash recovery, and per-experiment aggregation.
- **M4 — Knowledge layer.** Deterministic inferential statistics
  (`algolab.statistics`), immutable scientific evidence records
  (`algolab.knowledge.evidence`), the M4 operator catalog and credit budgets
  (`algolab.knowledge.operators`), and the append-only skill registry that
  gates which agent role may invoke which operator
  (`algolab.knowledge.registry`). The database schema is at **v3**.

The test suite currently has **275 passing tests** covering unit, integration,
ontology-invariant, and protocol-230 compliance behavior. `ruff` and `mypy`
(strict) are clean.

## Quickstart

```bash
bash scripts/setup.sh          # venv + editable install
make lint                      # ruff
make type                      # mypy (strict)
make test                      # pytest (279 tests)
```

## End-to-end run

```bash
# 1. Scaffold a project (config default: docs in configs/algolab.yaml).
algolab init-db --config configs/algolab.yaml

# 2. Create and approve an experiment (manifests in canonical schema).
algolab create-hypothesis  --config configs/algolab.yaml --file h.json
algolab create-candidate   --config configs/algolab.yaml --file c.json
algolab create-experiment  --config configs/algolab.yaml --file e.json
algolab approve-experiment --config configs/algolab.yaml EXP-XXXXXXXX

# 3. Plan runs (all-or-nothing, idempotent per --key) and grant budget.
algolab expand-experiment --config configs/algolab.yaml EXP-XXXXXXXX --key run-1
algolab budget-grant --config configs/algolab.yaml --credits 1000

# 4. Execute (one worker; recovery sweep runs at startup).
algolab worker --config configs/algolab.yaml --poll-interval 0.5

# 5. Inspect outcomes.
algolab list-runs --config configs/algolab.yaml --status SUCCEEDED --json
algolab aggregate-experiment --config configs/algolab.yaml EXP-XXXXXXXX --json
```

## CLI reference

```bash
algolab init-db [--config configs/algolab.yaml] [--path DB_PATH]
algolab validate-manifest --type hypothesis|candidate|experiment --file PATH
algolab create-hypothesis|create-candidate|create-experiment --file PATH
algolab approve-experiment|expand-experiment|recover-runs|aggregate-experiment EXP
algolab budget-state [--config ...] [--path DB_PATH]
algolab budget-grant --config ... [--credits N] [--cost C] [--key KEY]
algolab list-runs [--status S] [--json]
algolab show-run RUN_ID | cancel-run RUN_ID
algolab audit-log [--json]
algolab worker [--poll-interval SECONDS]
algolab search-run EXP_ID [--dir DIR] [--budget N] [--trials N] [--episodes N]
                [--prior-attempts N] [--top-k K] [--force] [--json]
```

### `search-run` (protocol 230)

Runs the pre-registered A/B/C cumulative-search policy comparison against the
deterministic toy environment: Statistic (A) vs Knowledge-informed (B) vs
Adaptive (C), plus a Random reference and two ablations (`c-permuted`,
`b-shuffled`), under identical budgets, task rotation, and seeds. Artifacts
(manifest, knowledge snapshot, per-condition raw events and operator
selections, statistics, report) are written to `--dir`, and every attempt is
persisted to schema-v3 tables (`tasks`, `evidence`, `operator_uses`,
`search_episodes`) with the `operator_stats` aggregate refreshed. The manifest
freezes before any episode runs; an existing artifact directory is refused
unless `--force` is passed.

## Package layout

```text
src/algolab/
  core/          ids, events, models, state
  control/       config, budget ledger
  storage/       sqlite schema v3 + append-only triggers, event store, repositories
  execution/     worker, queue, expansion, aggregation, recovery, artifacts, errors
  workloads/     adapter interface + deterministic quadratic_optimizer workload
  knowledge/     evidence records, M4 operator catalog, skill registry
  search/        protocol-230 toy environment, policies, A/B/C comparison harness
  statistics.py  deterministic inference: bootstrap CI, Welch's t, Cohen's d, FDR
  util.py        shared utilities
  schemas/       canonical JSON Schemas (byte-identical copies)
  cli/           argparse entry point
tests/           unit + integration + ontology-invariant acceptance
docs/decisions/  architecture decision records (ADR-0001..0008)
```

## Design invariants enforced

- Every state mutation appends an audit event in the same transaction.
- Invalid state transitions fail closed (nothing persisted).
- `events` and `ledger_entries` are append-only (DB triggers abort UPDATE/DELETE).
- Entity provenance columns are immutable (DB trigger).
- Runs only exist under approved experiments; results only under existing runs;
  discoveries require replication evidence (≥2 results from ≥2 distinct runs);
  report claims require evidence that resolves to stored results.
- Manifests must validate against the canonical JSON Schemas before persistence.
- Every run is fingerprinted by content and never duplicated across expansion keys.
- Workers run workloads in isolated subprocesses with an allowlisted
  environment; identical experiment + config + seed produce byte-identical
  metrics and logs.
- Artifacts are write-once and hash-sealed; recovery only trusts verified
  artifacts.
- Recovery reconciles orphans (lease expiry → verify/requeue/fail) without
  racing live workers; every recovery action is audited.
- `evidence`, `tasks`, `operator_uses`, and `search_episodes` are append-only:
  scientific records can be created, never silently rewritten.
- Evidence records are direction-consistent and carry novelty/replication
  status; promotion claims require the statistical analysis stored with them.
- Operators are invoked only by registered agent roles (`knowledge.registry`),
  and each invocation draws from a per-operator credit budget.
- The causal knowledge loop (research-loop step 10) is supported by
  evidence from the pre-registered A/B/C protocol
  (`../../spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md`): the adaptive
  policy (C) outperforms both static (A) and knowledge-informed (B) with
  adjusted p < 0.05 and the advantage transfers to the held-out family.
  This evidence is specific to the toy environment; generalisation to real
  workloads remains unproven.

## Documentation

- `../../MASTER_SPEC.md` — canonical specification (§8 evidence, §11 statistics)
- `../../spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md` — the A/B/C protocol gating the knowledge-loop claim
- `M1_PLAN.md` / `M1_COMPLETION_REPORT.md` — execution-core plan and verification
- `docs/M1_EXECUTION_MODEL.md` — pipeline: approve → expand → claim → run → seal → recover
- `docs/WORKLOAD_ADAPTERS.md` — adapter interface + `quadratic_optimizer` workload
- `docs/RECOVERY.md` — orphan/reservation reconciliation protocol
- `docs/ARTIFACT_FORMAT.md` — per-run artifact layout and hashing
- `docs/ERROR_CODES.md` — the stable `ErrorCode` taxonomy
- `docs/decisions/` — ADR-0001..0008 for contracts, execution, queue, artifacts, recovery
