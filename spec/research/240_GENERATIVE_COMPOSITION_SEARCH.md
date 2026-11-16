# Protocol 240 — Generative Composition Search on Real Tabular Pipelines

**Status:** Pre-registered. Frozen before any confirmatory run.
**Date frozen:** 2026-11-15
**Line:** KL research line (successor to protocols 235 / 237 / 239).
**Parent mission:** "Protocol 230 Reproducibility Challenge" — see
`docs/quality/protocol-240-mission.md` for the audit half of that mission.

## 1. Question

Can AlgoLab's search policies **generate and evaluate candidate algorithms**
that are genuinely better than a split-matched, compute-matched baseline — and
does any policy outperform uniform random program search at equal budget?

Two distinct claims are at stake and are scored separately:

- **C1 (discovery).** Some arm finds at least one *validated improvement*
  (2-replicate gate, ≥ 0.005 absolute accuracy) on real data, and that
  improvement is not an artifact of the search procedure.
- **C2 (policy).** Adaptive / history-using search beats uniform random search
  on `validated_discoveries / credits_consumed` across ≥ 2 training families.

C2 is the protocol-230 hypothesis re-tested on a **real** substrate with a
**generative** search space. C1 is the weaker, more basic claim that the
platform can produce a real algorithmic improvement at all.

## 2. Why a new substrate (and not protocol 239's)

Protocol 239's `transform` substrate selects one of 14 hand-enumerated atomic
transforms per attempt. That is *selection from a fixed catalog*, not
*generation of candidate algorithms*, so it cannot support the claim "the
system generates candidates". Protocol 240 replaces selection with a
**compositional program grammar**: an attempt is a program (a sequence of 1–3
typed transformers) that is constructed by the policy, serialized, parsed,
and executed as a real scikit-learn pipeline.

The final estimator is fixed and identical for every candidate and for the
baseline: `StandardScaler -> LogisticRegression(max_iter=1000)`. Only the
feature-transform program varies. This keeps the comparison attributable to
the generated program.

## 3. Substrate

- **Name:** `compose` (new workload module
  `src/algolab/search/workload_compose.py`).
- **Datasets (sklearn built-ins, CPU, offline):**
  - `alpha` = `load_breast_cancer` (569×30, binary);
  - `beta` = `load_wine` (178×13, 3-class);
  - `gamma` = `load_digits` subsampled to 900 rows with
    `RandomState(0)` (held out; never used for search or priors).
- **Baseline (B0):** `StandardScaler -> LogisticRegression` with no
  transform — the split-matched baseline for every attempt. Effect of a
  program = `CV accuracy(program) - CV accuracy(no transform)` on the **same
  CV split seed**, so the comparison is paired at the fold level.
- **Metric:** 5-fold stratified CV accuracy, mean over folds; each attempt is
  evaluated twice with two independent seeds (replicates A and B).
- **Discovery gate (pre-registered, unchanged in spirit from 239):** an
  attempt is a validated discovery iff **both** replicates beat the paired
  baseline by ≥ **0.005 absolute** accuracy.
- **Cost:** `credits = 4 × program_length + Σ operator_data_cost`, where
  operator data costs are fixed per transform (see §5). Costs are charged per
  attempt and are identical for all arms.

### 3.1 Ambition caveat (declared now)

A candidates-space of feature transforms in front of logistic regression on
three small datasets is a *small* algorithm space. Results are scoped to this
space. This protocol does **not** claim that AlgoLab can invent a novel
learning algorithm; it claims/denies that it can generate, evaluate, select,
and transfer pipeline programs against a matched baseline.

## 4. Search space (frozen grammar)

- **Atoms (9).** `log1p`, `sqrt`, `clip-1_99`, `robust-scale`,
  `standard-scale`, `quantile-bin-3`, `interaction-top2`, `pca-10`,
  `poly2-top5`.
  The two composite entries of protocol 239 (`interaction+robust`,
  `poly2+log1p`) are *removed* from the atom set, because in protocol 240 they
  are reachable by composition; keeping them would double-count.
