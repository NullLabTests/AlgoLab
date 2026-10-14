# Second-Substrate Transfer (Protocol 237)

**Status:** Pre-registered design record. This document replaces the
**non-existent** `spec/research/236_SECOND_SUBSTRATE_TRANSFER.md` that was
referenced by `src/algolab/search/workload_s2.py` and `GREAT_PLAN.md`. It
records the S2 substrate as actually implemented and freezes its contract
**before** any `protocol-237-v1` run. No `protocol-237-v1` bundle has been
sealed.

**Designation (resolved 2026-10-14, D-2):** the number **236** belongs to the
higher-N real-workload promotion design
(`spec/research/236_HIGHER_N_REAL_WORKLOAD_PROMOTION.md`). This second-substrate
workload was previously mislabelled "236" in code, tests, and docs; it is now
**protocol 237**. See `docs/quality/protocol-236-conflict.md`.

**Provenance of this document:** the contract below is transcribed from the
implementation (`src/algolab/search/workload_s2.py`), which was written before
this pre-registration existed. Because no run has been sealed, this remains a
pre-run registration; it does **not** describe any executed result.

## 1. Motivation

Finding 6 (`spec/research/235_REAL_WORKLOAD_BRIDGE.md`) established the
knowledge-loop ordering on the KNN micro-HPO (`hpo`) workload, but the strict
≥2-family promotion bar was not met at n = 32. A natural robustness question is
whether the pre-registered policy comparison **transfers to a second, distinct
task surface** while every gate and cost rule is held byte-frozen. Protocol 237
registers that second substrate; it changes the data surface only.

## 2. Question

On a second offline substrate (shifted sklearn task suite, see §4), does the
protocol-234 ten-arm comparison reproduce the pre-registered promotion
ordering under the byte-frozen 235-v1 discovery contract — i.e. is the loop's
behaviour substrate-stable?

## 3. The registered lever: task surface only (fixed)

The **only** change relative to protocol 235 is the dataset roster. Everything
else is byte-frozen from 235-v1: the discovery gate, the margin, the operator
set, the cost model, the seed derivation, and the arms. There is **no**
margin recalibration (all families stay at 0.005).

## 4. Substrate definition (frozen — transcribed from `workload_s2.py`)

- **Families (sklearn built-ins, fully offline; no downloads):**
  - `alpha` = **iris** (`load_iris`), a training family;
  - `beta` = **digits-300**, a 300-row subsample of `load_digits` drawn with
    `numpy.random.RandomState(0).choice(len(X), 300, replace=False)`, a
    training family;
  - `gamma` = **wine** (`load_wine`), the **held-out** family.
- **Operators (7 fixed single-knob configurations of the shared
  `StandardScaler -> KNeighborsClassifier` pipeline; baseline `n_neighbors=5`):**
  `k1` (n_neighbors=1), `k3` (=3), `k11` (=11), `k21` (=21),
  `dist-weight` (weights="distance"), `manhattan` (p=1),
  `chebyshev` (metric="chebyshev"). These are the **same KNN knob set as
  protocol 235**; this substrate deliberately does **not** cross estimator
  families.
- **Metric:** an attempt scores the modified pipeline with 5-fold
  `StratifiedKFold(shuffle=True)` cross-validated accuracy, computed **twice**
  (two episode-scoped replicate seeds), and is a validated discovery iff
  **both** replicate accuracies beat the split-matched cached baseline by at
  least the registered margin (§3). Split-match is achieved by deriving both
  replicates per episode so all arms share splits with the baseline (paired
  design, as in 235 §3; split-seed offset `777001`).
- **Costs:** flat nominal 10.0 credits per operator (cost dimension kept flat,
  mirroring 235); measured wall-clock seconds are accumulated for reporting
  only and never influence any decision.
- **Held-out discipline:** `gamma` (wine) is never used for selection; it is
  evaluated only for the held-out block, exactly as in 230–235.

## 5. Grid (frozen at sealing time; mirrors 235-v1)

The registered default grid mirrors protocol-235-v1's executed parameters
(trials = 32, episodes_per_trial = 2, budget_credits = 150.0,
prior_attempts_per_family = 20, prior_seed / analysis_seed / seed_base /
top_k = 101 / 11 / 7 / 3, arms = the protocol-234 ten-arm set, ablations = ()).
Any deviation (e.g. a higher-n variant) must be registered as a separate
amendment before execution; it may not be chosen post hoc.

## 6. Hypotheses (decision rules, NOT forecasts)

Identical in form to protocol-235 §5 and protocol-236 §5, candidate =
`adaptive-cost-aware` (C+):

- **H1 (transfer):** C+ > static AND C+ > knowledge-informed
  (adjusted p < 0.05, CI excluding 0) on ≥ 2 training families, with
  directional persistence on held-out `gamma`.
- **H2 (format replication):** B-com ≥ B-fam+ on both training families
  (directional).
- **H3 (representation):** B-fam > B (pooled) on at least one training family
  (adjusted p < 0.05).
- **H4 (floor):** every informed arm > random-arm efficiency (directional).

### Registered interpretation branches

- **H1 met** → the loop ordering is substrate-stable, strengthening the
  external-validity of the 235 line; next: a third surface or the protocol-236
  higher-n promotion.
- **H1 not met** → the 235 ordering is substrate-specific; documented negative,
  scoped to this task surface.
- **Contradiction / seed nondeterminism** → the run is void; investigate before
  interpreting.

## 7. Versioning and provenance

- `S2_WORKLOAD_VERSION` / `S2_TASK_SUITE_VERSION` = **1.0.0**;
  `discovery_gate_version` = **1.0.0**; promotion margin = **0.005** (all
  families).
- The harness key and module name remain the neutral `s2`
  (`resolve_workload("s2")`); the workload is exposed on the CLI as
  `search-run --workload s2`.
- `protocol-237-v1` bundle: freeze manifest before execution; determinism and
  immutability identical to 235 (checksums; no recomputation of a committed
  bundle without `--force`).

## 8. Explicitly deferred

- Crossing estimator families (LogisticRegression / DecisionTree / GaussianNB)
  and richer per-family operator sets — the original `GREAT_PLAN.md` Phase-2
  sketch — were **never implemented** and are out of scope for 237. They would
  require a separate pre-registration.
- No change to thresholds, margins, MASTER_SPEC, MILESTONES, or autonomy
  governance.
- No new dependencies; zero incremental cost; local CPU only.
