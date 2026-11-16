# Protocol 240 — Generative Composition Search (confirmatory bundle)

Pre-registration: [`spec/research/240_GENERATIVE_COMPOSITION_SEARCH.md`](../../../../spec/research/240_GENERATIVE_COMPOSITION_SEARCH.md)
(frozen in commit `0ca3b24`, before any confirmatory run).
Mission map: [`docs/quality/protocol-240-mission.md`](../../../../docs/quality/protocol-240-mission.md).

**Status: executed once, sealed, and independently reproduced. Outcome class C.**
Every number below is read from the artifacts in this directory. Nothing is
estimated, and no number was edited by hand.

| verdict | value |
|---|---|
| Pre-registered hypotheses met | **0 of 5** (H1–H5 all false) |
| Outcome class | **C** — no significant policy advantage over random search, no positively transferring champion |
| Sealed at | 2026-11-15; 2382 attempts, 1321 real CV evaluations. Re-sealed after defect D-11 (§6.1) — the science numbers are unchanged, only the recorded wall-clock is |
| Integrity | every SHA-256 in `checksums.json` verifies against the committed bytes |
| Reproduction | `scripts/verify_bundle.py` re-executes this bundle from a clean process and reports **REPRODUCED** (`reproduction-verification.json`) |

---

## 1. Research question

> Can the search policies **generate and evaluate candidate algorithms** that
> are genuinely better than a split-matched, compute-matched baseline — and
> does any policy outperform uniform random program search at equal budget?

Two claims were scored separately in advance:

- **C1 (discovery).** Some arm finds at least one *validated* improvement (both
  replicates beat the matched baseline by ≥ 0.005 absolute accuracy) on real
  data.
- **C2 (policy).** A history-using / adaptive arm beats uniform random program
  search on the primary metric across **both** training families at
  BH-adjusted p < 0.05.

**Result: C1 is met in the narrow, literal sense** (14 (arm, program) validated
pairs spanning 9 unique programs cleared the gate during training, §7), and
**C2 is not met** (§8, §9). A
program that clears the gate is not the same as a program that transfers, and
none of the champions transferred (§10). The class-C verdict is therefore about
*search-policy efficiency and transfer*, not about whether any pipeline program
ever beat the baseline on a training split.

## 2. Why this substrate, and what it is not

Protocol 239's `transform` substrate **selects** one of 14 hand-enumerated
transforms. Selection from a fixed catalog cannot support the sentence "the
system generates candidates". Protocol 240 replaces selection with
**composition**: an attempt is a *program* of 1–3 typed transformers that the
policy constructs, which is then serialized, parsed, and executed as a real
scikit-learn pipeline.

The final estimator is fixed and identical for every candidate **and** for the
baseline: `StandardScaler -> LogisticRegression(max_iter=1000)`. Only the
feature-transform program varies, so any measured effect is attributable to the
generated program.

**Declared scope (§3.1 of the pre-registration).** A grammar of nine feature
transforms in front of logistic regression, on three small tabular datasets, is
a *small* algorithm space. Nothing in this bundle supports "AlgoLab invented a
novel learning algorithm". The results are scoped to a **585-program
feature-transform space over three small tabular datasets**.

## 3. Substrate

| role | dataset | rows × features | classes | used for |
|---|---|---|---|---|
| `alpha` (train) | `load_breast_cancer` | 569 × 30 | 2 | search + inference |
| `beta` (train) | `load_wine` | 178 × 13 | 3 | search + inference |
| `gamma` (held out) | `load_digits`, subsampled | 600 × 64 | 10 | champion transfer + harness held-out loop only |

- **Baseline (B0):** `StandardScaler -> LogisticRegression` with no transform.
- **Effect of a program:** `CV_accuracy(program) - CV_accuracy(B0)` on the
  **same CV split seed**, so every comparison is paired at the fold level.
- **Measurement:** 5-fold stratified CV accuracy, mean over folds; every
  attempt is evaluated **twice** with two independent split seeds.
- **Discovery gate (frozen):** an attempt is a validated discovery iff **both**
  replicates beat the paired baseline by ≥ **0.005** absolute accuracy. This is
  a robustness gate, not a significance test on a single program.
- **Cost model:** `credits = 4 × program_length + Σ operator_data_cost` with
  per-atom data costs 5.0–8.0. Costs are identical for all arms, so longer
  programs buy fewer attempts under an equal credit budget. That coupling is
  the registered model, and it is visible in §7 (`static-atoms` runs 280
  attempts in the same budget that `greedy-history` spends on 178).
