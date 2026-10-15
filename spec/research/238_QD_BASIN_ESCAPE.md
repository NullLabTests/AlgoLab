# Protocol 238 — Quality-Diversity Archive + Basin Escape

**Status:** Pre-registered and frozen before any confirmatory run. Hypotheses,
arms, parameters, margins, promotion bar, contradiction policy, and outcome
classes below are immutable after this document is committed. The archive and
basin-escape logic must not be tuned after seeing outcomes.

**Reference points:** protocols 230–237 bundles; AlgoLab sealed findings in
`spec/research/23{0..7}_*.md` and `docs/STATUS.md`.

**Design sources (cited):**
- Farahbakhsh et al., *AgentDiscover: Autonomous Discovery with Minimal
  Search Scaffolding*, arXiv:2610.05334 — idea/candidate database where
  classical selection rules (MAP-Elites, MCTS) reduce to queries.
- Suwandi et al., *Kernel Autoresearch for Open-Ended Model Discovery*,
  arXiv:2610.10394 — quality-diversity archive + novelty screening
  keeping candidates valid and behaviorally distinct.
- Ziakas et al., *Fork-and-Flush: Escaping Idea Basins in Autoresearch
  Agents*, arXiv:2610.07447 — periodic forking with fresh context to
  escape localized idea basins.
- AlgoLab protocols 230–235 (cost-awareness, family-conditioning,
  decision-rule isolation, real-workload bridge, promotion at n=96/236).

## 1. Question

Does a quality-diversity archive plus periodic basin-escape forking increase
validated discoveries per fit-credit under distribution shift, relative to the
best existing arms (cost-aware adaptive and frozen commitment)?

## 2. Substrate and workload

- Workload: `hpo` (KNN micro-HPO, sklearn built-ins) unless second-substrate
  transfer is required; families alpha (breast_cancer), beta (wine), gamma
  (digits-900, held out).
- Families, operators (7 KNN knobs), costs (flat 10.0 credits), discovery
  gate (0.005 absolute 5-fold CV accuracy on both replicates), split-matched
  cached baselines, seed derivation rule: frozen from protocol 235/236.
- No new task families, operators, or cost changes in this protocol.

## 3. Frozen parameters

| Parameter | Value |
|---|---|
| workload | hpo |
| trials | 96 (full); smoke fallback 2 with UNRESOLVED-POWER if CPU budget < 10 min |
| episodes_per_trial | 2 (rotation [alpha, beta]) |
| budget_credits | 150.0 |
| prior_attempts_per_family | 20 |
| prior_seed / analysis_seed / seed_base / top_k | 101 / 11 / 7 / 3 |
| ablations | () (pre-registered scope cut for compute) |
| held_out_family | gamma |

## 4. QD archive contract (frozen)

Behavioral descriptors (deterministic):
1. cost tier — ordinal bucket of nominal credit cost;
2. family-affinity signature — performance vector (success-rate vector)
   across families (alpha, beta; held-out never included);
3. simple outcome-statistic embedding — (mean effect, success rate,
   attempt count).

Insertion: MAP-Elites style. A candidate is inserted into the cell keyed by
a discretized descriptor; it replaces the incumbent only if its quality is
strictly greater (ties broken by stable entry id). Archive state is
serializable (`to_dict` / `from_dict`) and written into the sealed bundle
as `qd-archive.json`.

Novelty: distance of a descriptor to the nearest archived descriptor
(max 1.0 for an empty archive).

Selection rule as query: arms query the archive (by quality, novelty, or
predicate) instead of re-implementing selection logic in ad-hoc code.

No post-hoc tuning of archive bins, quality definitions, novelty metrics, or
fork policy after outcomes are observed.

## 5. Arms

Carried over unchanged (byte-identical selection rules):
static, knowledge-informed, adaptive, adaptive-cost-aware, random,
knowledge-informed-cost-rank, knowledge-informed-family,
knowledge-informed-family-cost-rank, adaptive-cost-aware-family,
knowledge-informed-family-commit, knowledge-informed-family-alloc.

