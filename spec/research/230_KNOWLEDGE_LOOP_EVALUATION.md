# Knowledge Loop Evaluation

**Status:** Draft protocol (M4 column: substrate ready; harness = M5).
**Gates:** README research-loop step 10 ("update the knowledge base and
search policy") is a **causal-loop claim under experimental validation**.
It is not to be presented as demonstrated until this protocol's promotion
criterion is met.

## 1. Question

Does a search policy that **learns from historical outcomes** produce more
discoveries per unit of compute than (a) a policy that ignores history, or
(b) a policy that consumes history but does not adapt?

The claim under test is the loop, not the operator catalog:

```
outcome  ->  belief update  ->  next choice  ->  outcome
```

## 2. Arms

All arms execute episodes against the same task distribution with the same
credit budget and the same seed plan. Arms differ only in what they may
read and update.

| Arm | Reads history | Updates beliefs in-episode | Meaning |
|---|---|---|---|
| **A — Static** | never | no | fixed operator schedule; ignores `evidence`/`operator_stats` entirely |
| **B — Knowledge-informed** | pre-run aggregate only | no | proves "receiving knowledge" alone: operator priors fixed from other episodes' evidence; unchanged by own outcomes |
| **C — Adaptive** | pre-run aggregate + own live outcomes | yes | the causal loop: per-operator posterior (e.g. Thompson sampling over effect) updated after every attempt |
| **D — Random** (reference) | never | no | uniform random operator choice; calibration floor for C |

## 3. Experimental design

- **Environment:** toy rediscovery tasks registered in `tasks` with hidden
  ground-truth per-operator effect per family (deterministic, seeded).
- **Budget:** identical `budget_credits` per episode across all arms.
- **Episodes:** `N` episodes per arm; each episode runs `M` seeds. All
  episodes recorded append-only in `search_episodes` (`policy`,
  `operator_use_counts`, `failure_counts`, `attempts`, `discoveries`,
  `credits_charged`, `seed`, `payload`).
- **Discovery definition:** an operator application that (i) passes the
  task's `promotion_threshold` on the primary metric and (ii) meets the
  replication gate (≥2 seeds). Aligns with M1's replication rule.
- **Held-out family:** one task family is withheld from all arm priors;
  B and C never see it before evaluation (tests transfer, not memorization).

## 4. Metrics

- **Primary:** `discoveries / compute` (credits charged). Not best score.
- **Secondary:** promotion rate, credits per discovery, novelty count,
  failure-rate skew, operator concentration (diversity floor check).

## 5. Analysis and pre-registration

- Analysis via `algolab.statistics`: paired bootstrap CIs on arm
  differences (seeded), Cohen's d, BH-adjusted p-values across the full
  arm-comparison matrix. Pairs are matched on (family, seed).
- **Promotion criterion (claim-ready):** C beats both A and B — adjusted
  p < 0.05, CI excluding 0 on the primary metric — on ≥2 independent task
  families at their full seed plan, and the gap persists on the held-out
  family.
- Arms, seeds, budgets, and thresholds are fixed before execution.
  Amendments are recorded as append-only registry/plan entries; no arm
  reads another arm's in-progress episodes.
- The comparison script is deterministic and checked in; re-running the
  fixed seed plan must reproduce the episode table byte-for-byte.

## 6. Progression (autonomy earned, not asserted)

| Level | Evidence | Autonomy granted |
|---|---|---|
| 0 | no loop | none — all choices human-scheduled |
| 1 | protocol passed in toy environment | operator choice within approved catalog, same budget |
| 2 | transfer to held-out family | new families may register under default board |
| 3 | stability at higher budgets | budget expansion under prior approval |

Policy changes that alter discovery criteria or budget rules still require
human approval per `spec/governance/700_GOVERNANCE.md` at every level.

## 7. README claim discipline

Until Level 1 passes, documentation must phrase step 10 as "under
experimental validation" and link here. The README is updated to
demonstrated language only when the pre-registered analysis is attached.

## 8. Implementation mapping

- Substrate: `evidence`, `operator_stats`, `search_episodes`, `tasks`
  (schema v3, `migration 3`), `algolab.statistics`, `knowledge.registry`.
- Harness (M5): `algolab/knowledge/policies.py` (arms A–D),
  `algolab/search/compare.py` (episode runner + pre-registered analysis),
  CLI `algolab search-compare --plan plan.json --seeds S`.
- Environment: deterministic toy workload adapter under `workloads/`.