- **Determinism:** the evaluator is a pure function of
  `(family, program, seed_base, trial, episode)`. Attempts are memoised, so a
  repeat of an already-evaluated program costs credits but no compute — this is
  why 2382 attempts produced only 1321 real evaluations (1061 cache hits).
  `tests/test_protocol_240.py::TestComposeWorkload` asserts that repeating an
  attempt with a *different* `attempt` index returns the identical measurement.

## 4. Search space (frozen grammar)

**Atoms (9):** `log1p`, `sqrt`, `clip-1_99`, `robust-scale`, `standard-scale`,
`quantile-bin-3`, `interaction-top2`, `pca-10`, `poly2-top5`.
The two composite 239 atoms (`interaction+robust`, `poly2+log1p`) are removed
because in 240 they are reachable by composition; keeping them would
double-count.

**Program:** 1–3 atoms, no atom repeated, atoms joined with `+` in application
order (e.g. `log1p+robust-scale`). A length-1 program is exactly a protocol-239
operator, which is what makes the `static-atoms` control meaningful.

**Size:** 9 + 9·8 + 9·8·7 = **585** programs. Small enough to enumerate, and
that is deliberate: it makes coverage and contamination checks *complete*
rather than probabilistic, and it makes random search a genuinely strong
baseline.

## 5. Arms (five; three of them generate)

| arm | generates? | reads own outcomes? | mechanism |
|---|---|---|---|
| `random-program` | yes | no | **primary control.** Random program — the standard strong baseline for small discrete spaces. Samples the *length* uniformly (1–3) then atoms without replacement, i.e. uniform **within** each length class, not uniform over the 585 programs — see erratum **E3** (§6) and §8.1 |
| `greedy-history` | yes | yes | per-family best program; next = mutation (extend / swap / drop) of it, with an ε-explore branch |
| `evolutionary-archive` | yes | yes | population 6, tournament selection, mutation + crossover, QD archive keyed by (length, cost tier) |
| `static-atoms` | **no** (length-1 only) | no | round-robin over the 9 atoms — the composition-free control |
| `greedy-permuted` | yes | yes, **permuted** | identical machinery to `greedy-history` with outcome→program labels shuffled — the causal ablation of the feedback channel |

`random-program` tests C2. `static-atoms` tests the value of **composition**.
`greedy-permuted` tests the value of **feedback**.

## 6. Design, budget, and the baselines

- Trials (independent paired seeds): **10**; episodes per trial: **4**
  (rotation `alpha, beta, alpha, beta`, identical for every arm and trial).
- Budget: **45 credits per episode** (≈ 1800 credits per arm per trial block).
- Prior phase (K0): **8 attempts per training family**, uniform atom policy,
  `prior_seed = 101`. The prior contains **no `gamma` evidence** — asserted by
  `TestComposeWorkload::test_prior_phase_never_touches_gamma`.
- `analysis_seed = 11`, `seed_base = 7`, `top_k = 3`.
- Compute actually used: **5343 s user / 766 s wall** in the original run, and
  **10 min 26 s wall / 619.37 s of CV evaluation** in the re-seal (§6.1) — single
  CPU machine, no GPU, no network (pre-registered ceiling ≤ 60 min wall; see
  amendment A3).

**Run order (baselines first).** The prior phase — the only place where
baseline behaviour is measured — runs before any arm. Arms then run in the
registered order `random-program, greedy-history, evolutionary-archive,
static-atoms, greedy-permuted`, so the control is measured first. No arm reads
another arm's data: every arm is constructed from the **frozen** prior snapshot
(`self.snapshot`, `self.snapshots_by_family`, both written by `run_prior`
before the loop) plus its own attempt history. The shared SQLite database
accumulates evidence rows for the *audit* tables, but the generative policies
never read `operator_stats`; `tests/test_protocol_240.py` pins this by
re-deriving each arm's program stream from the prior alone.

### Pre-execution amendments (recorded, not retro-fitted)

All five were written **after** the pre-registration commit and **before** any
confirmatory data existed; the pilot numbers they cite come from the 2-trial
smoke configuration only. Full text: spec §13.