- **Program length:** 1–3 atoms, no atom repeated twice in one program.
- **Program identity:** atoms joined with `+`, in application order, e.g.
  `log1p+robust-scale`. A length-1 program is exactly a protocol-239
  operator, which makes 239 and 240 directly comparable at the atom level.
- **Total space size:** 9 + 9·8 + 9·8·7 = 9 + 72 + 504 = **585 programs**
  (ordered, without repetition). This is small enough to enumerate, and that
  is deliberate: it makes contamination checks and champion verification
  complete rather than probabilistic.

## 5. Arms (5 + 0 ablations-as-arms)

All arms share budget, task rotation, seeds, gate, and space. They differ only
in how they choose the next program.

| Arm | Generates programs? | Reads own outcomes? | Mechanism |
|---|---|---|---|
| `random-program` | yes (uniform over grammar) | no | uniform random program; the standard strong baseline for discrete search |
| `greedy-history` | yes | yes | maintain per-family best-scoring program; next program = mutation (extend/swap/drop) of it, with an ε-explore branch |
| `evolutionary-archive` | yes | yes | population of 6, tournament selection, mutation + crossover, QD archive keyed by (length, cost tier) |
| `static-atoms` | no (length-1 only) | no | round-robin over the 9 atoms — protocol-239-style control, isolates the value of composition |
| `greedy-permuted` | yes | yes, but **feedback permuted** | same machinery as `greedy-history` with outcome labels shuffled between programs (ablation of the feedback channel) |

`random-program` is the primary control for C2; `static-atoms` is the control
for the value of composition; `greedy-permuted` is the causal ablation of the
feedback loop.

## 6. Design parameters (frozen)

- Trials (independent paired seeds): **10**
- Episodes per trial: **2** (family rotation `alpha, beta`, identical for all
  arms and all trials) — **amended to 4 before execution, see §13**
- Budget per episode: **60 credits**
- Prior phase (K0): **8 attempts per training family**, uniform atom policy,
  `prior_seed = 101`. Prior evidence informs only `greedy-history`'s initial
  ranking and `evolutionary-archive`'s seed population; it contains **no
  gamma** evidence.
- `analysis_seed = 11`, `seed_base = 7`, `top_k = 3`.
- Promotion threshold passed to the harness = `0.005` (the discovery margin).
- Held-out evaluation: (a) harness held-out arm loop on `gamma` with the same
  trials/budget, and (b) **champion transfer**: each arm's champion program is
  re-evaluated on `gamma` twice with fresh seeds that no search attempt used.

### 6.1 Champion rule (frozen before running)

For each arm, the champion is the program with the highest `mean_effect`
observed during **training** with ≥ 1 attempt; ties broken by lower credit
cost, then by the lexicographically **largest** program string (stated
explicitly so the rule is reproducible to the character; amended in §13 A5). The champion is fixed after
training and is not re-selected on the basis of its gamma result. Programs
evaluated on only one family are eligible; this is declared to avoid a
post-hoc rule that would favour arms that happen to sample both.

## 7. Pre-registered hypotheses and decision rules

- **H1 (C2, primary).** `greedy-history` beats `random-program` on
  `validated_discoveries/credit` on **both** training families, with
  Benjamini–Hochberg adjusted p < 0.05 and the paired bootstrap CI excluding
  zero, using the harness's family × seed pairing (n=10).
- **H2 (C2, secondary).** `evolutionary-archive` beats `random-program` under
  the same rule.
- **H3 (C1, discovery).** At least one arm produces a validated discovery
  during training (both replicates ≥ +0.005), and its champion transfers to
  `gamma` with a **positive** 2-replicate mean effect.
- **H4 (composition value).** `random-program` beats `static-atoms` on at
  least one training family with adjusted p < 0.05 (composition is not
  worthless), *or* the arm-level efficiency difference is directionally
  positive on both families.
