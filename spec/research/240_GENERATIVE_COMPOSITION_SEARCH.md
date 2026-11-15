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
  arms and all trials)
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
cost, then lexicographically by program string. The champion is fixed after
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
  recorded.
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
  --trials 10 --episodes 2 --prior-attempts 8 --budget 60 \
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
