# Real-Workload Promotion at Higher n (Protocol 236)

**Status:** Pre-registered. Design, hypotheses, arms, parameters, and
decision rules are frozen BEFORE execution of experiment `protocol-236-v1`.
Reference points: `protocol-235-v1` (executed bundle; the frozen reference)
and `spec/research/235_REAL_WORKLOAD_BRIDGE.md` §6-§10.

**Amendment discipline:** this is the smallest pre-registered 235§6 next
step, executed with everything else frozen. The single registered lever is
**alpha-side discovery-margin recalibration**; the second pre-registered
lever (a third training family with richer discovery structure) is a fallback
only and explicitly deferred to a later protocol (see §7).

## 1. Motivation

Protocol-235 tested the pre-registered knowledge-loop claim
(H1: adaptive-cost-aware > static AND > knowledge-informed on ≥2 families)
on a real KNN micro-HPO workload and honestly reported it **not met** at
n = 32: beta ordering was replicable (static < B < C ≈ C+, q < 0.025) but
alpha was discovery-starved (baseline CV accuracy ≈ 96.5%; almost no
operator clears the registered 0.005 gate on both replicate seeds), so the
"≥2 families" clause of H1 could not be satisfied. Protocol 235 §6 therefore
pre-registered the next smallest lever: *"re-run this exact grid with
trials=96 and an alpha-side margin recalibration … to give H1 statistical
room; everything else frozen."* This protocol executes exactly that.

## 2. Question

Does the promotion claim (H1) survive contact with a real machine-learning
search problem when (a) the trial count is raised from 32 to 96 and (b) the
alpha discovery margin is recalibrated to the measurement lattice of
breast_cancer — *everything else byte-frozen to protocol-235-v1*?

## 3. The registered lever: alpha margin recalibration (fixed)

The alpha margin is a **structural measurement-design constant**, derived
from the quantized grid of 5-fold CV mean accuracy on breast_cancer
(n = 569), **not** from any operator outcome:

- fold size n_f ≈ 569 / 5 ≈ 113.8 (strata-shuffled split sizes 113–114);
- per-fold accuracy lattice step = 1 / n_f ≈ 0.00877;
- mean-of-5 accuracy lattice step = (1/n_f) / 5 ≈ **0.00175**;
- the registered gate admits real gains of ≥ **2 lattice steps** while
  rejecting 1-step quantization coincidence noise:

  margin_alpha = 2 × (1/114) / 5 ≈ 0.0035088 → **0.0035** (frozen).

beta (wine, 178 rows) and gamma (digits-900) are untouched at 0.005 to
preserve cross-protocol continuity with 235, where both carried clean
signal at that margin. The gate semantics are otherwise unchanged: an
attempt is a validated discovery iff BOTH replicate mean-CV accuracies beat
the split-matched cached baseline by ≥ the family's registered margin.

**Fairness:** the recalibrated alpha margin applies uniformly to ALL arms
(prior phase, every policy, held-out evaluation), so no arm gains an
advantage; only the sensitivity with which alpha discoveries are recognized
changes.

## 4. Experimental grid (frozen — identical to the executed 235 bundle)

| Parameter | protocol-235-v1 (executed) | protocol-236-v1 |
|---|---|---|
| trials | 32 | **96** |
| episodes_per_trial | 2 (rotation [alpha, beta]) | 2 (unchanged) |
| budget_credits | 150.0 | 150.0 |
| prior_attempts_per_family | 20 | 20 |
| prior_seed / analysis_seed / seed_base / top_k | 101 / 11 / 7 / 3 | unchanged |
| arms | executed 10-arm set (see below) | **same 10 arms** |
| ablations | () | () |
| workload / held_out_family | hpo / gamma | hpo / gamma |
| operators (7 KNN knobs), flat costs 10.0 | unchanged | unchanged |
| alpha / beta / gamma margins | 0.005 / 0.005 / 0.005 | **0.0035** / 0.005 / 0.005 |

Executed arm set (frozen, mirrors bundle-manifest `arms`, which is the
normative reference for "everything else frozen"):

```
static, knowledge-informed, adaptive, adaptive-cost-aware, random,
adaptive-cost-aware-family, knowledge-informed-family,
knowledge-informed-family-cost-rank, knowledge-informed-family-commit,
knowledge-informed-family-alloc
```

Power rationale: paired series n = 96; at expected efficiency SD ≤ 0.004 the
MDE ≈ 0.002 × sqrt(32/96) ≈ **0.0012** at α = .05 (vs ≈ 0.002 at n = 32).

**Machinery-invariant control (free, pre-registered):** per-family gating
and the seed derivation rule are retained, so **trials 0..31 of 236 must
byte-reproduce protocol-235-v1's beta and gamma outcomes** (alpha differs
via the margin). Agreement validates that raising n did not change the
machinery; disagreement invalidates the comparison.

## 5. Hypotheses (decision rules, NOT forecasts)

Identical to protocol-235 §5, candidate = adaptive-cost-aware (C+):

- **H1 (promotion transfers):** C+ > static AND C+ > knowledge-informed
  (adjusted p < 0.05, CI excluding 0) on ≥ 2 training task families, with
  directional persistence on held-out gamma.
- **H2 (format replication):** B-com ≥ B-fam+ on both training families
  (directional).
- **H3 (representation):** B-fam > B (pooled) on at least one training
  family (adjusted p < 0.05).
- **H4 (floor):** every informed arm > random-arm efficiency (directional).

### Registered interpretation branches

- **H1 met** → the loop claim survives contact with a real search problem at
  sufficient n; promotion is demonstrated; next: insurance-pricing / harder
  search spaces per 235§6.
- **H1 not met, alpha still starved at 0.0035** → alpha headroom, not the
  margin, is the binding constraint on this workload; registered honest
  negative; re-routes to the deferred third-family amendment.
- **H1 not met, beta/gamma now fail too** → the n=32 result was a
  small-sample artifact, not a true transfer; the loop claim is not
  supported on this workload; documented negative.
- **Machinery-invariant control fails** (trials 0..31 beta/gamma mismatch) →
  comparison void; investigate before interpreting any other result.

## 6. Versioning and provenance

- `HPO_WORKLOAD_VERSION` / `HPO_TASK_SUITE_VERSION` bump **1.1.0 → 1.2.0**
  (discovery-gate semantics changed for alpha; gate version → 1.1.0).
- Per-family margins recorded in `environment_metadata().workload_metadata`
  under `family_discovery_margins` and echoed in the bundle's
  `environment.json`; the global `promotion_threshold` stays 0.005
  (beta/gamma margin) for manifest continuity.
- `protocol-236-v1` bundle: freeze_manifest before execution; determinism
  and immutability rules identical to 235 (checksums, no recomputation of
  a committed bundle without `--force`).

## 7. Explicitly deferred (out of scope this round, per resource law)

- A third training family with richer discovery structure and the
  family-keyed `operator_stats` schema change (235§6 separate items) —
  deferred because sis/iris-class residuals are too coarse (lattice step ≈
  0.0067 at n=150) and network-fetched datasets are forbidden by the
  resource law; a synthetic family would defeat the real-workload purpose.
- No change to MASTER_SPEC, MILESTONES, thresholds, or autonomy governance.
- No new dependencies; zero incremental cost; local CPU only.