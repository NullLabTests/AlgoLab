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

### `algolab.meta_search`
Meta-Search / policy-evolution subsystem (protocols 241+). Search strategies are
typed, versioned experimental objects; all stochastic choices are seeded.

- `traces` — `DiscoveryTrace` / `TraceNode`: append-only, content-addressed,
  sha256-chained discovery lineage with canonical JSON.
- `replay` — `ReplayEnv`: prefix-only decisions on a frozen trace; counterfactual
  branches are labelled uncertain with no manufactured outcome and are never
  prospective evidence.
- `policies` — `SearchPolicy` with deterministic `select()`, `SearchPolicy.checksum()`,
  `propose_policy()` and the frozen `BASELINE` / `REPLAY` / `EVOLVED` / `CONTROL` presets.
- `evaluation` — staged `evaluate_policy()` and fail-closed `promote()`; replay
  can only diagnose, prospective and independent held-out stages can promote.
- `protocol_241` — sealed bundle writer `run_pilot()` and independent
  `verify_pilot()` re-hasher/verdict checker.
- `transfer` — Protocol 244 real-workload runner: reuses the same evaluator and
  promotion gate on frozen `transform`/`hpo` attempt traces; replay remains
  diagnostic only.

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

Meta-Search commands:

- `algolab meta-search-run --dir <bundle> ...` — run a preregistered policy
  comparison and seal every artifact in `checksums.json`.
- `algolab meta-transfer-run --dir <bundle> ...` — run the preregistered
  real-workload transfer protocol with the same evaluator/promotion gate.
- `algolab meta-verify --dir <bundle> [--json]` — independently re-hash the
  bundle, check trace integrity and detect replay-only promotion.

## Usage Examples

- [Quickstart with toy substrate](../../examples/quickstart_toy.py)
- [Running protocol comparisons](../../implementation/algolab/README.md#search-run-protocols-230234)
