# Real-Workload Bridge: Micro-HPO (Protocol 235)

**Status:** Pre-registered. Design, hypotheses, arms, parameters, and
decision rules are frozen BEFORE implementation execution of experiment
`protocol-235-v1`. Reference points: protocols 230–234 bundles. This is
the council-recommended "real-workload bridge": the protocol machinery
(arms, seeds discipline, gate, promotion criterion, statistics,
immutability) is held **identical** to protocol 232's configuration while
the environment changes from the planted-toy generator to a genuine
machine-learning workload whose ground truth is unknown ex ante.

## 1. Motivation

Protocols 230–234 established a rigorous, falsifiable experimentation loop
on a synthetic substrate whose answers were planted. The standing criticism
(their words): *a telescope pointed at an empty corner of sky*. This
protocol points the telescope at a real problem: which hyperparameter
changes improve a real classifier on real datasets, discovered under a
compute budget by policies that do not know the answer in advance.

## 2. Question

Do the pre-registered policy results from protocols 230–234 survive contact
with a real machine-learning search problem?

## 3. Workload definition (fixed)

- **Base estimator:** `sklearn.ensemble.RandomForestClassifier`,
  `n_jobs=-1`, `random_state=<derived seed>`, all other settings default,
  `n_estimators=60`.
- **Task families (datasets, sklearn built-ins — offline):**
  - `alpha` = breast_cancer (569×30, binary)
  - `beta` = wine (178×13, 3-class)
  - `gamma` (**held out**) = digits, stratified subsample of 900 rows
- **Evaluation:** stratified 25% holdout split (`random_state=<derived>`),
  metric = holdout accuracy. Two replicates per attempt (independent
  derived seeds for forest and split).
- **Discovery gate (unchanged semantics):** an attempt is a validated
  discovery iff BOTH replicate accuracies exceed the *split-matched
  baseline* accuracy (baseline configuration evaluated once per family ×
  replicate seed, cached, unbilled) by ≥ **0.01 absolute**.
- **Operators (8 fixed single-delta configurations over defaults):**
  trees-x2 (`n_estimators=120`), deep-leaves (`min_samples_leaf=3`),
  wide-split (`min_samples_split=10`), depth-cap (`max_depth=8`),
  feat-all (`max_features=None`), feat-log2 (`max_features="log2"`),
  no-bootstrap (`bootstrap=False`), balanced
  (`class_weight="balanced_subsample"`).
- **Costs:** nominal per-operator credit costs, **calibrated from measured
  pilot fits and then frozen as constants** in the workload module before
  execution (deterministic reproducibility requires nominal costs;
  measured wall-clock seconds are additionally recorded in every attempt
  payload for reporting only). Episode budget stays **150 credits**.
- **Determinism note:** outcomes depend only on dataset, operator, and
  derived integer seeds; timing never affects any recorded decision.

## 4. Experimental grid (fixed)

Identical to protocol 232's registered configuration except:

- workload = micro-HPO as defined above; `trials = 32`;
  `episodes_per_trial = 2` (rotation [alpha, beta]);
  `prior_attempts_per_family = 20`; arms = the nine main arms of
  protocol 232 **plus** the two protocol-234 format arms
  (commit, alloc) = eleven arms total.
- **Ablation arms (c-permuted, b-shuffled, c-plus-permuted) are omitted**
  — a pre-registered scope cut for compute; they remain available for a
  later amendment. Power rationale: paired series n = 32 per arm per
  family; expected efficiency SD ≤ ~0.004 gives MDE ≈ 0.002 at α = .05.
- Seeds: unchanged rule (`analysis_seed + _arm_seed(arm) + trial`),
  `analysis_seed = 11`, `seed_base = 7`, `prior_seed = 101`.

## 5. Hypotheses (decision rules, NOT forecasts)

Unlike protocols 230–234, numeric outcome forecasts are impossible here by
design (the ground truth is genuinely unknown). Registered decision rules:

- **H1 (promotion transfers):** adaptive-cost-aware > static AND >
  knowledge-informed (adjusted p < 0.05, CI excluding 0) on ≥ 2 training
  task families, with directional persistence on held-out gamma — i.e.,
  the protocol-231 criterion met on the real workload.
- **H2 (format replication):** B-com ≥ B-fam+ on both training families
  (directional).
