# STATUS — proven claims, substrates, sample sizes, evidence links

Updated: sprint "Good → Great" (protocols 235b / 236). Entry format:
**claim** — substrate, n, register link, evidence bundle.

## toy substrate (deterministic planted-truth generator)

| # | Proven claim | n | Spec | Evidence |
|---|---|---|---|---|
| 1 | Plain Thompson adaptation (C) beats static/random but misses the ≥2-family promotion bar (ties frozen B on beta) | 16 trials/family | `spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md` | `experiments/protocol-230-v1/` |
| 2 | Cost-aware C+ (success-probability-per-credit) meets the promotion bar and transfers to held-out family | 16 trials/family | `spec/research/231_COST_AWARE_SELECTION.md` | `experiments/protocol-230-v2/` |
| 3 | Family-conditioned priors dominate pooled priors for frozen policies | 60 prior attempts/family | `spec/research/232_FAMILY_CONDITIONED_KNOWLEDGE.md` | `experiments/protocol-232-v1/` |
| 4 | Prior quantity (30→240) does not shrink the frozen-vs-adaptive gap (structural, not informational) | 30/60/120/240 | `spec/research/233_PRIOR_SIZE_DOSE_RESPONSE.md` | `experiments/protocol-233-p{30,60,120,240}/` |
| 5 | Decision-rule format: frozen commitment hits the efficiency ceiling; adaptation value = estimation insurance | 30–240/family | `spec/research/234_DECISION_RULE_FORMAT.md` | `experiments/protocol-233-p{30,60,120,240}/` |

## hpo substrate (KNN micro-HPO, sklearn built-ins)

| # | Claim | n | Spec | Evidence |
|---|---|---|---|---|
| 6 | On real KNN hyperparameter search, static < B < C ≈ C+ ordering reproduces on beta; held-out gamma shows the adaptive loop surviving knob inversion (k21 29%→0% for frozen commitment); **strict ≥2-family promotion bar NOT met at n=32** | 32 | `spec/research/235_REAL_WORKLOAD_BRIDGE.md` | `experiments/protocol-235-v1/` |
| 7 | *UNRESOLVED-POWER* — powered higher-n replication needs CPU time beyond the budget; machinery + margin amendment smoke only | ≤8 | `spec/research/235b_POWERED_REPLICATION.md` (amendment pre-registered) | `experiments/protocol-235-v2/` |

## s2 substrate (protocol 236 — sklearn family shift, tiny/offline)

| # | Claim | n | Spec | Evidence |
|---|---|---|---|---|
| 8 | *(pending — this sprint)* A/B/C promotion verdict for C+ on the S2 substrate | frozen in spec | `spec/research/236_SECOND_SUBSTRATE_TRANSFER.md` | `experiments/protocol-236-v1/` |

## Official milestones (per `planning/MILESTONES.md`)

M0 Delivered · M1 Delivered · **M2 Reference rediscovery — not delivered
(this sprint: slice or `M2_DEFERRED.md`)** · M3 planned (LLM adapter, default
off) · M4 planned · M5 planned (governance-gated).

## Naming

Milestone IDs (M0–M5) are NOT the knowledge-loop protocols. The 230–23x
series is the **KL research line**; this sprint adds 235b and 236.