- **H5 (feedback causality, exploratory).** `greedy-history` >
  `greedy-permuted` in the same direction as H1; unadjusted p reported,
  labelled exploratory.

### Outcome taxonomy (pre-registered)

| Class | Meaning |
|---|---|
| **A — supported** | H1 met (both families, adj. p<0.05, CI>0) and H3 met |
| **B — partially supported** | H3 met, H1 not met (a real improvement was found, but history-using search did not beat random) |
| **C — falsified / underpowered** | H1 not met and H3 not met; must state whether the cause is power (no arm produced a discovery) or mechanism (discoveries exist but random matches them) |
| **D — invalid** | implementation, leakage, or reproducibility check fails; no scientific conclusion is drawn |

Class C is a legitimate, publishable outcome for this design and must not be
reported as "support for the knowledge loop".

## 8. Confounders and controls (declared)

- **Compute matching.** Credits are charged identically per program for all
  arms; arms that choose cheap programs get more attempts, which is part of
  the registered cost model rather than a confound.
- **Split pairing.** Each attempt uses the same CV split seed for baseline and
  candidate, so fold-level variance cancels in the effect estimate.
- **Leakage.** All transformers are fitted inside `Pipeline` on the training
  fold only (`cross_val_score` + `clone` per fold). `gamma` is not touched by
  the prior, by search, or by any policy-side statistic; champion selection
  never reads gamma.
- **Contamination.** Program space is fully enumerable (585); the report lists
  every program evaluated, every champion, and every rejection, so a reviewer
  can confirm no test-set tuning occurred.
- **Determinism.** Seeds are integers derived from the manifest; no wall-clock
  quantity affects selection or evaluation. Timing is recorded but never used.
- **Multiple comparisons.** The harness applies BH within each pre-registered
  comparison family; per-family analyses are reported separately.

## 9. Budget and failure criteria

- **Registered compute budget:** ≤ 12 minutes wall clock, single CPU machine,
  `n_jobs=-1`, no GPU, no network. A pilot measurement of per-attempt cost is
  recorded in the experiment README **before** the confirmatory run and may
  only be used to check that the frozen design fits the budget — it may not
  be used to change the design. If it does not fit, the run is scaled down by
  reducing trials only, and that deviation and its power consequence are
  recorded. *(Amended to ≤ 60 minutes before execution; see §13 A3. The
  deviation is a measured budget correction, not a reduction in trials.)*
- **Failure criteria (any one ⇒ class D, no claim):** non-deterministic
  repeated attempt under identical seeds; leakage detection; a bundle
  checksum mismatch; a missing artifact; a champion that was never evaluated
  during training; a held-out evaluation that touched `gamma` during search.

## 10. Analysis

- Harness analysis (unchanged statistics path): paired bootstrap CI (2000
  iterations, seeded), Welch fallback, Cohen's d, BH across pre-registered
  pairs, per-family pairing on (family, seed).
- Champion transfer: 2 fresh-seed evaluations per champion on `gamma`,
  reported as raw pairs; no significance test is claimed on a single program.
- Reproduction: the bundle is re-executed by `scripts/verify_bundle.py` in a
  clean process and compared byte-for-byte (raw streams, report) or
  numerically at 1e-9 (derived JSON), same contract as protocol 230 (D-10).

## 11. Reproduction

```bash
cd implementation/algolab
.venv/bin/python -m algolab.cli.main search-run protocol-240-v1 \
  --workload compose --dir experiments/protocol-240-v1 \
  --trials 10 --episodes 4 --prior-attempts 8 --budget 45 \
  --arms random-program,greedy-history,evolutionary-archive,static-atoms,greedy-permuted \
  --force
.venv/bin/python scripts/verify_bundle.py experiments/protocol-240-v1
```

## 12. Negative-result interpretation (bound in advance)

If class C is returned, the following must be stated explicitly: the finding
is about **search-policy efficiency on a 585-program feature-transform space
over three small tabular datasets**, not about knowledge loops in general;
uniform random search is a strong baseline for small discrete spaces and
beating it is not implied by any prior protocol result.

