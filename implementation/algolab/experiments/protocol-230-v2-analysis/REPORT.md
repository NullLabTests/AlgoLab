# Protocol-231 Analysis Report: Cost-Aware Selection (experiment protocol-230-v2)

**Status:** Post-execution analysis of the pre-registered experiment
`experiments/protocol-230-v2/` (spec/research/231_COST_AWARE_SELECTION.md,
frozen before execution). The generated bundle in
`experiments/protocol-230-v2/` (manifest, statistics, raw streams,
checksums) is the primary evidence; this document interprets it against the
pre-registered hypotheses. Exploratory statements are labeled as such.

Analysis date: 2026-08-23. Design summary: arms A/B/C/D carried over
unchanged from protocol 230; new arms **C+** (`adaptive-cost-aware`,
selection = argmax θ/cost over unchanged Beta posteriors) and **B+**
(`knowledge-informed-cost-rank`, frozen K0 ranked by rate÷cost); ablation
**c-plus-permuted** added; trials = **128** (pre-registered power: MDE ≈
0.0019 ≈ 7% of B's beta mean); everything else identical to v1.

## 1. Headline result

| family | B | B+ | C | C+ | C+ vs B |
|---|---|---|---|---|---|
| alpha | 0.01603 | 0.04936 | 0.02826 | **0.06376** | d = 9.7 |
| beta | 0.02640 | 0.02547 | 0.03016 | **0.07006** | **d = 8.6** |
| held-out gamma | 0.01636 | 0.02594 | 0.05709 | **0.07205** | — |

Beta, C+ > B: delta **+0.04367**, CI [+0.04274, +0.04457], adjusted
p = 0.0005, Cohen's d = **8.62** (+165% relative).

**Promotion criterion (230 §5 form, candidate = C+) is MET**: C+ > A and
C+ > B on both training families (adjusted p < 0.001 everywhere, CI well
above 0) and the gap persists on held-out gamma (C+ 0.0721 vs B 0.0164,
d ≈ 5–9 range in held-out comparisons). This is the first Level-1 pass of
the knowledge-loop claim under a pre-registered ≥2-family criterion — in
the toy environment, with the scope caveats below.

## 2. Pre-registered hypothesis scoreboard

| # | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | C+ > B on beta | **PASS** | delta +0.0437, q = 0.0005, d = 8.62 |
| H2 | C+ > B+ on beta (loop necessity) | **PASS** | C+ 0.0701 vs B+ 0.0255 (delta +0.0446, q = 0.0005, d = 8.53); B+ ≈ B on beta (0.0255 vs 0.0264) |
| H3 | no harm: C+ > A everywhere; C+ ≥ C directionally | **PASS** | alpha d = 9.79, beta d = 11.35 vs static; C+ > C on every family (d = 4.3–4.7) |
| H4 | mechanism: C+ reaches `refresh` on beta | **PASS** | 194 selections (v1: 0), 142 discoveries (73.2%, ≈ reparameterize's 73.4%) |

All four pre-registered interpretations therefore resolve to the first
branch: **beta failure attributed to selector cost-blindness, with the
online loop contributing information that a frozen cost-ranked reading of
history cannot order statically.**

## 3. Why this resolves the v1 beta question

The v1 diagnosis predicted exactly this asymmetry, and every leg landed:

- **Prior saturation was real but not fundamental.** B+ shows that merely
  *reordering* the frozen K0 by cost does not help on beta (its top-3 =
  reparameterize + two neutral operators; misses both synthesize and
  refresh): 0.0255 ≈ B's 0.0264. Knowledge alone, however indexed, stays
  stuck near B because pooled history ranks refresh below three neutral
  operators.
- **Cost-blindness was the binding constraint.** Switching only the
  selection objective (same posteriors, same feedback) moved beta from
  C = 0.0302 to C+ = 0.0701 — capturing **95% of the all-reparameterize
  oracle** (0.0734 estimated in the v1 analysis §5).
- **The loop matters again on beta once selection is cost-normalized.**
  c-plus-permuted degrades to 0.0447 (< C+, q-level separation in the
  ablation table) — unlike v1, where permuted-C ≈ C on beta. Mechanism:
  with a cost-normalized objective, cheap-but-prior-suppressed `refresh`
  becomes reachable through Thompson tail draws; its successes then feed
  back into posteriors (142/194 discovered). Under the probability-only
  objective those same tail draws were outcompeted before any feedback
  could accumulate.
- **Behavioral trace:** C+ on beta puts 93.3% of attempts on
  `reparameterize` (10 cr, 73.4% discovery) and never locks onto expensive
  `synthesize`; on alpha it concentrates on the two *cheap* useful
  operators (tune, validate) and drops the neutral tier that consumed 37.5%
  of B's budget.

## 4. Continuity with v1 (no contradiction)

Carried-over arms reproduce their v1 qualitative pattern with tighter
precision (n = 128): C > B > A pooled; C ≫ B on alpha (d ≈ 2.0); C ≈ B on
beta (delta +0.0038, q = 0.0005 — now *significantly* positive but tiny,
d = 0.45, i.e., v1's point estimate +4.7% relative was accurate, just
imprecisely measured); c-permuted collapse on alpha; b-shuffled ≈ B.
Nothing in v2 requires revising the v1 record; v1's beta null stands as
measured, now explained.

## 5. Scope and caveats

- Toy environment with known ground truth; the claim promoted is the loop
  mechanism inside this substrate, not real-workload performance.
- The environment's cost structure (10-cr useful operators exist in every
  family) makes cost-normalization unusually decisive; families whose only
  useful operators are expensive would reward different objectives.
- C+ inherits Thompson sampling's per-trial resets; longer-horizon
  persistence, non-stationary families, and credit-aware priors remain
  untested (exploratory observations, not registered claims).
- Plain C remains governed by protocol 230: its promotion criterion is
  still NOT met, and nothing here retroactively changes that.

## 6. Recommended next step (not started)

Smallest increment with new information: a **family-conditioned or
credit-weighted prior** variant evaluated identically (pre-register as
232), testing whether the remaining gap between B+/frozen-knowledge arms
and C+ closes when history itself is cost-normalized at construction time
— the one lever this experiment deliberately left untouched.