| # | change | why it does not weaken the test |
|---|---|---|
| A1 | episodes/trial 2 → 4; budget/episode 60 → 45 | total per-trial budget 120 → 180 credits: the run got **larger**, and the 4-episode rotation removes a systematic first-family advantage |
| A2 | primary metric declared as **distinct validated programs / credits** | on a deterministic evaluator the harness metric counts *attempts*, so re-evaluating a lucky program looks like discovering something. The distinct metric counts a program once per (arm, family, trial) cell and cannot be farmed. The harness metric is kept verbatim as the secondary metric |
| A3 | wall-clock budget 12 → 60 min | measured, not guessed: the smoke run implied ~15–30 min; the real run took 12:46 wall. Trials were **not** reduced, so n = 10 paired trials per family is preserved |
| A4 | harness delivers `update`/`observe` by duck typing instead of `isinstance(AdaptivePolicy)` | behaviour-identical for every pre-existing arm (none define `observe`); verified against the committed protocol-230-v1 golden bundle |
| A5 | champion tie-break stated exactly (lower cost, then lexicographically **largest** program) | removes a reproducibility ambiguity; the implementation already did this |

### Errata (documentation defects found while writing this report)

These are recorded because they are wrong statements, even though no result
depends on them.

- **E1 — `gamma` size.** §3 of the pre-registration says "subsampled to 900
  rows"; the implementation and this bundle use **600 rows**
  (`GAMMA_ROWS = 600`, `RandomState(0)`), and `environment.json` records
  `gamma_rows: 600`. The executed value is the one recorded in the artifact;
  the pre-registration text was never updated at code-writing time. `gamma` is
  used only for champion transfer and the harness held-out loop, so **no
  training comparison is affected** — but the registered and executed
  held-out sample sizes differ and that must be visible.
- **E2 — "promotion threshold passed to the harness = 0.005".** There is no
  such CLI flag. `manifest.json` records the harness default
  `promotion_threshold = 0.15`; the *effective* discovery gate is
  `workload_compose.DISCOVERY_MARGIN = 0.005`, applied inside
  `workload_compose.run_attempt`, which is what produced every
  `discovery` flag in the raw streams. The harness field is recorded evidence
  metadata only: it is written into an `evidence` column and is never read by
  `_refresh_operator_stats` (which counts `outcome == PROMOTE`, decided by
  `attempt.discovery`) and never enters the primary or secondary metric.
- **E3 — `random-program` is length-stratified, not uniform over the 585
  programs.** The arm draws the program *length* uniformly from {1, 2, 3} and
  then the atoms uniformly, so ~42 % of its attempts are length-1 programs
  instead of the 1.5 % a space-uniform draw would give. This favours the
  baseline on a per-credit metric (§8.1). It is recorded rather than corrected:
  changing the sampler after the run would make the executed experiment
  different from the registered one.

### 6.1 Re-seal after defect D-11 (reporting only)

`report.md` is compared **byte-for-byte** when a bundle is reproduced, and the
first seal embedded the measured evaluation time inside it. A clean
re-execution could therefore never match. The first verification returned
`NOT REPRODUCED` on exactly two items — the `report.md` bytes and
`protocol-240-statistics.json.compute.evaluation_seconds` — while the other 33
artifacts already matched.

The fix was to make the *reporting* deterministic rather than to relax the
comparison:

- `report.md` no longer prints any measured duration; the number lives in
  `protocol-240-statistics.json` (`compute.evaluation_seconds`) and
  `environment.json` only;
- `evaluation_seconds` was registered as a **volatile** field in
  `scripts/verify_bundle.py` (alongside `created_at` and
  `measured_operator_seconds`), so it is excluded from the comparison **and
  listed in the verdict** — recorded-but-never-read, not silently ignored;
- every run now starts with a cold memo cache, so the reported
  `evaluations` / `cache_hits` split is a property of that run rather than of
  whatever the process evaluated earlier;
- `tests/test_protocol_240.py::test_report_is_byte_stable_across_runs` pins
  both properties.

The bundle was then **deleted and re-created** from the exact command in §14,
with a fresh SQLite database. Nothing in the design, the seeds, the arms, the
gate, or the analysis changed; only the reporting did. Every science number is
identical to the first seal (2382 attempts, 1321 real evaluations, 1061 cache
hits, the same validated programs, the same H1–H5 verdicts, class C), which is
itself evidence that the edits between the two runs were behaviour-neutral.
The new wall clock is what §6 reports as the re-seal figure.