New arms:
- **qd-adaptive-cost-aware** (`QDAdaptiveCostAwarePolicy`): cost-aware /
  Thompson selection biased toward (or restricted to) the current QD
  archive; the archive of elite parents is queryable and deterministic.
- **basin-escape** (`BasinEscapePolicy`): every N=25 steps, or on
  measurable stagnation (no discovery in the last 5 attempts), fork a
  high-quality, high-novelty parent from the QD archive into a fresh
  adaptive trajectory with a reserved exploration budget of 3 steps
  (fork-and-flush). Parent IDs are logged.

Both arms log priors, posteriors, scores, reasons, and parent IDs in their
selection records.

## 6. Comparisons and correction

Primary pairs (BH-corrected within each family block), carried-over matrix
plus:
- qd-adaptive-cost-aware vs adaptive-cost-aware
- basin-escape vs adaptive-cost-aware
- basin-escape vs qd-adaptive-cost-aware

Ablications: none (scope cut).

## 7. Hypotheses / decision rules (not forecasts)

Candidate = improvement over best existing arms.

- **H1 (QD helps):** qd-adaptive-cost-aware > adaptive-cost-aware on both
  training families (adjusted p < 0.05, CI excluding 0).
- **H2 (basin escape helps under shift):** basin-escape shows higher held-out
  (gamma) efficiency than adaptive-cost-aware (directional).
- **H3 (no harm):** both new arms >= random on every family (directional).
- **H4 (inspectability):** archive snapshots and parent IDs are present in
  the sealed bundle.

Interpretation branches:
- H1 & H2 pass → archive + basin escape is a validated lever under shift.
- H1 fails, H2 passes → basin escape alone carries the gain.
- H2 fails → basin escape does not escape this substrate's basins; report
  honest negative.
- Either new arm below random → reject, report negative.

## 8. Promotion bar (frozen, mirrors 231/235)

The candidate arm (primary: basin-escape if H2 passes else qd-adaptive-
cost-aware) must beat static AND knowledge-informed with adjusted p < 0.05
and CI excluding 0 on >= 2 training families, and the gap must persist on
held-out gamma. Evaluated via `PolicyComparison.evaluate_claim` with the new
candidate label.

## 9. Outcome classes (frozen)

- **A — confirmed:** promotion bar met as registered.
- **B — partial:** directional improvement / held-out gain without meeting
  the full multi-family bar.
- **C — falsified:** no significant improvement, or new arm below random, or
  machinery failure.

## 10. Contradiction policy

If a result contradicts a prior protocol finding, the protocol-238 result is
scoped to this substrate and n; earlier protocol verdicts are not overruled
in place. Contradictions are recorded in the completion report and ADR.

## 11. Guarantees

- Golden protocol-230-v1 reproduction stays byte-identical (regression test).
- No changes to discovery gates, margins (except as 236), statistical
  protocols, provenance, or governance.
- No paid compute, no GPU, no free-form LLM code rewriting.
- Autonomy remains L1.
- Archive and basin logic not tuned after seeing outcomes.
- Append-only evidence, hash-sealed artifacts, budget ledger respected.

## 12. Amendment log

- (none yet; post-execution records appended below)- **2026-10-15 (POST-EXECUTION record; no design change):** experiment
  `protocol-238-v1` executed as a smoke-size confirmatory run under this
  frozen pre-registration (hpo KNN micro-HPO; trials=2, episodes/trial=2,
  prior=2/family, budget=60; all thirteen main arms plus default ablations;
  no ablations tuned, no post-hoc policy changes). Evidence:
  `implementation/algolab/experiments/protocol-238-v1/` (checksummed bundle,
  68 files). Outcome: **C — falsified / UNRESOLVED-POWER** for every claim;
  n=2 is below the registered full n=96 and the pre-declared smoke size,
  so no multi-family statistical bar was met and no new claim is promoted.
  Directional smoke observations only: qd-adaptive-cost-aware training
  efficiency 0.025000 < adaptive-cost-aware 0.029167; basin-escape training
  0.025000 < adaptive-cost-aware 0.029167; held-out gamma basin-escape
  0.029167 > adaptive-cost-aware 0.012500. No prior verdicts altered.
