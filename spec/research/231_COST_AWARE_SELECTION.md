# Cost-Aware Selection Evaluation (Protocol 231)

**Status:** Pre-registered. This document freezes hypotheses, arms,
parameters, comparisons, and decision rules BEFORE execution of experiment
`protocol-230-v2`. It amends nothing in protocol 230; it is a new
experiment whose reference point is the frozen v1 bundle
(`implementation/algolab/experiments/protocol-230-v1/`, checksums verified).
Per 230 §5, amendments after execution are recorded append-only below and
never applied retroactively.

## 1. Motivation (from v1 post-hoc analysis, exploratory)

The v1 beta-family null (C ≈ B: delta +0.00125, adjusted p = 0.786) was
diagnosed as (i) prior saturation — pooled K0 already ranks two of beta's
three useful operators on top — compounded by (ii) exploration starvation of
the third (`refresh`, 0 selections in 214 attempts, prior-suppressed) and
(iii) cost-blindness — C maximizes a success-probability draw while the
beta metric is discoveries per credit; oracle schedules reach +48% to
+178% over B. The c-permuted ablation showed C's beta performance is
carried by its initialization, not its feedback loop.

## 2. Question

Is C's failure on beta an artifact of the *selector's objective*
(cost-blind Thompson), or of adaptation itself?

## 3. Hypotheses (fixed before execution)

- **H1 (primary):** C+ beats B on beta — adjusted p < 0.05, CI excluding 0,
  delta > 0.
- **H2 (loop necessity):** C+ beats B+ on beta. A frozen cost-ranked
  reading of K0 must NOT suffice; if it does, the loop adds nothing beyond
  reordering K0.
- **H3 (no harm):** C+ beats A on every family (alpha, beta, held-out
  gamma) and is not worse than C beyond noise (directional check).
- **H4 (mechanism):** C+ selects `refresh` on beta at least once
  (cost normalization resolves the exploration starvation observed in v1),
  and its posterior for `refresh` rises above its K0 initial value by the
  end of trials in which it was tried.

Falsification branches (pre-registered interpretations):

- H1 ∧ H2 pass → beta failure attributed to selector cost-blindness;
  the loop contributes information B+ cannot order statically.
- H1 pass ∧ H2 fail (B+ ≈ C+) → cost-normalized *ranking* of K0 explains
  everything; the loop's marginal value on beta is nil.
- H1 fail → prior saturation dominates; the next lever is family-
  conditioned priors (separate pre-registration), NOT selector tuning.

## 4. Arms

| Arm | Definition | Status |
|---|---|---|
| static | unchanged (round-robin) | carried over |
| knowledge-informed | unchanged (K0 rate-ranked top-3 cycle) | carried over |
| adaptive | unchanged (Thompson over Beta posteriors, argmax θ) | carried over |
| **adaptive-cost-aware (C+)** | identical posteriors/updates; selection argmax(θ_op / credit_cost(op)) | new |
| **knowledge-informed-cost-rank (B+)** | frozen K0 ranked by smoothed success_rate ÷ credit_cost, top-3 cycle, no updates | new |
| random | unchanged | carried over |

Ablations (machinery kept, association destroyed): c-permuted (carried
over), b-shuffled (carried over), **c-plus-permuted** (new: C+ with
permuted feedback).

No existing arm's selection rule, priors, rewards, seeds, budgets, task
definitions, family membership, gate, or thresholds change.

## 5. Fixed experimental parameters

Identical to v1 except where stated:

- Environment toy-discovery 1.1.0; families alpha, beta; held-out gamma;
  ground truth unchanged; discovery gate unchanged (2-seed replication).
- Budget 150 credits/episode; episodes/trial 10; rotation
  `[alpha, beta] × 5`; held-out phase on gamma only.
- Prior: uniform policy, 60 attempts/family, prior_seed 101, seed_base 7,
  analysis_seed 11, top_k 3. K0 construction byte-identical to v1.
- **trials = 128** (v1 used 8). Pre-registered power rationale: v1 paired
  sd(diff) ≈ 0.0077 ⇒ MDE ≈ (1.96 + 0.84) × 0.0077 / √128 ≈ 0.0019
  (~7% of B's beta mean) at α = 0.05 two-sided, 80% power. Chosen before
  any v2 execution; not expandable post hoc without a new registration.
- Arm RNG streams: `analysis_seed + _arm_seed(arm) + trial` (unchanged
  rule; new arms receive their own deterministic offsets).

## 6. Comparisons and correction (fixed)

Primary pairs (BH-corrected within each family block; paired bootstrap CI +
sign-flip permutation p + Cohen's d, as v1):

1. static vs knowledge-informed
2. static vs adaptive
3. knowledge-informed vs adaptive
4. static vs adaptive-cost-aware
5. knowledge-informed vs adaptive-cost-aware
6. adaptive vs adaptive-cost-aware
7. knowledge-informed-cost-rank vs adaptive-cost-aware

Held-out (gamma) block: pairs 1–5 (arms present), BH-corrected.

**Promotion criterion for C+** (mirrors 230 §5 verbatim, candidate
substituted): C+ beats static AND knowledge-informed AND
knowledge-informed-cost-rank is not required — criterion is C+ > A and
C+ > B (adjusted p < 0.05, CI excluding 0) on ≥ 2 independent training
families at the full pre-registered seed plan, and the gap persists on the
held-out family (same direction, CI excluding 0). The original C claim
remains governed by protocol 230 exactly as registered.

## 7. Guarantees

- v1 bundle remains byte-frozen; a golden regression test must reproduce
  v1's statistics/report/raw streams from the post-v2 codebase.
- No result-dependent stopping, seeding, filtering, or threshold changes.
- All raw events, selections (with full posterior traces), statistics,
  manifests, and checksums are persisted under
  `experiments/protocol-230-v2/`.

## 8. Amendment log

- **2026-08-23 (post-execution record; no design change):** experiment
  `protocol-230-v2` executed exactly as registered above (128 trials, all
  arms and ablations, held-out phase). Outcome: H1–H4 all PASS; promotion
  criterion MET for `adaptive-cost-aware`. Primary evidence:
  `implementation/algolab/experiments/protocol-230-v2/` (checksummed
  bundle); interpretation:
  `implementation/algolab/experiments/protocol-230-v2-analysis/REPORT.md`.
  Protocol 230's criterion for plain C remains NOT met and is unchanged.
