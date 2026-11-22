# ADR-0010 — Meta-Search: native replay traces and fail-closed promotion

- **Status:** Accepted
- **Date:** 2026-11-19
- **Related:** MASTER_SPEC §13, protocol 241, DREAM-RSI integration audit

## Context

The master mission asks for the ability to improve AlgoLab's *search policy*
using recorded research histories. DREAM-RSI implements a related loop using a
filesystem discovery tree, frozen `raw_scores.json` traces, a shared
`TraceEnv`, agent-rewritten policy modules and a replay-fitness promotion step.
AlgoLab already has authoritative persistence (append-only SQLite + event
store), artifact sealing, budgets, statistics and a sealed-bundle harness.
Importing the DREAM-RSI framework would create a second event store, budget
ledger and experiment registry.

## Decision

1. Add an AlgoLab-native `algolab.meta_search` package. Discovery traces are
   content-addressed, append-only and canonically serialized with a sha256
   chain (`traces.py`).
2. Replay is a read-only facade over a frozen trace
   (`replay.py`). Prefix-only decisions are recorded; outcomes for branches
   never explored are marked counterfactual with `uncertain=true` and **no**
   label. Replay output is explicitly not prospective evidence.
3. Policies are frozen, structured, versioned objects with a rollback pointer
   (`policies.py`). No unrestricted self-modifying code and no paid API in the
   core loop; four deterministic presets provide the protocol arms.
4. Promotion is a four-stage, fail-closed gate (`evaluation.py`). Historical
   replay alone cannot promote; prospective improvement and independent
   held-out confirmation are mandatory. Decisions are checksummed and auditable.
5. Protocol 241 is a single bounded CLI run producing one sealed bundle;
   `meta-verify` independently re-checks it. No new dependencies are added and
   no DREAM-RSI source is copied (Apache-2.0 ideas only; see notices).

## Consequences

- Positive: histories are durable, attributable and replayable; policies are
  reviewable; promotion evidence cannot be manufactured by replay or by
  fitting the traces that inspired a proposal.
- Negative / limitations: replay cannot estimate off-tree counterfactuals; the
  first pilot uses a synthetic trace because no meta-search traces existed
  before this ADR; the toy substrate is not a real workload.
- Alternatives rejected: importing DREAM-RSI wholesale (class D), copying its
  MIT/AGPL task suites, or allowing agent-rewritten policy source (violates
  MASTER_SPEC §13).
