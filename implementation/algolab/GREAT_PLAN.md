# GREAT_PLAN.md — AlgoLab "Good → Great" Sprint (Canonical Phases 0–4)

**Status:** Active. This plan is the gate artifact; implementation of Phases
1–4 begins only after this document exists. Governance unchanged; zero
incremental cost; no paid compute, no GPU.

**Authority order honored:** `MASTER_SPEC.md` > `planning/MILESTONES.md` >
`spec/` > this prompt > existing code.

---

## 1. Preflight output (required gate — verified)

```text
$ gh auth status
github.com
  ✓ Logged in to github.com account NullLabTests (keyring)
  - Active account: true
  - Token scopes: 'codespace', 'gist', 'read:org', 'repo'
  ✓ Logged in to github.com account zenithbrew (/home/illy/.config/gh/hosts.yml)
  - Active account: false

$ gh api user --jq .login
NullLabTests                 # MUST print — PASSED
```

Repo: `NullLabTests/AlgoLab` (`git@github.com:NullLabTests/AlgoLab.git`),
branch `main`, HEAD `7425ab9` (protocol-235 bridge). Identity check PASSED;
onboarding does not run as any other user.

## 2. Runtime decision: LOCAL

| Check | Result |
|---|---|
| `python3 --version` | 3.14.4 (≥ 3.11 required) |
| `implementation/algolab/.venv` | present; `algolab 0.3.0`, sklearn, numpy import clean |
| `bash scripts/setup.sh` requirement | not needed — venv + editable install already exist |
| `make lint` (ruff) | All checks passed |
| `make type` (mypy strict) | Success, no issues (43 source files) |
| `make test` (pytest) | 344 passed, 2 warnings (~103 s) |
| `git status` | clean per-commit; in-flight 235b margin work uncommitted at plan time |

**Decision: LOCAL CPU.** Bootstrapping deps cheaply was already satisfied and
tests run, so the Codespace bootstrap clause is not triggered. No Codespace
will be created; nothing new is installed.

## 3. Current-state map

- **M0 delivered** — contracts, event store, budget ledger, schemas, CLI.
- **M1 delivered** — deterministic execution core, recovery, artifacts.
- **Knowledge layer (unlabeled KL line internal, formerly mislabeled M4)** —
  schema v3, statistics, evidence records, operator catalog, skill registry.
- **KL protocols 230–235 delivered** (`algolab.search`, formerly mislabeled
  M5): toy-discovery substrate (230–233 sweeps, 234 format isolation) + the
  KNN micro-HPO real-workload bridge (`protocol-235-v1`, n=32: ordering
  reproduced on beta, strict promotion bar honestly not met).
- **In-flight (uncommitted):** protocol-235b pre-work (per-family discovery
  margins, HPO workload version 1.2.0) — folded into Phase 3 as a
  pre-registered amendment.
- **Not started:** official M2, M3, M4, M5; protocol 236 (S2); 235b run.

## 4. Glossary (resolves the milestone/protocol collision)

- **Official milestones** (`planning/MILESTONES.md`): M0 Contracts · M1
  Deterministic execution · M2 Reference rediscovery · M3 LLM-assisted
  research · M4 Evolutionary search · M5 Controlled meta-improvement.
  These are repo/milestone IDs, NOT the knowledge-loop protocols.
- **KL line (knowledge-loop protocols)** `spec/research/23x_*.md`:
  protocol 230 (A/B/C gate) → 231 (cost-aware C+) → 232 (family-conditioned)
  → 233 (prior-size dose response) → 234 (decision-rule format) → 235
  (real-workload KNN bridge) → **236 (this sprint: second substrate S2)**.
  Protocols stop being called "M4/M5" everywhere in README/docs.
- **Substrates:** `toy` (deterministic planted-truth generator) · `hpo`
  (KNN micro-HPO on sklearn built-ins, protocol 235) · `s2` (new — protocol
  236, sklearn family-shift: LogisticRegression / DecisionTree / GaussianNB
  on tiny offline datasets).

## 5. File plan Phases 0–4