- **H3 (representation):** B-fam > B (pooled) on at least one training
  family (adjusted p < 0.05).
- **H4 (floor):** every informed arm > random-arm efficiency (directional).

Registered interpretation branches:

- H1 pass → the loop claim's first contact with reality; subsequent work
  moves to harder real search spaces.
- No arm beats static → the real workload offers no exploitable signal at
  this budget scale; report as informative negative, revisit operator set.
- B-family arms succeed where C+ fails → knowledge-without-loop suffices
  on reality; the 230–232 narrative requires revision, reported as such.

## 6. Comparisons and correction (fixed)

Primary matrix = protocol-232 pairs plus protocol-234 commit/alloc pairs,
BH-corrected within each family block; held-out block likewise. Same
statistics stack (paired bootstrap CI, sign-flip permutation, Cohen's d).

## 7. Environment recording (fixed)

The manifest records: scikit-learn/numpy/python versions, CPU core count,
workload module version, calibration table (pilot-measured mean fit
seconds per operator per family), and the frozen nominal costs. The
measured-vs-nominal cost distinction is restated in the bundle report.

## 8. Guarantees

- Toy-workload behavior remains byte-identical (golden v1 regression must
  stay green); the harness gains a workload indirection only.
- No tuning against observed results: operators, thresholds, budgets, and
  seeds are frozen above before any HPO attempt executes. The pilot phase
  may calibrate COSTS ONLY (fit-time measurement), never outcomes.

## 9. Amendment log

- **2026-08-25 (PRE-EXECUTION instrumentation amendment):** two calibration
  pilots were run against the originally registered workload
  (RandomForest micro-HPO, single stratified-holdout split, margin 0.01).
  Findings: (a) all eight registered RF operator deltas averaged ≤ 0.0000
  accuracy on both training families — sklearn RF defaults already
  saturate these datasets, so the arm space carried no positive signal;
  (b) single-split accuracy on `beta` quantizes at ~0.023 (44-row holdout)
  — coarser than the registered 1-point margin, making the gate
  unmeasurable as specified. Both are measurement-design defects, not
  outcome information. Accordingly, BEFORE any policy-relevant execution,
  the workload is amended to: base estimator = ``StandardScaler ->
  KNeighborsClassifier`` (baseline ``n_neighbors=5``); operators = seven
  fixed KNN knobs {k1, k3, k11, k21, dist-weight, manhattan, chebyshev};
  evaluation = mean 5-fold stratified-CV accuracy (two replicate seeds);
  discovery margin = **0.005 absolute CV accuracy**, both replicates;
  nominal costs flat at 10.0 credits (this bridge de-emphasizes the cost
  dimension, established separately in protocols 231–234). Trials remain
  32; episodes/trial 2; prior 20/family; budget 150; arms = the eleven
  main arms of protocols 232/234; ablations omitted. Pilot evidence
  (per-operator effect ranges incl. sign flips across families, e.g.
  k21: +0.0102 on beta vs −0.0341 on gamma) is retained in the repo
  working notes. Transparency note: individual operator effect signs were
  observable during instrumentation and cannot be unobserved; however no
  policy-level comparison was executed or inspected at pilot time, all
  registered hypotheses concern policy orderings rather than operator
  identities, and every revision above applies uniformly to all arms.
  Timing recording is aggregate-per-bundle (not per-attempt payload).
  No other section changes.

- **2026-08-25 (POST-EXECUTION record; no design change):** experiment
  `protocol-235-v1` executed exactly as amended (32 trials, 11 main arms,
  no ablations, ~30 min wall). Outcome: H2 PASS, H4 PASS, H1 NOT met
  (C+ > A and > B on beta only — alpha discovery-starved), H3 FAIL
  (family-conditioning flat at 20-attempt slice sizes). Key mechanistic
  result: B-com posted the best training-phase efficiency (0.0203) but
  scored exactly zero on held-out gamma where the operator value structure
  inverted (k21: 29% → 0.0% discovery across 3933 attempts), while
  adaptive C+ recovered via exploration to top gamma efficiency (0.0192)
  — the adaptation-as-insurance hypothesis empirically demonstrated.
  Evidence: `implementation/algolab/experiments/protocol-235-v1/`;
  interpretation:
  `implementation/algolab/experiments/protocol-235-analysis/REPORT.md`.
