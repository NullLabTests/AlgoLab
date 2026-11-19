# STATUS — proven claims, substrates, sample sizes, evidence links

Updated: 2026-11-15 — protocols 239 (transform) and 240 (compose) recorded;
both bundles independently re-executed and reproduced by
`scripts/verify_bundle.py`. Protocol 240 adds a **negative** claim (class C).
The protocol-236 designation was resolved (D-2: 236 = higher-N real workload,
S2 = protocol 237) — see `docs/quality/protocol-236-conflict.md`. Entry format:
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
| 7 | *UNRESOLVED-POWER* — powered higher-n replication of finding 6 (protocol 236: trials 32→96, alpha margin 0.005→0.0035) is pre-registered but not performed; the alpha-margin lever is not yet implemented | — | `spec/research/236_HIGHER_N_REAL_WORKLOAD_PROMOTION.md` | *no bundle* |

## s2 substrate (protocol 237, second-substrate transfer; KNN on a shifted sklearn suite)

| # | Claim | n | Spec | Evidence |
|---|---|---|---|---|
| 8 | No confirmatory claim. The aborted partial bundle (manifest + prior snapshots only; no conditions/report/checksums) is archived as non-evidence at `experiments/_aborted/protocol-236-v1-2026-09-19/`; no `protocol-237-v1` bundle has been sealed | — | `spec/research/237_SECOND_SUBSTRATE_TRANSFER.md` | *none sealed* |

## transform substrate (protocol 239, typed feature-transform selection on real data)

| # | Claim | n | Spec | Evidence |
|---|---|---|---|---|
| 9 | On real transform selection (`StandardScaler -> LogisticRegression` head, 14 typed transforms), adaptive and cost-aware arms do **not** meet the ≥2-family promotion bar (A ≈ B ≈ C); the bundle reproduces bit-for-bit apart from its recorded wall-clock field | 8 trials/family | `spec/research/239_TYPED_TRANSFORM_SUBSTRATE.md` | `experiments/protocol-239-v1/` |

## compose substrate (protocol 240, generative composition search on real pipelines)

| # | Claim | n | Spec | Evidence |
|---|---|---|---|---|
| 10 | A closed 585-program grammar (1–3 typed transforms, no repeats) over three sklearn datasets yields **no** significant policy advantage over uniform random program search on distinct-validated-programs/credit in either training family (H1–H5 all false), and **no** arm's champion transfers positively to the held-out family; outcome class **C**. Scoped to this 585-program space, not to knowledge loops in general | 10 trials/family | `spec/research/240_GENERATIVE_COMPOSITION_SEARCH.md` | `experiments/protocol-240-v1/` |

## meta-search substrate (protocol 241, replay-grounded policy improvement)

| # | Claim | n | Spec | Evidence |
|---|---|---|---|---|
| 11 | Exploratory pilot only: no policy beat the fixed baseline on discoveries/credit (all REJECTED_PROSPECTIVE); the preregistered 10-credit budget was below most operator costs. A post-hoc 40-credit diagnostic also found no improvement (cost-aware Δ = −0.006548, p = 0.14). No promotion; replay never used as prospective evidence | 4 trials/family | `spec/research/241_META_SEARCH_POLICY_IMPROVEMENT.md` | `experiments/protocol-241-v1/`, `experiments/protocol-241-v1-diagnostic/` |

## Official milestones (per `planning/MILESTONES.md`)

M0 Delivered · M1 Delivered · **M2 Reference rediscovery — not delivered
(this sprint: slice or `M2_DEFERRED.md`)** · M3 planned (LLM adapter, default
off) · M4 planned · M5 planned (governance-gated).

## Naming

Milestone IDs (M0–M5) are NOT the knowledge-loop protocols. The 230–237
series is the **KL research line**: 236 = higher-N real-workload promotion
(`spec/research/236_HIGHER_N_REAL_WORKLOAD_PROMOTION.md`), 237 = second-substrate
transfer (`spec/research/237_SECOND_SUBSTRATE_TRANSFER.md`). See
`docs/quality/protocol-236-conflict.md`.