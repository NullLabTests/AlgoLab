# Decision-Rule Format Isolation (Protocol 234)

**Status:** Pre-registered. Hypotheses, arms, parameters, and decision
rules are frozen BEFORE execution of experiments
`protocol-234-p{30,60,120,240}`. Reference points: frozen bundles of
protocols 230–233. Post-execution changes appear only as dated amendment
entries.

## 1. Motivation

Protocol 233 established that the adaptive margin over frozen knowledge is
structural: it survived a 16x range of prior volume unchanged and arises
because a top-K *cycle* cannot express "concentrate spend on cheap useful
operators." But protocol 233 conflated two candidate causes inside the
frozen consumer's format:

(a) **forced diversification** — cycling forces equal attempt counts across
top-3 regardless of cost or quality;
(b) **rank-based arithmetic** — ordering operators cannot express spend
*shares*, only sequence.

This protocol separates them by adding two frozen consumers that read the
SAME family slices with the SAME estimates and differ from B-fam+ ONLY in
consumer arithmetic. Zero online learning, zero new information.

## 2. Question

How much of the structural frozen-vs-adaptive margin is closed by the
decision rule alone — commitment (monotherapy on the cost-argmax) and/or
deterministic proportional allocation — with no adaptation at all?

## 3. Arms (fixed)

Carried over unchanged: all nine main arms and three ablations of
protocols 232/233. New arms:

| Arm | Definition |
|---|---|
| **knowledge-informed-family-commit (B-com)** | frozen monotherapy: always selects argmax(smoothed rate ÷ credit cost) of the current family's K0 slice; pooled-slice fallback for families without history; never updates |
| **knowledge-informed-family-alloc (B-alloc)** | deterministic deficit-scheduled allocation: attempt-count shares proportional to smoothed rate ÷ credit cost over the FULL catalog (weights normalized to fractions φ; each step adds φ to every quota, selects argmax quota, subtracts 1); per-family slices with pooled fallback; never updates |

Both use the same smoothing, the same slices, and the same cost basis as
B-fam+. Neither receives budget state (same select() contract as all
arms; unaffordable selections end episodes under the shared stopping rule,
identically to every carried-over arm).

## 4. Experimental grid (fixed)

The four sweep points of protocol 233, re-run with the two additional
arms: `prior_attempts_per_family ∈ {30, 60, 120, 240}`, trials = 128,
seeds/budgets/rotation/gate/top_k unchanged, held-out phase unchanged.
Experiment ids `protocol-234-p{size}`. Carried-over arms are expected to
reproduce their protocol-233 values exactly within each point (identical
configurations and per-arm RNG streams).

## 5. Pre-registered hypotheses with numeric forecasts

Using beta p240 as the primary cell (stable rankings; C+fam ≈ 0.0733;
B-fam+ = 0.04164; margin ≈ +0.0316):

- **H1 (commitment closes most of the gap):**
  B-com(beta, p240) ∈ [0.065, 0.075] — i.e., captures ≥ ~70% of the margin.
  Basis: beta slice cost-argmax is reparameterize (10 cr, true success
  ≈ 0.73), so committed efficiency should approach the single-operator
  ceiling ≈ 0.0734.
- **H2 (allocation intermediate):**
  B-alloc(beta, p240) ∈ [0.040, 0.058]: proportional weights still assign
  meaningful spend to expensive synthesize (equal rate, 4x cost ⇒ equal
  *credit share*, not quarter share), so most of the diversification tax
  remains. Ordering registered: B-fam+ ≤ B-alloc ≤ B-com on beta p240.
- **H3 (residual genuine adaptation):** C+fam ≥ max(B-com, B-alloc) on
  every family at every point; the residual C+fam − B-com at p240 quantifies
  the part of the margin attributable to online correction rather than
  decision-rule format.
- **H4 (robustness guard):** B-com ≥ random-arm efficiency on both training
  families at every point (a sanity bound against catastrophic
  mis-ranking; no cross-draw variance claims are possible with one
  deterministic K0 per point).

Interpretation branches (registered):

- H1 pass ∧ small residual → the loop's value decomposes as: knowledge for
  estimation + decision-rule format as first-order lever; online correction
  second-order in this substrate.
- H1 fail (commit stays near cycle level) → even commitment cannot express
  what's needed; the margin belongs to feedback itself, not format.

## 6. Comparisons and correction

Added pairs (BH-corrected within each family block, appended to the
protocol-232 matrix):

1. knowledge-informed-family-cost-rank vs knowledge-informed-family-commit
2. knowledge-informed-family-commit vs adaptive-cost-aware-family
3. knowledge-informed-family-cost-rank vs knowledge-informed-family-alloc
4. knowledge-informed-family-alloc vs adaptive-cost-aware-family

Cross-point analysis descriptive (SE ≈ 0.0007 per cell, n = 128).

## 7. Guarantees

- No changes to any existing arm, seed, gate, threshold, or harness loop;
  additions only. Golden v1 regression must stay green; carried-over arms
  must reproduce protocol-233 numbers exactly within matching points.
- No tuning of any policy against any family after seeing results.

## 8. Amendment log

- **2026-08-25 (post-execution record; no design change):** all four
  points executed as registered with the two added arms. Outcome: H1 PASS
  (B-com = 0.07328–0.07349 on both families at every prior size — at the
  theoretical ceiling), H2 PASS (alloc intermediate, monotone in data),
  H3 FALSIFIED (commitment ≥ adaptive at thin history; equal at large),
  H4 PASS. Conclusion: the protocol-233 structural margin is a top-K-cycle
  artifact; zero-learning commitment to the family-conditioned cost-argmax
  matches the adaptive loop here, and adaptation's residual value is
  estimation insurance rather than steady-state performance.
  Evidence: `implementation/algolab/experiments/protocol-234-p{30,60,120,240}/`;
  interpretation:
  `implementation/algolab/experiments/protocol-234-analysis/REPORT.md`.
  No prior verdicts altered.
