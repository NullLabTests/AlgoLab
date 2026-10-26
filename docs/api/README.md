# AlgoLab API Documentation

## Core Modules

### `algolab.core`
Core domain models, IDs, events, and state machines.

### `algolab.search`
Research search harness for policy comparison across substrates.
- `ExperimentConfig` - Configuration for search experiments
- `PolicyComparison` - Main harness for running policy comparisons
- Workloads: `toy`, `hpo` (KNN), `s2`, `transform`

### `algolab.knowledge`
Knowledge layer with evidence tracking and operator management.
- `evidence` - Immutable scientific evidence records
- `operators` - Operator catalog and credit budgets
- `registry` - Append-only skill registry

### `algolab.statistics`
Deterministic statistical inference utilities.
- Bootstrap confidence intervals
- Welch's t-test
- Cohen's d effect size
- Benjamini-Hochberg FDR correction

### `algolab.storage`
Persistent storage layer.
- SQLite schema (v3) with append-only triggers
- Event store
- Repositories

### `algolab.execution`
Execution engine for experiments and runs.
- Worker with isolated subprocess execution
- Queue with leases
- Artifact store (write-once, hash-sealed)
- Recovery and aggregation

## CLI Reference

See [implementation/algolab/README.md](../../implementation/algolab/README.md#cli-reference) for full CLI documentation.

## Usage Examples

- [Quickstart with toy substrate](../../examples/quickstart_toy.py)
- [Running protocol comparisons](../../implementation/algolab/README.md#search-run-protocols-230234)
