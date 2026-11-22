# System Architecture

## Components

### Control Plane
Owns state transitions, permissions, scheduling, and event dispatch.

### Research Services
Literature, hypothesis, novelty, candidate generation, experiment design,
statistics, reporting.

### Execution Plane
Sandboxed workers that build, test, train, and benchmark candidates.

### Data Plane
Relational metadata store, artifact store, knowledge graph, append-only event log.

### Meta-Search / Policy Evolution plane
A bounded subsystem that treats AlgoLab's own *search strategies* as experimental
objects. It adds no second event store, budget ledger, artifact manager or
experiment registry; it reuses the Data Plane and `algolab.statistics`.

- `meta_search.traces` — `DiscoveryTrace`: content-addressed, append-only
  discovery history with a sha256 chain and canonical JSON. Unwritten branches
  are never assigned an outcome.
- `meta_search.replay` — `ReplayEnv`: prefix-only decisions against a frozen
  trace. Its output is explicitly `is_prospective_evidence=false`; it cannot
  promote a policy.
- `meta_search.policies` — frozen, versioned `SearchPolicy` records with
  deterministic `select()`, content-derived ids, lineage and rollback pointer.
  No agent rewrites policy source code.
- `meta_search.evaluation` — staged evaluation (A historical, B prospective,
  C independent held-out, D fail-closed promotion) using the shared statistics
  layer, with paired bootstrap CIs, Welch p-values, effect sizes and BH-FDR.
- `meta_search.protocol_241` (and successors) — one CLI command writes one
  sealed, checksummed bundle; `meta-verify` independently re-hashes every file
  and re-checks every promotion verdict.
- `meta_search.transfer` — Protocol 244 real-workload runner that swaps only
  the attempt source (frozen `transform`/`hpo` traces) while reusing the same
  evaluator, statistics and fail-closed promotion gate.

Authority boundary: this plane may *propose* and *evaluate* policy versions. It
may not weaken an evaluator, promotion threshold or test, may not promote on
replay-only evidence, and may not alter the historical record. Real-workload
transfer is evaluated by the same evaluator under a new preregistered protocol,
not by changing the toy-stage gate.

## Required APIs

- `POST /hypotheses`
- `POST /candidates`
- `POST /experiments/plan`
- `POST /experiments/{id}/approve`
- `POST /runs`
- `POST /runs/{id}/cancel`
- `GET /entities/{id}`
- `GET /lineage/{id}`
- `GET /budget`
- `POST /governance/stop`

All mutating endpoints require idempotency keys.

## Repository structure

```text
src/algolab/
  core/          IDs, schemas, state machine, events
  control/       orchestrator, scheduler, budget, permissions
  research/      literature, hypotheses, novelty, candidates
  search/        search policies, toy/real workloads, harness
  meta_search/   traces, replay, policies, evaluation, protocol runners
  experiments/   planning, execution, benchmarks, statistics
  statistics.py  bootstrap CI, Welch, Cohen's d, BH-FDR
  storage/       repositories, artifacts, provenance
  execution/     queue, workers, hash-sealed artifacts, recovery
  validation/    schema validation
  workloads/     executable workload adapters
  reporting/     reports and evidence links
  governance/    policy engine, audit, emergency stop
tests/
configs/
experiments/
artifacts/
reports/
ops/
```