**Phase 0 (docs, no science):** `implementation/algolab/GREAT_PLAN.md` ·
`docs/STATUS.md` · `docs/FREE_CPU_RUNBOOK.md` · glossary fixes in root +
package READMEs.

**Phase 1 (extract reusable core, unit tests only):** new
`src/algolab/search/rules.py` exposing `DecisionRule` (Static,
FrozenTopKCycle, CostAwareThompson = C+, FamilyConditionedFrozen,
CostArgmaxCommitment, ProportionalAllocation), `PriorFactor` (PooledPrior,
FamilyConditionedPrior), `SelectorObjective` (success probability per
credit). Policies in `policies.py` delegate to the library; **rule code must
not import sklearn or the planted-truth toy module**; deterministic seeds;
evidence emission stays on the existing knowledge layer; no new deps;
protocol-230-v1 golden bundle must stay byte-identical.

**Phase 2 (protocol 236 — second substrate S2):**
`spec/research/236_SECOND_SUBSTRATE_TRANSFER.md` (pre-registered BEFORE the
full run: metric = validated discoveries per fit-credit; families alpha=iris,
beta=digits-900, gamma=wine held out; operators across LogisticRegression C /
penalty, DecisionTree max_depth, GaussianNB var_smoothing; credit = fit()
count; n/seeds/priors/margins/promotion bar + contradiction policy frozen).
`src/algolab/search/workload_s2.py`; CLI `search-run --workload s2` plus a
`--protocol 236` preset; hermetic fast tests; sealed
`experiments/protocol-236-v1/`; report promotion **A confirmed / B partial
(claim-by-claim) / C falsified** — no tuning to make C+ win.

**Phase 3 (protocol 235b — powered replication of 235):**
`spec/research/235b_POWERED_REPLICATION.md` pre-registering a measurement-
calibration amendment (alpha margin 0.0035 = 2 × mean-CV lattice step on
breast_cancer; `HPO_WORKLOAD_VERSION` 1.2.0) and identical-metric higher-n
goal. Runs only if the run fits the CPU budget (< 10 min on 2–4 cores at n
reported); otherwise a smaller CI smoke (n=8, ~7 min) + **UNRESOLVED-POWER**
documentation. Machinery-invariant check: trials 0..7 must byte-reproduce
protocol-235-v1 beta/gamma.

**Phase 4 (optional M2 slice or defer):** if budget remains, a minimal M2
slice on the S2 (or KNN) substrate: baseline vs one candidate, five seeds,
statistical report, provenance, replication command; else
`M2_DEFERRED.md`. No fake M2.

## 6. CPU budget (hard)

- `make test` (default CI) target **< 3 minutes**; full-protocol runs are
  pytest-marked `@slow` and excluded from the default run.
- @slow protocols **< 10 minutes each** on 2–4 CPU cores; abort and shrink
  if exceeded. Any run that would exceed the cap without shrinking → do not
  run; document UNRESOLVED-POWER or scale the grid down.

## 7. Risk register

| Risk | Mitigation |
|---|---|
| Peeking / outcome-tuning S2 until C+ wins | Frozen spec before run; A/B/C all valid; report measured |
| Toy-overfit of the extraction refactor | protocol-230-v1 golden byte-compat test guards it |
| Extraction goldens drift (random-draw ordering) | Port logic exactly; run golden before/after each refactor step |
| @slow runs blow past 10 min | Abort & shrink; n=8 KNN smoke or smaller S2 grid |
| Codespace idle cost | None used; if ever bootstrapped, `gh codespace stop` at end |
| Hash fragility from version bumps | Version schema in manifest + environment metadata; append-only bundles |

## 8. Completion evidence (Phase 5)

`GREAT_COMPLETION_REPORT.md` with: LOCAL vs CODESPACE statement, pytest
counts, evidence hashes, promoted/failed/unresolved claims, autonomy remains
**L1**, and explicit "no paid compute and no GPU were used." Claim style:
"on substrate X, at n=Y, rule R beat S on pre-registered metric M."