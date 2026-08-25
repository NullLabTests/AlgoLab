# Prior-Size Dose-Response (Protocol 233)

**Status:** Pre-registered. Hypotheses, sweep points, parameters, and
decision rules are frozen BEFORE execution of experiments
`protocol-233-p{30,60,120,240}`. Reference points: frozen bundles of
protocols 230–232. Post-execution changes appear only as dated amendment
entries.

## 1. Motivation

Protocol 232 showed that family-conditioned knowledge repairs most — but
not all — of the frozen policies' deficit: C+ retains a real margin over
the best frozen composite (B-fam+), concentrated on beta (d = 5.2). The
residual gap was attributed to thin per-family history (~7.5 uniform
attempts per operator at `prior_attempts_per_family = 60`) mis-ranking
frozen schedules that cannot re-rank mid-trial. That attribution is a
hypothesis; this protocol tests it directly by varying history quantity.

## 2. Question

Does the adaptive margin over frozen knowledge shrink as prior data grows —
i.e., is adaptation value ∝ 1/history quality?

## 3. Design (fixed before execution)

Four experiment instances, identical to protocol-232-v1 in every respect
except one swept parameter:

| instance | prior_attempts_per_family | attempts/op/family (÷8 ops) |
|---|---|---|
| protocol-233-p30 | 30 | ~3.75 |
| protocol-233-p60 | 60 | ~7.5 (= protocol 232 configuration) |
| protocol-233-p120 | 120 | ~15 |
| protocol-233-p240 | 240 | ~30 |

- Arms: all nine main arms of protocol 232 plus the three ablations,
  unchanged.
- trials = 128; seeds/budgets/rotation/gate/top_k unchanged; held-out phase
  unchanged.
- Each point is an independent registered configuration: the K0 generator
  consumes its RNG stream per family sequentially, so slices at different
  sizes are different draws, not strict prefixes. Cross-point comparison is
  therefore between configurations, not within a nested sequence.
- No code changes are required; no new mechanisms; no new promotion claim.

## 4. Hypotheses (fixed before execution)

- **H1 (frozen dose-response):** B-fam+ mean efficiency increases with
  prior size on beta across p30 < p60 < p120 < p240 (monotone ordering;
  adjacent contrasts positive). On alpha, saturation near C+ may flatten
  the curve — assessed descriptively.
- **H2 (adaptive margin shrinks):** paired delta (C+fam − B-fam+) on beta
  decreases with prior size, with delta(p240) < delta(p30). On alpha the
  delta is expected small at every size.
- **H3 (graceful degradation / ceiling):** C+fam stays within 10% of its
  best sweep-point efficiency on each training family at every size
  (adaptation degrades gracefully with worse priors and does not degrade
  with more history).
- **H4 (mechanism, descriptive):** rank agreement between family-slice
  smoothed rates and ground truth improves with prior size (reported as
  Spearman correlation of slice rates vs true effect values per family).

Falsification branches:

- H2 fails (margin constant/growing) → the residual adaptive margin is not
  a thin-data artifact; it reflects structural limits of any frozen
  schedule → knowledge-layer investment alone cannot close it.
- H1 fails (frozen flat) → per-family cells remain too noisy even at 240
  → next lever is shrinkage/hierarchical priors, not volume.

## 5. Comparisons and correction

Within-point: the full protocol-232 primary matrix, BH-corrected per
family block (unchanged). Cross-point: descriptive means ± SE (n = 128)
with adjacent-pair sign checks and the pre-registered orderings above; no
new multiplicity regime is introduced beyond BH within points.

## 6. Guarantees

- Protocols 230–232 bundles remain byte-frozen; existing suite (including
  golden v1 regression) must stay green. Sweep uses only pre-existing
  config surface (`prior_attempts_per_family`), so no behavioral change to
  any carried-over arm at fixed config.

## 7. Amendment log

- **2026-08-25 (post-execution record; no design change):** all four
  points executed exactly as registered. Outcome: H1 FALSIFIED, H2
  FALSIFIED (registered falsification branch applies — the adaptive margin
  is structural, not thin-data), H3 PASS, H4 partial/descriptive.
  Mechanism: ranking accuracy improves with volume but frozen top-K cycle
  quality is a step function; correctly-learned expensive-useful operators
  displace cheap slots and lower cycled efficiency (beta: 0.0586 at p30 →
  0.04164 at p60+; C+fam flat at ~0.071–0.073 throughout).
  Evidence: `implementation/algolab/experiments/protocol-233-p{30,60,120,240}/`;
  interpretation:
  `implementation/algolab/experiments/protocol-233-analysis/REPORT.md`.
  No prior verdicts altered.