A second, unrelated **provenance** defect was corrected in that same re-seal, and
it changes no random draw: `conditions/random-program/operator-selections.jsonl`
recorded `selection_probability = 1/585` and the reason "uniform sample from the
585-program grammar", which does not describe the length-stratified draw that
actually produced the program (erratum E3). The record now reports the exact
per-program probability of that draw — `(1/3) / |{programs of that length}|` —
and names it; the greedy arm's explore branch, which uses the same sampler, is
corrected the same way, and the evolutionary arm now records the probability of
the branch it actually took. Every program, cost, effect, credit total and
statistic is byte-identical to the previous seal; only the descriptive fields of
the selection records changed. `tests/test_protocol_240.py::
test_random_arm_reports_its_actual_sampler` pins it.

This README's own SHA-256 is recorded in `checksums.json` after the re-seal, so
the narrative is byte-pinned as well: editing it now would break
`tests/test_artifact_integrity.py`.

## 7. Results — what the search actually generated

Attempts and programs, training phase (from `protocol-240-statistics.json`
`program_summary` and the raw streams):

| arm | attempts | credits | distinct programs evaluated | discovered programs | mean length |
|---|---:|---:|---:|---:|---:|
| `random-program` | 142 | 1520.0 | 76 | 3 | 2.224 |
| `greedy-history` | 178 | 1586.0 | 54 | 3 | 2.093 |
| `evolutionary-archive` | 160 | 1548.5 | 56 | 3 | 1.964 |
| `static-atoms` | 280 | 1695.0 | 9 | 2 | 1.000 |
| `greedy-permuted` | 173 | 1589.5 | 56 | 3 | 2.036 |

**Invalid attempts: 0 in every arm** (no program failed to build or evaluate).

Distinct validated programs found during training:

| arm | validated programs |
|---|---|
| `random-program` | `clip-1_99+log1p`, `log1p+sqrt`, `log1p+sqrt+poly2-top5` |
| `greedy-history` | `log1p`, `sqrt`, `sqrt+interaction-top2` |
| `evolutionary-archive` | `log1p+sqrt`, `sqrt`, `sqrt+standard-scale` |
| `static-atoms` | `log1p`, `sqrt` |
| `greedy-permuted` | `log1p+robust-scale`, `sqrt`, `sqrt+log1p` |

`sqrt` is found by four of the five arms; it is a strong, cheap, single-atom
transform on these datasets. The generative arms spend their extra budget on
longer programs and do not add much beyond it.

**Coverage.** 131 distinct programs were evaluated during training, i.e.
**22.4 %** of the 585-program space; after the held-out loop, 205 distinct
programs (**35.0 %**) have been evaluated somewhere in the bundle. A 74-program
slice of the space was evaluated *only* on `gamma`. Coverage is a description
of this run, not a claim of saturation.

## 8. Results — the primary metric

Primary metric: **distinct validated programs / credits consumed**, where a
program counts **at most once per (arm, family, trial) cell**. 20 cells per arm
(10 trials × 2 families).

| arm | mean distinct/credit | cells |
|---|---:|---:|
| `random-program` | 0.002041 | 20 |
| `greedy-history` | 0.001849 | 20 |
| `evolutionary-archive` | 0.002043 | 20 |
| `static-atoms` | **0.003593** | 20 |
| `greedy-permuted` | 0.001734 | 20 |

Per-family means (a zero means the arm produced no validated discovery in that
family at all):

| arm | `alpha` | `beta` |
|---|---:|---:|
| `random-program` | 0.001212 | 0.002870 |
| `greedy-history` | 0.000000 | 0.003697 |
| `evolutionary-archive` | 0.000000 | 0.004086 |
| `static-atoms` | 0.000000 | 0.007186 |
| `greedy-permuted` | 0.000000 | 0.003468 |

**`alpha` is nearly degenerate:** only `random-program` produced a single
validated discovery there (one program, in one cell). Every paired comparison
in `alpha` therefore has a delta of 0 or −0.001212 and p = 1.0. This is a real
property of the substrate (breast-cancer is easy, and the identity baseline is
already near the ceiling), not a bug — but it means `alpha` contributes almost
no discrimination, and the `beta` comparisons carry the analysis.

### Paired comparisons, BH-adjusted, per family

`alpha`:

