# AlgoLab — M1 deterministic execution core

AlgoLab (`../../../planning/MILESTONES.md`): an autonomous AI algorithm
discovery laboratory. M0 delivered the contracts layer (IDs, models,
append-only audit/event store, budget ledger, canonical JSON-schema manifest
validation, config, CLI). **M1** adds the deterministic execution core:
experiment expansion into runs, a persistent queue with leases, isolated
subprocess execution, a hash-sealed artifact store, budget reservation on
plan and charge on completion, crash recovery, and per-experiment
aggregation.

## Quickstart

```bash
bash scripts/setup.sh          # venv + editable install
make lint                      # ruff
make type                      # mypy (strict)
make test                      # pytest (192 tests)
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
algolab expand-experiment --config configs/algolab.yaml EXP-XXX --key run-1
algolab budget-grant --config configs/algolab.yaml --credits 1000

# 4. Execute (one worker; recovery sweep runs at startup).
algolab worker --config configs/algolab.yaml --poll-interval 0.5

# 5. Inspect outcomes.
algolab list-runs --config configs/algolab.yaml --status SUCCEEDED --json
algolab aggregate-experiment --config configs/algolab.yaml EXP-XXX --json
```

## CLI

```bash
algolab init-db [--config configs/algolab.yaml] [--path DB_PATH]
algolab validate-manifest --type hypothesis|candidate|experiment --file PATH
algolab budget-state [--config ...] [--path DB_PATH]
algolab budget-grant --config ... [--credits N] [--cost C] [--key KEY]
algolab create-hypothesis|create-candidate|create-experiment --file PATH
algolab approve-experiment|expand-experiment|recover|aggregate-experiment EXP
algolab list-runs [--status S] [--json]
algolab worker [--poll-interval SECONDS]
```

## Layout

```text
src/algolab/
  core/          ids, events, models, state
  control/       config, budget ledger
  storage/       sqlite schema + append-only triggers, event store, repositories
  execution/     worker, queue, expansion, aggregation, recovery, artifacts, errors
  workloads/     adapter interface + deterministic quadratic_optimizer workload
  schemas/       canonical JSON Schemas (byte-identical copies)
  cli/           argparse entry point
tests/           unit + integration + ontology-invariant acceptance
docs/decisions/  architecture decision records
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
- Runs only exist under approved experiments; every run is fingerprinted by
  content and never duplicated across expansion keys.
- Workers run workloads in isolated subprocesses with an allowlisted
  environment; identical experiment + config + seed produce byte-identical
  metrics and logs.
- Artifacts are write-once and hash-sealed; recovery only trusts verified
  artifacts.
- Recovery reconciles orphans (lease expiry → verify/requeue/fail) without
  racing live workers; every recovery action is audited.

## Documentation

- `docs/M1_EXECUTION_MODEL.md` — pipeline: approve → expand → claim → run → seal → recover
- `docs/WORKLOAD_ADAPTERS.md` — adapter interface + `quadratic_optimizer` workload
- `docs/RECOVERY.md` — orphan/reservation reconciliation protocol
- `docs/ARTIFACT_FORMAT.md` — per-run artifact layout and hashing
- `docs/ERROR_CODES.md` — the stable `ErrorCode` taxonomy
- `docs/decisions/` — ADR-0005..0008 for execution model, queue/leases, artifact store, recovery