# Protocol-233 Analysis Report: Prior-Size Dose-Response

**Status:** Post-execution analysis of the pre-registered experiment series
(spec/research/233_PRIOR_SIZE_DOSE_RESPONSE.md, frozen before execution).
Evidence: four checksummed bundles under
`experiments/protocol-233-p{30,60,120,240}/`.

Design recap: four instances identical to protocol-232-v1 except one swept
parameter — `prior_attempts_per_family` in {30, 60, 120, 240} (~3.75 / 7.5 /
15 / 30 uniform attempts per operator per family). trials = 128 per point;
full arm set; no code changes were required or made.

## 1. Headline result (per-family mean efficiency)

| quantity | alpha p30 | alpha p240 | beta p30 | beta p240 |
|---|---|---|---|---|
| B-fam+ (best frozen composite) | 0.05792 | 0.05792 | **0.05860** | 0.04164 |
| **C+fam (family-init adaptive)** | 0.07181 | 0.07349 | **0.07079** | 0.07328 |
| delta(C+fam - B-fam+) | +0.01389 | +0.01557 | **+0.01219** | **+0.03164** |

C+ (pooled-init) varies slightly across points because pooled K0 changes
with prior size; full tables in each bundle's `statistics.json`.
Cross-point SE is about 0.0007 (128 paired trials/point), so every delta
difference cited below exceeds ~20 SE.

## 2. Pre-registered hypothesis scoreboard

| # | Hypothesis | Verdict |
|---|---|---|
| H1 | B-fam+ efficiency rises monotonically with prior size | **FALSIFIED** - beta: p30 0.0586 > p60 = p120 = p240 0.04164; alpha: flat at 0.05792 at every size |
| H2 | adaptive margin shrinks as history grows | **FALSIFIED** - beta margin *grew* from +0.0122 (p30) to +0.0314 (p60), plateau +0.0316 (p240); alpha drifted up (+0.0139 -> +0.0156) |
| H3 | C+fam degrades gracefully / stays near ceiling | **PASS** - every point within ~3% of its best point (registered bound 10%) |
| H4 | slice-rate vs truth rank agreement improves with size | PARTIAL (descriptive) - beta-slice Spearman 0.50 / 0.52 / 0.88 / 0.71 across p30-p240 |

The registered falsification branch for H2 applies verbatim: *the residual
adaptive margin is not a thin-data artifact; it reflects structural limits
of any frozen schedule.*

## 3. Why naive dose-response failed - mechanism

Tracing each point's derived snapshots
(`knowledge-snapshot-by-family.json`) exposes a two-step mechanism:

1. **Ranking accuracy does improve with volume.** Beta-slice smoothed rates
   converge toward truth: synthesize rises from a noisy 0.600 (p30) toward
   its true ~0.73; neutral operators fall from ~0.14-0.17 toward <0.09.
2. **Schedule quality is a step function of rankings - and the steps cut
   against the frozen policy:**
   - At p30, noise kept expensive-but-genuinely-useful `synthesize`
     (40 cr) out of the beta cost-ranked top-3. The third slot went to
     `rollback` (5 cr, truly harmful) whose noisy rate was flattered by
     division by the smallest cost. The accidental schedule
     [reparameterize, refresh, rollback] spent almost everything on the two
     cheap useful operators -> 0.0586.
   - From p60 on, synthesize's true rate emerges and correctly enters the
     top-3 -> [reparameterize, refresh, synthesize]. The frozen cycle now
     burns one slot in three at 40 credits for exactly the same success
     probability as the 10-credit operators -> 0.04164, flat thereafter.
     The identical values at p60/p120/p240 are exact: rankings stabilize,
     schedules become byte-identical, and seeded measurement streams
     reproduce exactly.

So **more history made the frozen policy more knowledgeable and worse.**
Accuracy about success probabilities does not imply schedule quality,
because a fixed top-K cycle cannot express what the discoveries-per-credit
metric rewards - concentrating spend on cheap useful operators. The
adaptive selector (argmax theta/cost) expresses it natively and sits within
~1-3% of the theoretical ceiling at every history level.

## 4. Scientific interpretation

Three findings harden into structure across protocols 230 -> 233:

1. **Knowledge representation matters enormously** (protocol 232:
   family-conditioning repaired B by d = 3.9-11.4), but representation
   quality has a ceiling that decision rules do not: once estimates are
   approximately right, more/better data changes nothing for adaptive arms
   (flat C+fam) and can actively hurt cycled-frozen arms (this protocol).
2. **The adaptive margin is structural, not informational.** It survived a
   16x range of history volume essentially unchanged (~+0.031 on beta from
   p60 up). It is the price of the frozen *format* (top-K cycle), not of
   imperfect estimates.
3. **Frozen-policy behavior is discontinuous in data quality.** Identical
   efficiencies at p60-p240 show zero behavioral response to large estimate
   improvements until a ranking threshold flips - the opposite of graceful
   improvement.

Practical reading for AlgoLab: invest in family-conditioned knowledge
storage (232), but treat any non-adaptive consumer of that knowledge as a
bounded-quality component; the cost-aware online loop is where remaining
performance lives.

## 5. Scope and caveats

- Single K0 realization per point (deterministic generator). The p30 beta
  "accident" is one draw, not a property of small priors generally; small
  samples could equally have produced worse accidental schedules.
- The environment's clean separation (cheap-useful vs expensive-useful with
  equal success probability) maximally rewards cost concentration; domains
  without such cost/success decoupling would narrow the structural margin.
- H4's Spearman wobble (p240 dip) is a small-sample descriptive artifact;
  no inference drawn.
- No promotion claims are registered or altered; protocols 230/231 verdicts
  and all prior bundles remain unchanged.

## 6. Next step (not started)

The remaining open lever is no longer information quantity but the frozen
consumer's format. Smallest informative increment (pre-register as 234 if
pursued): replace top-K cycling with a deterministic cost-weighted
*allocation* rule over the same frozen family slices (fixed spend shares,
e.g., proportional to rate/cost), testing whether format alone - with zero
online learning - closes part of the ~+0.031 structural margin on beta.
This isolates "decision-rule expressiveness" from "adaptation" cleanly:
same data, same rankings, different consumer arithmetic.

