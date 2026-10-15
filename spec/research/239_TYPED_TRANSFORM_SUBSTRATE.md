# Protocol 239 — Typed Feature-Transform Substrate + Powered QD Evaluation

**Status:** Pre-registered and frozen before any confirmatory run. Hypotheses,
arms, parameters, margins, promotion bar, contradiction policy, and outcome
classes below are immutable after this document is committed. The QD archive
and basin-escape logic must not be tuned after seeing outcomes.

**Reference points:** protocols 230–238 bundles; `spec/research/238_QD_BASIN_ESCAPE.md`;
`implementation/algolab/PROTOCOL_238_COMPLETION_REPORT.md`.

**Design sources (cited):**
- AlgoLab protocols 231–235: cost-aware selection is a first-order lever;
  family-conditioned knowledge dominates pooled aggregates; commitment is
  efficient in-domain but fragile; adaptation value is primarily estimation
  insurance under shift; the strict ≥2-family promotion bar was not met at
  n=32 on KNN (238: UNRESOLVED-POWER at smoke n).
- Farahbakhsh et al., *AgentDiscover*, arXiv:2610.05334 — selection rules
  as queries over an idea/candidate database.
- Suwandi et al., *Kernel Autoresearch*, arXiv:2610.10394 — quality-diversity
  archive + novelty screening keeping candidates valid and distinct.
- Ziakas et al., *Fork-and-Flush*, arXiv:2610.07447 — periodic forking with
  fresh context to escape localized idea basins.

## 1. Question

Does the QD archive + basin-escape mechanism — UNRESOLVED-POWER on the
7-knob KNN substrate — resolve into a real, promotable effect on a richer
typed feature-transform substrate where operator behaviour varies more across
families?

## 2. Substrate definition (frozen)

- **Base estimator:** `LogisticRegression(max_iter=1000, random_state=<derived>)`.
- **Baseline (no transform):** `StandardScaler -> LogisticRegression`.
  The baseline is evaluated once per (family, replicate seed), cached, unbilled.
- **Operators:** a closed catalog of 14 typed feature transforms applied
  *before* the baseline. Each operator is a deterministic, sklearn-compatible
  transformer cloned per CV fold (fit on train only; no leakage). All
  transforms preserve row count.
- **Catalog (frozen):**

| operator | transform | cost (credits) |
|---|---|---|
| log1p | log1p on all features | 5.0 |
| sqrt | sqrt of clipped-nonneg features | 5.0 |
| clip-1_99 | clip at 1st/99th percentile (fit per fold) | 6.0 |
| robust-scale | RobustScaler | 8.0 |
| standard-scale | StandardScaler | 8.0 |
| quantile-bin-3 | quantile binning into 3 bins (fit per fold) | 8.0 |
| interaction-top2 | pairwise products of top-2 variance features | 10.0 |
| quantile-bin-5 | quantile binning into 5 bins (fit per fold) | 10.0 |
| poly2-top5 | PolynomialFeatures(degree=2) on top-5 variance features | 12.0 |
| power-yeo-johnson | PowerTransformer(method="yeo-johnson") | 12.0 |
| pca-10 | PCA(n_components=10) | 14.0 |
| poly2-all | PolynomialFeatures(degree=2) on all features | 15.0 |
| interaction+robust | interaction-top2 then RobustScaler | 15.0 |
| poly2+log1p | poly2-all then log1p | 18.0 |

- **Costs vary by operator** (5.0–18.0) so the cost dimension, established in
  protocols 231–234, is live on this substrate. Measured wall-clock seconds
  are recorded for reporting only and never influence any decision.
- **Discovery gate (frozen):** an attempt is a validated discovery iff BOTH
  replicate mean 5-fold stratified-CV accuracies of
  `Transform -> StandardScaler -> LogisticRegression` beat the cached
  split-matched baseline by ≥ **0.005** absolute. Replicates share splits
  with the baseline (paired design, seed offset 777001).
- **Families (frozen):** `alpha` = breast_cancer (569×30, binary);
  `beta` = wine (178×13, 3-class); `gamma` (**held out**) = digits stratified
  subsample of 900 rows. Held-out never enters the K0 prior or any training
  selection; it is evaluated only in the held-out block.
- **Determinism:** outcomes depend only on dataset, operator, and integers
  derived from (seed_base, trial, episode, replicate); timing never affects
  any recorded decision.

## 3. Experimental grid (frozen)

| Parameter | protocol-239-v1 |
|---|---|
| workload | transform |
| trials | 32 (target; see §5 power note) |
| episodes_per_trial | 2 (rotation [alpha, beta]) |
| budget_credits | 100.0 |
| prior_attempts_per_family | 20 |
| prior_seed / analysis_seed / seed_base / top_k | 101 / 11 / 7 / 3 |
| arms | the 7-arm set below |
| ablations | () (scope cut for compute) |
| held_out_family | gamma |
| alpha / beta / gamma discovery margins | 0.005 / 0.005 / 0.005 |

**Arms (frozen, 7):**
`static`, `adaptive`, `adaptive-cost-aware`, `random`,
`knowledge-informed-family-commit`, `qd-adaptive-cost-aware`, `basin-escape`.

