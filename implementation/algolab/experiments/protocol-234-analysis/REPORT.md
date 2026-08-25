# Protocol-234 Analysis Report: Decision-Rule Format Isolation

**Status:** Post-execution analysis of the pre-registered experiment series
(spec/research/234_DECISION_RULE_FORMAT.md, frozen before execution).
Evidence: four checksummed bundles under
`experiments/protocol-234-p{30,60,120,240}/`.

Design recap: the four protocol-233 sweep points re-run with two added
frozen arms that read the SAME family slices and differ from B-fam+ only
in consumer arithmetic — **B-com** (`knowledge-informed-family-commit`,
frozen monotherapy on the slice's rate-per-credit argmax) and **B-alloc**
(`knowledge-informed-family-alloc`, deficit-scheduled attempt shares
proportional to rate per credit over the full catalog). No online
learning, no RNG, no new information. trials = 128 per point.

## 1. Headline result (per-family mean efficiency)

| arm | alpha p30 | alpha p240 | beta p30 | beta p240 |
|---|---|---|---|---|
| B-fam+ (cycle, top-3) | 0.05792 | 0.05792 | 0.05860 | 0.04164 |
| B-alloc (proportional) | 0.04358 | 0.05776 | 0.04146 | 0.05204 |
| **B-com (commitment)** | **0.07349** | **0.07349** | **0.07328** | **0.07328** |
| C+fam (adaptive) | 0.07181 | 0.07349 | 0.07079 | 0.07328 |

Held-out gamma (pooled-slice fallback): B-com 0.07375 / C+fam 0.07220 /
B-alloc 0.032–0.038.

Cross-point SE ≈ 0.0007 (128 paired trials/point).

## 2. Pre-registered hypothesis scoreboard

| # | Hypothesis | Verdict |
|---|---|---|
| H1 | commitment closes most of the gap; forecast B-com(beta,p240) ∈ [0.065, 0.075] | **PASS** — actual 0.07328; B-com sits AT the single-operator ceiling (~0.0734) at every prior size |
| H2 | allocation intermediate; ordering B-fam+ ≤ B-alloc ≤ B-com; forecast [0.040, 0.058] | **PASS** — 0.04164 ≤ 0.05204 ≤ 0.07328; actual within band |
| H3 | C+fam ≥ max(frozen variants) everywhere | **FALSIFIED** — B-com ≥ C+fam at p30 on both families and marginally at p60/p120 on beta; equal at p240 |
| H4 | B-com ≥ random floor everywhere | **PASS** (0.073 vs 0.017) |

The registered interpretation branch "H1 pass ∧ small residual" applies:
**decision-rule format is the first-order lever; online correction is
second-order in this substrate.**

## 3. What this resolves

Protocol 233 left a paradox: the frozen-vs-adaptive margin survived a 16x
range of history volume unchanged, suggesting a structural limit of frozen
consumers. Protocol 234 identifies the structure precisely:

- **It was the cycle, not the freezing.** Committing to a single
  well-chosen operator — the simplest possible frozen rule — reaches the
  theoretical ceiling immediately and stays there regardless of prior size
  (identical values at p30–p240: the argmax never changed).
- **Allocation confirms the continuity diagnosis.** B-alloc improves
  monotonically with prior size (beta 0.0415 → 0.0520) exactly because
  deficit scheduling is *continuous* in weight estimates — better knowledge
  smoothly shifts spend away from expensive operators. The top-K cycle,
  being discontinuous, could not convert better estimates into better
  behavior (protocol 233). Same data, three formats: step function
  (cycle) < smooth (alloc) = ceiling (commit).
- **Adaptation's measurable edge over commitment is ≈ 0 here — and
  negative at thin history.** At p30, C+fam trails B-com by ~3% (its
  exploration spends credits on non-argmax operators; B-com does not).
  Adaptation's true residual value is *insurance*: if the frozen argmax
  had been mis-ranked, B-com would collapse while C+fam recovers online.
  This K0 realization never mis-ranked the argmax, so the insurance
  premium was visible and the payout never was. (On held-out gamma the
  pooled-fallback argmax happened to be useful in gamma too — a property
  of this ground-truth construction, not a guarantee.)

## 4. Revised decomposition of the original beta null (protocols 230–234)

| lever | contribution to closing the v1 beta gap (C≈B at 0.0264 → oracle 0.0734) |
|---|---|
| more/better-pooled data (233) | none — cycle format cannot use it |
| family-conditioned representation (232) | necessary: fixes which operators look good per task |
| cost-normalization inside the selector (231) | necessary: ranks cheap-good operators correctly |
| **consumer format: commit, don't cycle (234)** | **sufficient at the ceiling**: zero-learning monotherapy on the family-conditioned cost-argmax |
| online updates (231/232) | second-order here: estimation insurance, not steady-state performance |

## 5. Scope and caveats

- Toy substrate with known ground truth; cheap-useful operators exist in
  every family and the pooled argmax happens to transfer to gamma.
  Commitment's known failure mode (wrong argmax → unrecoverable) did not
  occur in these realizations; measuring that fragility requires multiple
  prior seeds or adversarial slices (not run).
- B-com's dominance assumes estimate quality sufficient to rank ONE
  operator correctly — a far weaker requirement than ranking a full top-K,
  which is why it succeeds already at p30 while B-fam+/B-alloc still gain
  from volume.
- No promotion claims are registered or altered; the protocol-231 criterion
  for C+ remains met as recorded; all earlier bundles untouched.

## 6. Next step (not started)

If pursued (pre-register as 235): multi-seed prior robustness — repeat the
p30 cell across N independent `prior_seed` values to measure the
commit-vs-adapt trade-off as an insurance pricing problem (mean loss of
B-com when argmax mis-ranks vs C+fam's exploration overhead when it does
not). This directly quantifies when the loop earns its keep.