| base → candidate | delta | 95 % CI | p | adj. p | d |
|---|---:|---|---:|---:|---:|
| random → greedy-history | −0.001212 | [−0.003636, 0.000000] | 1.000 | 1.000 | −0.447 |
| random → evolutionary-archive | −0.001212 | [−0.003636, 0.000000] | 1.000 | 1.000 | −0.447 |
| random → static-atoms | −0.001212 | [−0.003636, 0.000000] | 1.000 | 1.000 | −0.447 |
| greedy-history → greedy-permuted | 0.000000 | [0.000000, 0.000000] | 1.000 | 1.000 | 0.000 |

`beta`:

| base → candidate | delta | 95 % CI | p | adj. p | d |
|---|---:|---|---:|---:|---:|
| random → greedy-history | +0.000828 | [−0.004687, +0.007486] | 1.000 | 1.000 | 0.112 |
| random → evolutionary-archive | +0.001217 | [−0.003381, +0.005557] | 0.883 | 1.000 | 0.192 |
| random → static-atoms | +0.004316 | [−0.000839, +0.011502] | 0.502 | 1.000 | 0.518 |
| greedy-history → greedy-permuted | −0.000229 | [−0.007643, +0.009255] | 1.000 | 1.000 | −0.023 |

Nothing survives BH correction. Every interval contains zero. The only
non-trivial direction is `random → static-atoms` on `beta` (+0.0043,
d = 0.52 — a medium effect that 10 paired trials cannot resolve), and it points
**against** composition: the arm that only ever tries single atoms does best on
the primary metric, because a length-1 program costs 5–8 credits instead of
12.5–18 and its per-credit rate is therefore higher. That is the registered
cost model working as specified, and it is also the honest answer to "does
composition pay for itself here?" — on this space it does not.

### Secondary (harness) metric, kept for comparability with protocol 239

`validated_discoveries / credits_consumed`, counting **attempts**:

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---:|---:|---:|---:|
| `random-program` | 3 | 1520.0 | 0.001974 | 142 |
| `greedy-history` | 3 | 1586.0 | 0.001892 | 178 |
| `evolutionary-archive` | 4 | 1548.5 | 0.002583 | 160 |
| `static-atoms` | 6 | 1695.0 | 0.003540 | 280 |
| `greedy-permuted` | 3 | 1589.5 | 0.001887 | 173 |

Two further arms appear in the bundle because the harness always runs the
protocol-230 legacy comparison pairs: `b-shuffled` (0.003525, 285 attempts) and
`c-permuted` (0.004793, 292 attempts). They are **not pre-registered for
protocol 240** and are **not used for any claim here**. They are reported
because omitting arms that happen to look good would be selective. Their
apparent advantage is on the attempt-counting metric, which is exactly the
metric A2 was written to distrust.

### 8.1 Post-hoc decomposition by program length (not pre-registered)

This table is derived from the sealed raw streams (nothing new was evaluated).
It exists because it changes how the class-C verdict should be read.

| arm | length | attempts | credits | distinct discoveries | distinct/credit |
|---|---:|---:|---:|---:|---:|
| `random-program` | 1 | 59 | 351.5 | 0 | 0.00000 |
| `random-program` | 2 | 55 | 672.5 | 2 | 0.00297 |
| `random-program` | 3 | 28 | 496.0 | 1 | 0.00202 |
| `greedy-history` | 1 | 106 | 642.5 | 2 | 0.00311 |
| `greedy-history` | 2 | 58 | 695.0 | 1 | 0.00144 |
| `greedy-history` | 3 | 14 | 248.5 | 0 | 0.00000 |
| `evolutionary-archive` | 1 | 60 | 356.5 | 1 | 0.00281 |
| `evolutionary-archive` | 2 | 93 | 1074.5 | 2 | 0.00186 |
| `evolutionary-archive` | 3 | 7 | 117.5 | 0 | 0.00000 |
| `static-atoms` | 1 | 280 | 1695.0 | 2 | 0.00118 |
| `greedy-permuted` | 1 | 96 | 591.0 | 1 | 0.00169 |
| `greedy-permuted` | 2 | 65 | 780.5 | 2 | 0.00256 |
| `greedy-permuted` | 3 | 12 | 218.0 | 0 | 0.00000 |

Two facts follow, and both are recorded as erratum **E3** in the
pre-registration:

1. `random-program` draws the **program length** uniformly (1, 2, 3) and then
   the atoms uniformly, so its attempts are ~42 % length-1, ~39 % length-2,
   ~20 % length-3. A draw uniform over the **585 programs** would be 1.5 % /
   12 % / 86 %. The registered baseline is therefore length-stratified, not
   space-uniform, and it spends **10.7 credits per attempt** where a
   space-uniform sampler would spend **17.08** (the exact mean cost over the
   585 programs). Cheap programs — the ones that win the per-credit metric —
   are over-sampled by roughly 28×.
2. Length-3 programs produced **zero** distinct discoveries in four of the five
   arms (one, for `random-program`), and a space-uniform sampler would draw
   them 86 % of the time.

**Consequence for the verdict.** Class C is a statement about *this* registered
baseline. It does not establish that history-using search cannot beat a
space-uniform random sampler. Since the mis-specified sampler favours the
baseline, the honest reading is: the null is *not* explained by an artificially
weak random control, but part of the gap between "no advantage" and "advantage"
could be sampler design. A space-uniform replication is a concrete next step
(§13, item (i)), not something this bundle can settle.

## 9. Pre-registered hypotheses

| # | hypothesis | result |
|---|---|---|
| **H1** | `greedy-history` > `random-program` on the primary metric, both families, adj. p < 0.05 | **NOT MET** — `alpha` false, `beta` false |
| **H2** | `evolutionary-archive` > `random-program`, both families, adj. p < 0.05 | **NOT MET** — `alpha` false, `beta` false |
| **H3** | a validated training discovery **and** a champion that transfers with a positive mean on both held-out replicates | **NOT MET** — arms with a transferring champion: *none* |
| **H4** | `random-program` vs `static-atoms` resolves the value of composition (significant with a direction, or clearly null) | **NOT MET** — not significant in either family; directional only on `beta` (false on `alpha`) |
| **H5** | `greedy-history` > `greedy-permuted` (feedback ablation), exploratory | **NOT MET** — `alpha` false, `beta` false |

**Outcome class C**, as bound in advance: *neither a significant policy
advantage over random search nor a positively transferring champion was
established.*

## 10. Champion transfer (the decisive check)

Each arm's champion = its highest training `mean_effect` program, ties broken
by lower cost then lexicographically largest name. Champions are re-evaluated on
`gamma` **twice with fresh seeds that no search attempt used**
(`CHAMPION_TRIAL_BASE > 100_000`):

| arm | champion | training mean effect | held-out mean effect | both replicates positive? |
|---|---|---:|---:|---|
| `random-program` | `log1p+sqrt+poly2-top5` | +0.011190 | **−0.016667** | no (−0.0175, −0.015834) |
| `greedy-history` | `sqrt` | +0.008413 | **−0.002083** | no (+0.000834, −0.005) |
| `evolutionary-archive` | `sqrt` | +0.011350 | **−0.002083** | no (+0.000834, −0.005) |
| `static-atoms` | `sqrt` | +0.011350 | **−0.002083** | no (+0.000834, −0.005) |
| `greedy-permuted` | `sqrt` | +0.011350 | **−0.002083** | no (+0.000834, −0.005) |

Four arms converge on the same champion (`sqrt`) and it is worth **−0.0021** on
digits. The random arm's length-3 champion is worse still (−0.0167). **Nothing
transferred.**

The H3 rule is "a **positive** 2-replicate mean effect". The recorded verdict
uses the strict reading (both replicate means > 0) and is reported alongside the
pooled mean; the pooled means are also negative, so H3 is false under both the
strict and the weak reading. There is no reading of the table that makes H3
true.

Honest nuance, stated so the table is not over-read: the harness *also* runs a
full held-out search loop on `gamma`, and that loop does find 103
gate-passing attempts (18 distinct programs, mostly `poly2-top5` /
`interaction-top2` variants). Those programs were found **by searching on
`gamma`**, so they are a replication of the search, not evidence of transfer,
and they are excluded from H3 by construction. They do say something useful:
the discovery gate is satisfiable on `gamma` — it is the *transfer of a chosen
program*, not the gate itself, that fails.

## 11. Rejected candidates

"Rejected" here means **evaluated and not validated** (`discovery: false` in
`conditions/<arm>/raw-results.jsonl`), not "considered and thrown away". The
raw streams are the complete record:

- training: 1510 attempts across the seven arms that ran in training, of which
  **33** carried `discovery: true` (19 in the five registered arms — 3 random,
  3 greedy-history, 4 evolutionary, 6 static-atoms, 3 permuted); every other
  attempt is a recorded rejection with its `effect_1`, `effect_2`,
  `mean_effect`, `cost`.