## 13. Pre-execution amendments (recorded before the confirmatory run)

These changes were made **after** the pre-registration commit
(`0ca3b24 docs(protocol-240): pre-register generative composition search`)
and **before** any confirmatory protocol-240 run. No confirmatory data existed
when they were written; the pilot numbers below were measured on the smoke
configuration only. Each amendment states its reason and its effect on power,
as required by §9.

**A1 — episodes per trial: 2 → 4; budget per episode: 60 → 45 credits.**

- *Reason.* With the rotation `alpha, beta` repeated twice per trial, a
  4-episode trial gives each family two non-adjacent opportunities per trial
  with a symmetric rotation, which removes the systematic "first-family
  advantage" that a 2-episode rotation creates for any policy with warm
  state. It also lengthens the adaptation horizon for the history-using arms,
  which is the mechanism H1/H2 test.
- *Effect.* Total per-trial credit budget is 4 × 45 = 180 versus 2 × 60 = 120,
  so the run is *larger*, not smaller. No power is lost; the design fit the
  registered wall-clock budget at these values (see A3).

**A2 — primary metric: distinct validated programs per credit (declared).**

- *Reason.* §3/§10 already derived the metric from the raw streams, but §6's
  parameter block did not name it as primary. On a **deterministic** evaluator,
  the harness metric `validated_discoveries / credits` counts *attempts*, so an
  arm that re-evaluates a lucky program accumulates discoveries without
  discovering anything new. The pre-registered primary metric therefore counts
  each validated program **at most once per (arm, family, trial) cell**, which
  is farming-proof by construction. The harness metric is retained verbatim as
  the secondary metric so the numbers remain comparable with protocol 239.
- *Effect.* Stricter than the secondary metric for every arm; it cannot
  manufacture a discovery that the 2-replicate gate did not produce.

**A3 — pilot cost measurement (smoke configuration, not confirmatory).**

- Measured on `trials=2, episodes=4, budget=45, prior=4`: 50.55 s wall clock
  for the training phase, 200 attempts, 142 real CV evaluations, 58 memoised
  repeats (0.28–0.50 s per evaluation). The frozen confirmatory configuration
  (`trials=10, episodes=4, budget=45, prior=8`) is therefore ~15–30 min of CPU
  wall clock on one machine, inside the registered "≤ 12 minutes" only if the
  memo cache is effective. **Declared deviation:** the §9 budget is amended to
  **≤ 60 minutes wall clock, single CPU, no GPU, no network**, because the
  frozen design is five arms × 10 trials and was measured, not guessed.
  Reducing trials is *not* used, so n = 10 paired trials per family is
  preserved.

**A4 — harness feedback hook generalized (behaviour-preserving).**

- *Change.* The harness previously delivered outcomes only to
  `isinstance(policy, AdaptivePolicy)`. It now delivers an optional `update`
  and an optional `observe` hook by duck typing.
- *Effect.* For every pre-existing arm this is behaviour-identical (they all
  inherit `AdaptivePolicy.update`, and none define `observe`); it is required
  only so the new generative arms can read the realised effect magnitude
  rather than the binary discovery flag. Verified against the committed
  protocol-230-v1 golden bundle.

**A5 — champion tie-break stated exactly (clarification, no behaviour change).**

- *Change.* §6.1 now says ties are broken by lower credit cost, then by the
  lexicographically **largest** program string. That is what the implementation
  already did (it and ``ProgramHistory.best`` share one key function); the
  original text said "lexicographically" without a direction.
- *Effect.* None. It removes a reproducibility ambiguity: two reviewers
  applying the old wording could have produced different champions on an
  exact tie.

## 14. Post-execution errata (documentation only)

Written **after** the confirmatory run
(`implementation/algolab/experiments/protocol-240-v1/`), while the experiment
README was being prepared. Unlike §13 these are not pre-execution changes: they
record places where the frozen text above does **not** match the executed
design. The frozen text is left as written so the discrepancy stays visible;
each erratum names the executed value and its effect on the reported numbers.

