# Family-Conditioned Knowledge Evaluation (Protocol 232)

**Status:** Pre-registered. Hypotheses, arms, parameters, comparisons, and
decision rules below are frozen BEFORE implementation execution of
experiment `protocol-232-v1`. Reference points: frozen bundles
`experiments/protocol-230-v1/`, `experiments/protocol-230-v2/`. Per 231 §8
discipline, post-execution changes appear only as dated amendment entries.

## 1. Motivation

Protocol 231 established that cost-aware selection (C+) meets the
promotion criterion and that reordering the *pooled* K0 snapshot by cost
(B+) does not help on beta: pooled history ranks `refresh` (useful only in
beta) below three operators neutral in beta, because pooling dilutes
family-specific structure. The prior episodes are, however, already
family-tagged — pooling is a *choice* made at knowledge-construction time.
Whether frozen policies fail because history is uninformative or because
the aggregation discards its structure is open. Protocol 232 tests the one
lever left untouched: **prior construction**.

## 2. Question

Does family-conditioned (non-pooled) historical knowledge close the gap
between frozen-knowledge arms and the adaptive cost-aware arm — i.e., how
much of C+'s advantage is compensation for a lossy knowledge layer?

## 3. Hypotheses (fixed before execution)

- **H1 (conditioning repairs frozen knowledge):**
  `knowledge-informed-family` > `knowledge-informed` on BOTH training
  families (alpha and beta; adjusted p < 0.05, CI excluding 0, delta > 0).
  Basis: family-specific rates de-dilute (a useful-in-one-family operator
  no longer inherits the other family's failures).
- **H2 (frozen ceiling):** `adaptive-cost-aware` >
  `knowledge-informed-family-cost-rank` on both training families
  (adjusted p < 0.05). Even the best composite frozen representation is
  predicted to trail C+ because top-K cycling wastes slots on mis-ranked
  operators and cannot adapt within trials.
- **H3 (initialization source secondary for adaptive selection):**
  `adaptive-cost-aware-family` (posteriors initialized from family-split
  K0 where available) is not significantly worse than `adaptive-cost-aware`
  on any training family, and behaves equivalently on held-out gamma
  (no gamma history exists → falls back to pooled init by construction).
- **H4 (transfer honesty control):** on held-out gamma,
  `knowledge-informed-family` ≈ `knowledge-informed` (CI of delta includes
  0) — conditioning must collapse to pooled behavior when no family
  history exists, confirming no hidden information advantage.

Falsification branches:

- H1 ∧ H2 hold → pooling masked real knowledge value; the adaptive
  advantage persists but its *size* is partly an artifact of lossy
  aggregation; design implication: store per-family aggregates.
- H1 holds ∧ H2 fails (best frozen ≈ C+) → with the right representation,
  adaptation adds ~nothing beyond cold-start; loop value reduces to
  initialization.
- H1 fails → per-family cells too noisy to help (≈7.5 uniform attempts per
  operator per family); next lever would be hierarchical/shrinkage priors.

## 4. Arms

| Arm | Definition | Status |
|---|---|---|
| static, knowledge-informed, adaptive, adaptive-cost-aware, knowledge-informed-cost-rank, random | unchanged | carried over |
| **knowledge-informed-family (B-fam)** | frozen ranking from the family-tagged slice of K0 (plain success-rate ranking, same smoothing), top-3 cycle, never updates | new |
| **knowledge-informed-family-cost-rank (B-fam+)** | as B-fam but ranked by smoothed rate ÷ credit cost | new |
| **adaptive-cost-aware-family (C+fam)** | identical machinery/selection to C+; Beta posteriors initialized from the family-tagged K0 slice when it exists, pooled K0 otherwise | new |

Ablations carried over unchanged (c-permuted, b-shuffled, c-plus-permuted).

Zero-attempt cells in a family slice are zero-filled before ranking;
smoothing yields the neutral 0.5 default (documented deterministic rule).

## 5. Fixed experimental parameters

Identical to protocol 231 except arms:

- budget 150/episode; episodes/trial 10; rotation [alpha, beta]×5;
  held-out gamma phase; discovery gate unchanged.
- Prior generation unchanged: uniform policy, 60 attempts/family,
  prior_seed 101, seed_base 7, analysis_seed 11, top_k 3. The pooled
  snapshot construction remains byte-identical; family slices are derived
  from the SAME prior attempts (no additional environment draws).
- **trials = 128** (as pre-registered in 231; MDE ≈ 0.0019 ≈ 7% relative
  at α = 0.05, 80% power).
- Arm RNG streams: `analysis_seed + _arm_seed(arm) + trial`.

## 6. Comparisons and correction (fixed)

Added to the protocol-231 matrix (BH-corrected within each family block):

1. knowledge-informed vs knowledge-informed-family
2. knowledge-informed-family vs knowledge-informed-family-cost-rank
3. knowledge-informed-family-cost-rank vs adaptive-cost-aware
4. adaptive-cost-aware vs adaptive-cost-aware-family

Held-out block: all pairs among present arms, BH-corrected.

**No new promotion claim is registered.** The criterion evaluated in
`claim_readiness` remains the protocol-231 criterion for
`adaptive-cost-aware`; nothing in this experiment can alter the recorded
230/231 verdicts regardless of outcome.

## 7. Guarantees

- v1/v2 bundles remain byte-frozen; golden regression (v1) must stay green;
  carried-over arm behavior must be untouched (additive-only code change).
- No tuning of any policy against any family; priors, seeds, budgets,
  gate, thresholds fixed as above before execution.

## 8. Amendment log

- **2026-08-25 (post-execution record; no design change):** experiment
  `protocol-232-v1` executed exactly as registered (128 trials, all arms
  and ablations, held-out phase). Outcome: H1–H4 all PASS. Conditioning
  repaired frozen knowledge (B-fam > B: alpha d = 11.4, beta d = 3.9);
  C+ retained a real margin over the best frozen composite (beta d = 5.2);
  C+fam reached ≈99.5% of the cost-aware oracle (pooled eff 0.0730);
  held-out fallback verified (B-fam == B on gamma to printed precision).
  Evidence: `implementation/algolab/experiments/protocol-232-v1/`;
  interpretation:
  `implementation/algolab/experiments/protocol-232-v1-analysis/REPORT.md`.
  No prior verdicts altered.