- held-out: 856 attempts, 103 with `discovery: true`.
- 0 invalid attempts anywhere.

(The bundle's `compute.attempts = 2382` is 1510 training + 856 held-out + 16
prior attempts.)

Selection rationale for the reported champions is the deterministic rule in
§10; because the champion is a function of the training stream only, the
held-out family cannot influence which program was chosen.

## 12. Failure analysis — why class C, and what would have changed it

1. **Two arms are not enough resolution.** With n = 10 paired trials and a
   binary-ish per-cell outcome (most cells are 0.0), the smallest detectable
   effect is large. `static-atoms` on `beta` shows d = 0.52 and still p = 0.50.
2. **`alpha` is nearly saturated.** The identity baseline already scores high on
   breast-cancer; only 1 of 200 training cells produced a discovery there.
   Half the registered family-level test therefore had almost no signal.
3. **Uniform random search is genuinely strong at 585 programs.** In a space
   this small, the history-using arms spend their advantage on *cost* — they
   pick longer programs — which lowers their per-credit rate. This is the
   pre-registered cost model, and it is the single biggest driver of the null.
   Note the direction: the registered random arm is *length-stratified* (E3),
   which over-samples cheap programs and therefore makes the control **stronger**
   on a per-credit metric. The null is not explained by a weak baseline; it is
   partly explained by the metric rewarding cheap programs, which is the
   registered model.
4. **Composition did not transfer.** The winning training programs are
   length 1–2 `sqrt`/`log1p` variants; the one length-3 program that won on
   `breast_cancer`/`wine` was strongly negative on digits. A 600-row 10-class
   dataset rewards different transforms (`poly2-top5`, `interaction-top2`), so a
   champion selected on the training families need not generalise — which is
   exactly why H3 was pre-registered as a separate, harder claim.

What would have produced a different class: a real per-credit advantage for a
history-using arm on **both** training families after BH correction, *or* any
champion whose two held-out replicates were both positive. Neither occurred.

## 13. Limitations

- **Scope.** 585-program feature-transform grammar, fixed logistic-regression
  head, three small tabular datasets. This is not evidence about knowledge
  loops in general, about larger algorithm spaces, or about neural architecture
  search.
- **Deterministic evaluator.** "Discovery" is a two-replicate robustness gate
  against a matched baseline; it is not a significance test, and a program that
  clears it need not be a better *algorithm*.
- **n = 10 paired trials per family.** Effects below the pairing noise are
  invisible. The medium-size `static-atoms` effect on `beta` (d = 0.52) is a
  concrete example of a plausible effect this design cannot resolve.
- **Cost/quality coupling.** Longer programs cost more credits per attempt by
  construction. Any arm that generates longer programs is penalised on the
  per-credit metric. That is registered and intended, but it is a design
  choice, not a law.
- **Champion transfer is one program, two replicates.** A directional check,
  not a powered test. A single unlucky split can decide it.
- **`alpha` family near-ceiling.** Half the family-level inference had almost no
  headroom.
- **Errata E1/E2/E3** (§6) are documentation defects in the pre-registration
  text or mismatches between it and the executed design, not silent changes.
  E3 is the one with a substantive consequence: the random control is
  length-stratified, so the class-C verdict is scoped to that sampler.
- **The executed code is not byte-frozen at the moment of the seal.** Two edits
  landed after the original run (a typing-only change and a `reset()` override
  on the permuted arm that is behaviour-identical for a fresh policy). The
  bundle was therefore re-sealed with the current code (§6.1) and then
  re-executed from a clean process (§14); the science numbers did not move,
  which is the evidence that those edits were behaviour-neutral.

## 14. Reproduction

The bundle is sealed: `checksums.json` covers every deterministic artifact.
`scripts/verify_bundle.py` rebuilds the configuration **from the manifest**,
re-executes the experiment in a separate process with a fresh temporary SQLite
database and a fresh artifact directory, and compares:

- raw attempt streams and `report.md` — **byte-for-byte**;
- derived JSON — **numerically at 1e-9**;
- `manifest.json` / `plan.json` / derived JSON — field by field and value by
  value, with `created_at`, `measured_operator_seconds` and
  `evaluation_seconds` excluded (wall clock, recorded but never read by any
  decision) and every exclusion **listed in the verdict**
  (`excluded_volatile_fields`). No other field is skipped.