**E1 — held-out `gamma` size: 900 registered, 600 executed.**

- §3 above says `load_digits` subsampled to 900 rows with `RandomState(0)`.
  The implementation uses `GAMMA_ROWS = 600`, and
  `environment.json` in the sealed bundle records `gamma_rows: 600`,
  `gamma_subsample_seed: 0`.
- *Effect on results:* none for any training comparison. `gamma` is used only
  for the champion-transfer check and the harness held-out loop; neither feeds
  the primary or secondary metric. The executed sample size is the one recorded
  in the artifact, so the reported transfer numbers are internally consistent —
  but the registered and executed held-out sample sizes differ, and a reviewer
  reproducing "900 rows" would not reproduce this bundle.

**E2 — "promotion threshold passed to the harness = 0.005" is not what
happened.**

- §6 above states the promotion threshold passed to the harness is `0.005`.
  There is no CLI flag for it; `manifest.json` records the harness default
  `promotion_threshold = 0.15`.
- The **effective** discovery gate is
  `workload_compose.DISCOVERY_MARGIN = 0.005`, applied inside
  `workload_compose.run_attempt` (both replicates must beat the split-matched
  identity baseline by ≥ 0.005 absolute). That is the gate every `discovery`
  flag in `conditions/**/raw-results.jsonl` came from.
- *Effect on results:* none. The harness `promotion_threshold` is written into
  an `evidence` column and never read back by `_refresh_operator_stats` (which
  counts `outcome == PROMOTE`, decided by `attempt.discovery`), and it enters
  neither the primary metric (distinct validated programs / credits) nor the
  secondary metric. It is recorded metadata whose value is misleading in
  isolation; the real gate is stated in
  `environment.json -> workload_metadata.discovery_margin_absolute` (= 0.005).

**E3 — `random-program` is length-stratified, not uniform over the 585
programs.**

- §5 describes `random-program` as "uniform random program; the standard strong
  baseline for discrete search", and §4 calls the grammar the search space. The
  implementation (`candidates.random_program`) draws the **length** uniformly
  from {1, 2, 3} and then the atoms uniformly without replacement. That is
  uniform *within* each length class and uniform over lengths — it is **not**
  uniform over the 585 programs, where length-3 programs are 86 % of the space.
- *Measured in the executed run:* 59 length-1, 55 length-2, 28 length-3 attempts
  (42 % / 39 % / 20 %), at 10.7 credits per attempt. A space-uniform sampler
  would draw 1.5 % / 12 % / 86 % and spend 17.08 credits per attempt (exact
  mean `program_cost` over the 585 programs). Cheap programs are over-sampled
  by roughly 28×.
- *Effect on the result:* this favours the random baseline on the registered
  per-credit metric, because cheap programs are the ones that win per credit,
  and length-3 programs produced zero distinct discoveries in four of the five
  arms. The class-C verdict therefore holds **against a strengthened random
  control** — it is not an artefact of a weak baseline — but it is also **not**
  evidence that history-using search fails against a space-uniform sampler. The
  conclusion must be read as scoped to the executed sampler; a space-uniform
  replication is required to settle the difference and is listed as a next step.
- *Not corrected in place.* The **sampler** is unchanged: changing it after the
  confirmatory run would make the executed experiment different from the one
  that was pre-registered. What *was* corrected, in the re-seal described in the
  experiment README §6.1, is the audit trail's **description** of the sampler.
  Each selection record used to report `selection_probability = 1/585` and the
  reason "uniform sample from the 585-program grammar", neither of which
  describes the draw that produced the program. The record now reports the exact
  per-program probability of the length-stratified draw,
  `(1 / MAX_PROGRAM_LENGTH) / |{programs of that length}|`, and names that draw
  in the reason. The correction changes no random draw: every program stream,
  credit total, effect, and statistic is identical, and the re-sealed bundle
  reproduces.
