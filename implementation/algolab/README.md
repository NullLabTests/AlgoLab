# AlgoLab — M0 contracts layer

M0 of the AlgoLab v1 build (`../../../planning/MILESTONES.md`): a tested Python
package for IDs, entity models, lifecycle state machines, an append-only
audit/event store, the budget ledger, canonical JSON-schema manifest
validation, configuration loading, and the `algolab` CLI.

This milestone has **no** LLM agents, no execution, no evolutionary search, no
publication, and no distributed execution (all deferred to M1+).

## Quickstart

```bash
bash scripts/setup.sh          # venv + editable install
make lint                      # ruff
make type                      # mypy (strict)
make test                      # pytest
```

## CLI

```bash
algolab init-db [--config configs/algolab.yaml] [--path DB_PATH]
algolab validate-manifest --type hypothesis|candidate|experiment --file PATH
algolab budget-state [--config configs/algolab.yaml] [--path DB_PATH]
```

## Layout

```text
src/algolab/
  core/          ids, events, models, state
  control/       config, budget ledger
  storage/       sqlite schema + append-only triggers, event store, repositories
  schemas/       canonical JSON Schemas (byte-identical copies)
  validation/    manifest validation against canonical schemas
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