```bash
cd implementation/algolab
.venv/bin/python scripts/verify_bundle.py experiments/protocol-240-v1
# -> verdict: REPRODUCED, written to experiments/protocol-240-v1/reproduction-verification.json
```

To re-create the bundle from scratch (≈ 13 min wall on one CPU machine,
no GPU, no network):

```bash
cd implementation/algolab
.venv/bin/python -m algolab.cli.main search-run protocol-240-v1 \
  --workload compose --dir experiments/protocol-240-v1 \
  --trials 10 --episodes 4 --prior-attempts 8 --budget 45 \
  --arms random-program,greedy-history,evolutionary-archive,static-atoms,greedy-permuted \
  --force
.venv/bin/python scripts/verify_bundle.py experiments/protocol-240-v1
```

Tests that pin this experiment:

```bash
.venv/bin/python -m pytest tests/test_protocol_240.py tests/test_verify_bundle.py -q
```

They cover: the grammar is exactly 585 programs and rejects out-of-grammar
strings; costs and mutation/crossover stay in-grammar; the evaluator is
deterministic and `gamma`-free during the prior; each arm's stream is
seed-deterministic and `reset()` restores it; the analysis units (distinct
metric, champion rule, H3's "discovering arm" requirement) behave as specified;
a smoke run seals a checksum-verifiable bundle; and the committed bundle
re-executes in a clean process.

## 15. Artifact index

| file | content |
|---|---|
| `manifest.json` / `plan.json` | frozen experiment definition (arms, seeds, trials, budget) |
| `protocol.json` | gate definition, comparison matrix, statistical methods |
| `environment.json` | datasets, shapes, estimator, atom costs, versions, grammar size |
| `knowledge-snapshot.json` / `knowledge-snapshot-by-family.json` | the K0 prior, per family (`alpha`, `beta` only) |
| `statistics.json` | harness statistics (secondary metric, legacy arms, held-out loop, promotion bookkeeping) |
| `protocol-240-statistics.json` | **primary metric**, per-family comparisons, program summary, champion transfer, H1–H5 |
| `report.md` | machine-generated report (byte-compared on reproduction) |
| `conditions/<arm>/raw-results.jsonl` | every attempt, with both replicate effects and the discovery flag |
| `conditions/<arm>/operator-selections.jsonl` | every policy choice with its audited reason |
| `conditions/<arm>/held-out-*.jsonl` | the `gamma` replication loop and champion transfer |
| `checksums.json` | SHA-256 of every deterministic artifact |
| `reproducibility.json` | harness self-consistency verdict |
| `reproduction-verification.json` | independent re-execution verdict (`scripts/verify_bundle.py`) |

---

## Claim classification

**(A) Implemented and tested.** A closed 585-program compositional grammar, a
real scikit-learn evaluator with a paired split-matched baseline and a
two-replicate discovery gate, five search arms (three generative), a
pre-registered distinct-efficiency metric with champion transfer on a held-out
dataset, sealed-bundle writing, and a generic independent reproduction verifier
with its own test suite.

**(B) Demonstrated.** The bundle is self-consistent, checksum-verified, and
independently reproducible from a clean process. The five arms ran the frozen
design to completion with zero invalid attempts. The pre-registered analysis
returns class C, and the champion-transfer check fails for every arm. The
`alpha` family is nearly degenerate, so the informative comparisons are on
`beta`, where nothing survives BH correction and the only medium-size effect
(`static-atoms`, d = 0.52) points against composition.

**(C) Unproven.** That any of these policies can generate a *novel* algorithm;
that the null generalises beyond a 585-program feature-transform space over
three small tabular datasets; that history-using search cannot beat random
search in a larger or differently-costed space; that no champion could transfer
with a redesigned gate or a larger held-out sample.

**(D) Next steps.** (i) Re-run the same five arms against a **space-uniform**
random control (erratum E3), so the "random search is strong here" claim is
tested against the sampler the pre-registration describes rather than the
length-stratified one that ran. Widen the space so random search is no longer
near optimal — longer programs, other estimators, real operator chains — and
re-run under the same registered metric. (ii) Replace the
binary-ish discovery gate with a continuous paired effect so n = 10 gains
resolution instead of collapsing to zeros. (iii) Replace the near-saturated
`alpha` family with a task that has headroom. (iv) Test champion transfer with
more replicates and more than one program per arm before treating a negative
transfer as a negative result.