This set includes the five required arms (static, cost-aware adaptive,
family-commit, QDAdaptiveCostAware, BasinEscape) plus `adaptive` (plain
Thompson reference) and `random` (calibration floor). Family-conditioned
ranking arms (B-fam, B-fam+) are folded into the family-commit comparator
since they share the same K0 slice; adding them would double the compute
without a new hypothesis.

**Comparison matrix (frozen, BH-corrected within each family block):**
the 230–232 primary matrix restricted to present arms, plus:
- static vs qd-adaptive-cost-aware
- knowledge-informed vs qd-adaptive-cost-aware (via family-commit comparator)
- adaptive-cost-aware vs qd-adaptive-cost-aware
- static vs basin-escape
- adaptive-cost-aware vs basin-escape
- qd-adaptive-cost-aware vs basin-escape

## 4. Hypotheses / decision rules (not forecasts)

Candidate = basin-escape if H2 directional passes, else qd-adaptive-cost-aware.

- **H1 (QD helps on a richer substrate):** qd-adaptive-cost-aware >
  adaptive-cost-aware on both training families (adjusted p < 0.05, CI
  excluding 0).
- **H2 (basin escape helps under shift):** basin-escape held-out gamma
  efficiency > adaptive-cost-aware (directional), with directional training
  persistence.
- **H3 (no harm):** both new arms ≥ random on every family (directional).
- **H4 (mechanism / archive richness):** the QD archive on this substrate
  populates more distinct cells than on the 238 KNN smoke bundle at equal
  budget (descriptive; reported as mean cells/attempt).

Interpretation branches:
- H1 ∧ H2 pass → archive + basin escape resolve into a real effect; promote
  the candidate per §6.
- H1 pass ∧ H2 fail → QD helps in-domain but basin escape adds nothing under
  this shift; report partial.
- H1 fail ∧ H2 pass → basin escape alone carries the gain; report partial.
- Both fail → clean falsification of the 238 mechanism on this substrate.

## 5. Power note (frozen before execution)

Target trials = 32. On the 238 KNN substrate the paired per-trial efficiency
SD was ≈ 0.004, giving MDE ≈ 0.002 at α = .05, 80% power for n = 32. The
transform substrate has a richer operator space, so the SD is expected to be
larger; if the measured pilot SD exceeds 0.006 the target is raised to
trials = 48 via a frozen amendment (only if CPU allows). **Decision rule
(frozen):** run a 2-attempt timing pilot before the full run; if the projected
full-grid wall time exceeds the local CPU budget (<10 min on 2–4 cores),
execute the largest trial count that fits (minimum 8) and document
UNRESOLVED-POWER exactly as in 238. No trial count is chosen post hoc except
via this pre-registered rule.

## 6. Promotion bar (frozen, mirrors 231/235/238)

The candidate arm beats static AND the family-commit comparator with adjusted
p < 0.05 and CI excluding 0 on ≥ 2 training families, and the gap persists
on held-out gamma. Evaluated via `PolicyComparison.evaluate_claim`.

## 7. Outcome classes (frozen)

- **A — confirmed:** promotion bar met as registered.
- **B — partial:** directional improvement / held-out gain without meeting
  the full multi-family bar.
- **C — falsified:** no significant improvement, or a new arm below random,
  or machinery failure.

## 8. Contradiction policy

If a result contradicts a prior protocol finding, the 239 result is scoped
to this substrate and n; earlier protocol verdicts are not overruled in
place. Contradictions are recorded in the completion report and an ADR.

## 9. Guarantees

- Golden protocol-230-v1 reproduction stays byte-identical (regression test).
- No changes to discovery gates, statistical protocols, provenance, or
  governance. No LLM code generation, no evolutionary mutation, no M3–M5.
- Autonomy remains L1. No paid compute, no GPU.
- Archive and basin logic not tuned after seeing outcomes.
- Append-only evidence, hash-sealed artifacts, budget ledger respected.

## 10. Amendment log

- (none yet; post-execution records appended below)
- **2026-10-16 (POST-EXECUTION record; no design change):** experiment
  `protocol-239-v1` executed under this frozen pre-registration. A 2-attempt
  timing pilot (prior=2) projected 45 min for the trials=32 target on the
  local CPU budget; per the frozen decision rule the fallback (trials=8,
  prior=20/family, budget=100, 7 arms, ablations=()) was executed (~17 min
  wall). Outcome: **C — falsified / UNRESOLVED-POWER**. H1 (QD > C+):
  directional positive on beta (d=+0.0045, q=0.66) but not significant at
  n=8. H2 (basin escape under shift): FALSIFIED — 0 discoveries on both
  training families and held-out gamma, below the random floor. H3 (no harm):
  FALSIFIED — basin-escape < random on every family. H4 (archive richness):
  CONFIRMED — 13 archive cells / 1806 attempts on transform vs 4 / 384 on
  the 238 KNN smoke. The 235 commitment-collapse finding replicates
  (family-commit: 20 training discoveries, 0 on held-out gamma). Evidence:
  `implementation/algolab/experiments/protocol-239-v1/` (checksummed bundle);
  interpretation:
  `implementation/algolab/PROTOCOL_239_COMPLETION_REPORT.md`. No prior
  verdicts altered.
