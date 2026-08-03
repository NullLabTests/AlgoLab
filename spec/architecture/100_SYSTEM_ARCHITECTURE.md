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
  experiments/   planning, execution, benchmarks, statistics
  storage/       repositories, artifacts, provenance
  reporting/     reports and evidence links
  governance/    policy engine, audit, emergency stop
tests/
configs/
experiments/
artifacts/
reports/
ops/
```
