# AlgoLab — Initial Audit (mission baseline)

- **Audit date:** 2026-10-14
- **Baseline commit (HEAD):** `93e5f11220f8b98bb97a2c63d95be5054cd380e4`
  ("chore(protocol): commit Phase-1 hermetic substrate — foundation only, no
  sealed advance")
- **Branch:** `main` (up to date with `origin/main`)
- **Auditor:** OpenCode (principal research engineer / methodology auditor)
- **Scope:** entire repository, with emphasis on `implementation/algolab/`,
  `spec/research/`, `docs/`, and the committed experiment bundles.

This audit establishes what actually exists and works. Confirmed defects are
separated from hypotheses. Every substantive statement cites a file, a command,
or an artifact.

---

## 1. Repository and working-tree state

### 1.1 Pre-existing working-tree changes (preserved, not introduced here)

`git status --porcelain` at baseline:

```
 M README.md
?? implementation/algolab/experiments/protocol-236-v1/
```

- `README.md` was already modified before this mission (working digest
  `39837df61c506caa6d562ae2da0b18693ca804ac3c146f578edfcbf35e7bc2fd`).
- `implementation/algolab/experiments/protocol-236-v1/` was already untracked.
  It contains exactly three files (no `conditions/`, `statistics.json`,
  `report.md`, or `checksums.json`):

  | file | sha256 |
  |---|---|
  | `manifest.json` | `3951392c7bbbedd5b06521f17cd96a34b2ff3dbcfc01f29f043127664874eac1` |
  | `knowledge-snapshot.json` | `87f4a5ccb65bb1f52652934713ad1de8686e6a16a78f76c79abae1d3a728f2dc` |
  | `knowledge-snapshot-by-family.json` | `c092ef281e4bf3deae6699e1cc1eb7bbc36381a6d290b22e5f43a1eeb976a8fd` |

  Its `manifest.json` records `trials: 96`, `environment_version: "1.1.0"`,
  `discovery_gate_version: "1.0.0"`, `promotion_threshold: 0.005`, and no
  per-family margins. **Interpretation:** an aborted/incomplete run (see §5.2),
  not evidence. It is preserved untouched.

### 1.2 Commands executed to establish the baseline

All run from `implementation/algolab/` with the project venv
(`.venv/bin/python`, Python **3.14.4**):

| Command | Result |
|---|---|
| `make lint` (`ruff check src tests scripts`) | **All checks passed** (ruff 0.16.4) |
| `make type` (`mypy`, strict) | **Success: no issues found in 45 source files** (mypy 2.3.1) |
| `make test` (`pytest -m "not slow"`) | **345 passed, 2 warnings in 98.38s** |
| `pytest --collect-only -m slow` | **0 tests** (see §4.3, D-4) |
| committed-bundle checksum sweep (see §1.3) | **606/606 files verified across 12 bundles** |

The two `make test` warnings: (a) a Pydantic serializer warning from a
`test_cli_execution.py` negative-input case; (b) a NumPy 2.5 deprecation
emitted by `sklearn.datasets.load_digits` (third-party, not fixable here).

### 1.3 Independent checksum verification (performed in this audit)

A script re-hashed every file referenced by every committed
`experiments/*/checksums.json` (12 bundles: `protocol-230-v1`, `-v2`,
`protocol-232-v1`, `protocol-233-p{30,60,120,240}`, `protocol-234-p{30,60,120,240}`,
`protocol-235-v1`) and compared to the recorded digest:

```
verified 606 files across 12 bundles
problems: 0
```

This is a read-only verification, not a re-execution of the experiments. It
confirms **artifact integrity at rest**, not scientific reproducibility.

---

## 2. Architecture and experiment inventory

### 2.1 Executable core (`implementation/algolab/src/algolab`, ~9.9k LoC)

| Layer | Modules | State |
|---|---|---|
| Contracts | `core/{ids,events,models,state}.py`, `validation/schema_validator.py` | Implemented (M0) |
| Control | `control/{config,budget}.py` | Implemented; ledger with monetary override, partial charge, overrun audit |
| Storage | `storage/{db,event_store,repositories,run_repository}.py` | Implemented; schema v3; append-only triggers on `events`, `ledger_entries`, `tasks`, `evidence`, `operator_uses` |
| Execution | `execution/{worker,queue,expansion,aggregation,recovery,artifacts,errors,logging}.py` | Implemented (M1) |
| Workloads | `workloads/{base,quadratic_optimizer}.py` | Implemented |
| Knowledge | `knowledge/{evidence,operators,registry}.py` | Implemented |
| Statistics | `statistics.py` | Implemented; dependency-free bootstrap CI, Welch t, Cohen's d, BH FDR |
| Search (KL line) | `search/{toy,policies,harness,workload_hpo,workload_s2,rules}.py` | Partial (see §2.2, §4) |
| CLI | `cli/main.py` | 18 subcommands; `search-run --workload {toy,hpo}` |

The tests (~5.5k LoC, 345 fast tests) cover IDs, models, state machines,
event-store append-only, budget ledger + partial charge, repositories,
ontology invariants, expansion, queue, worker, recovery, aggregation,
artifacts, determinism, migration, CLI lifecycles, statistics, and the
protocol 230–236 surface.

### 2.2 The knowledge-loop (KL) research line

Protocols are **not** milestones M0–M5. They are the pre-registered KL
experiments in `spec/research/`:

| Protocol | Spec | Harness workload | Committed bundle | Claim status |
|---|---|---|---|---|
| 230 | `230_KNOWLEDGE_LOOP_EVALUATION.md` | toy | `protocol-230-v1` | C misses ≥2-family bar |
| 231 | `231_COST_AWARE_SELECTION.md` | toy | `protocol-230-v2` | C+ meets bar |
| 232 | `232_FAMILY_CONDITIONED_KNOWLEDGE.md` | toy | `protocol-232-v1` | family conditioning dominates |
| 233 | `233_PRIOR_SIZE_DOSE_RESPONSE.md` | toy | `protocol-233-p{30,60,120,240}` | gap is structural |
| 234 | `234_DECISION_RULE_FORMAT.md` | toy | `protocol-234-p{30,60,120,240}` | commitment = ceiling; adaptation = insurance |
| 235 | `235_REAL_WORKLOAD_BRIDGE.md` | hpo (KNN) | `protocol-235-v1` | promotion bar honestly NOT met at n=32 |
| 236 | `236_HIGHER_N_REAL_WORKLOAD_PROMOTION.md` | **spec says hpo** | none sealed | **conflict — see §5** |

The harness (`search/harness.py`) freezes a manifest before any episode,
builds a seeded K0 prior snapshot, runs arms under identical budgets/seeds,
persists every attempt to schema-v3 tables, and writes a checksummed bundle.
This machinery is real and well-tested.

---

## 3. Verified strengths

1. **Contracts and invariants are enforced in code, not prose.** Append-only
   enforcement via SQLite triggers (`storage/db.py:251`), fail-closed state
   transitions, idempotent budget entries, and content-fingerprinted runs are
   implemented and tested.
2. **Deterministic statistics from first principles** (`statistics.py`):
   seeded bootstrap, Welch–Satterthwaite, BH FDR, and a self-implemented
   Student-t survival function — no SciPy dependency. Reproducible by
   construction.
3. **The strategy-layer golden test is real.** `tests/test_protocol_230_golden.py`
   regenerates protocol-230-v1 and asserts byte-identical artifacts, guarding
   the "refactor must not change pre-registered behavior" contract.
4. **Committed bundles are hash-sealed and currently intact** (606/606 verified).
5. **Scientific self-skepticism is present in the artifacts themselves.**
   The 235 report and spec report the promotion bar as unmet rather than
   weakening it; the README scopes findings to their substrate.
6. **CPU-friendly and offline.** Heaviest test ≈ 40 s; whole fast suite ≈ 98 s;
   no network/GPU/credentials required.
7. **Honest commit discipline.** HEAD explicitly states "foundation only, no
   sealed advance" rather than implying a completed experiment.

---

## 4. Confirmed defects

Severity: **S1** critical / **S2** major / **S3** moderate / **S4** minor.
Status: **CONFIRMED** (reproduced from files/commands) or **HYPOTHESIS**.

### D-1 (S2, CONFIRMED) — Documentation references files and experiments that do not exist

Several authoritative docs cite paths that are absent from the repository:

| Document | Cites | Reality |
|---|---|---|
| root `README.md:77,78,84` | `spec/research/235b_*`, `spec/research/236_SECOND_SUBSTRATE_TRANSFER.md` | neither exists; the only 236 spec is `236_HIGHER_N_REAL_WORKLOAD_PROMOTION.md` |
| `docs/STATUS.md:21` | `spec/research/235b_POWERED_REPLICATION.md`, `experiments/protocol-235-v2/` | neither exists |
| `docs/STATUS.md:27` | protocol 236 = "sklearn family shift" | the committed 236 spec is "higher-N real workload (KNN)" |
| `implementation/algolab/README.md:22-24` | "the S2 family-shift substrate (protocol 236)", `236_*` | S2 is a second KNN workload, not a family shift, and 236 is the higher-N spec |
| `src/algolab/search/workload_s2.py:3,164` | `spec/research/236_SECOND_SUBSTRATE_TRANSFER.md` | missing |

A new contributor following these links hits dead ends.

### D-2 (S2, CONFIRMED) — Protocol-236 identity conflict (pre-registration vs. implementation)

The pre-registered `spec/research/236_HIGHER_N_REAL_WORKLOAD_PROMOTION.md` defines
protocol 236 as a higher-N (trials 32→96) real KNN-HPO run with a single
registered lever — an alpha discovery-margin recalibration 0.005→0.0035, with
`HPO_WORKLOAD_VERSION`/`HPO_TASK_SUITE_VERSION` bumped 1.1.0→1.2.0 and
`discovery_gate_version` → 1.1.0 (`spec/.../236...md:34-72,120-130`).

The implementation does **not** implement that design:

- `workload_hpo.py:39-40,63,169` keeps `1.1.0`, margin `0.005`, gate `1.0.0`.
- `scripts/run_protocol_236.py:45` sets `promotion_threshold=hpo.DISCOVERY_MARGIN`
  (0.005) with **no** family margins — so it would seal a `protocol-236-v1`
  bundle that does not match the registered 236.
- `tests/test_protocol_236.py:1-9`, `GREAT_PLAN.md:94-103`, and the docs instead
  describe protocol 236 as a **new S2 substrate** (`workload_s2.py`).
- `workload_s2.py` is itself inconsistent: its docstring claims operators
  "across three estimators" (`:12`) but it defines only KNN knobs (`:52-60`);
  and it cites a spec (`:3`) that does not exist.

**No confirmatory run for either interpretation has been sealed.** The untracked
`protocol-236-v1/` bundle is an aborted run that matches neither design cleanly
(trials=96 but margin=0.005/gate 1.0.0, no family margins). This is a
scientific-governance defect: the protocol number and its registered design
disagree.

**RESOLVED 2026-10-14 (Option 1, owner decision).** Protocol 236 remains the
higher-N real-workload design (committed spec authoritative); the S2 substrate is
re-designated **protocol 237** with its own pre-registration
(`spec/research/237_SECOND_SUBSTRATE_TRANSFER.md`). Code/tests/docs were
relabelled (`workload_s2.py` docstring, `test_protocol_236.py` →
`test_rules_library.py`, root `README.md`, `docs/STATUS.md`, `GREAT_PLAN.md`);
`s2` is now CLI-reachable (`search-run --workload s2`); and the 236 driver now
states it is not yet conformant (only the trials lever implemented). Remaining
work is *not* naming: the registered 236 alpha-margin lever is still
unimplemented, so no `protocol-236-v1` bundle may be sealed. Full record:
`docs/quality/protocol-236-conflict.md`.

### D-3 (S3, CONFIRMED) — Provenance mis-records the workload for non-toy experiments

`search/harness.py` hardcodes the toy workload label in the schema-v3 `tasks`
table for **all** workloads:

- `:435` `_register_task` → `"toy-discovery"`, `"protocol-230 task"`
- `:633` `_register_prior_task` → `"toy-discovery"`, `"protocol-230 prior"`
- `:1544` `_register_held_out_task` → `"toy-discovery"`, `"protocol-230 held-out transfer"`

When `--workload hpo` runs, every task row still claims `toy-discovery`. Since
the mission's core value is traceable provenance, a real-workload run that is
recorded as a toy run is a correctness defect (evidence records reference these
task rows).

### D-4 (S3, CONFIRMED) — The `slow` test lane is defined but empty; CI runs the whole suite

- `Makefile:14-18` and `pyproject.toml` define a `slow` marker and a
  `test-slow` target; `docs/FREE_CPU_RUNBOOK.md:17-18` and
  `implementation/algolab/README.md:30-31` tell users `make test` "excludes
  @slow full-protocol runs".
- **No test is marked `@slow`** (`grep -rn "mark.slow" tests` → none).
  `pytest -m slow` collects 0 tests and exits with code 5 ("no tests ran"), so
  `make test-slow` **fails**, not passes — but the failure is an opaque bare exit
  5, and the lane delivers no actual slow coverage.
- CI (`.github/workflows/ci.yml`) runs `pytest -q` with no marker filter, so it
  does not match the documented fast lane (`pytest -m "not slow"`) and would run
  any future `@slow` test (budgeted at <10 min each) on every push.

### D-5 (S3, CONFIRMED) — The S2 workload is registered but unreachable and untested

- `search/harness.py:169` registers `"s2"` in `_WORKLOADS`.
- But `cli/main.py:160` restricts `--workload` to `("toy", "hpo")`, and
  `scripts/run_protocol_236.py` uses `workload="hpo"`.
- No test imports `workload_s2` or calls `resolve_workload("s2")` (grep across
  `tests/`). The module passes mypy but has **zero functional coverage**, and no
  execution path reaches it.

### D-6 (S4, CONFIRMED) — S2 environment metadata omits the held-out family

`workload_s2.py:185` sets `"families": list(TASK_FAMILIES)` (alpha, beta),
omitting the held-out family, whereas the analogous HPO builder
(`workload_hpo.py:170`) uses `list(ALL_FAMILIES)`. The S2 bundle's
`environment.json` would therefore under-report its own task suite.

### D-7 (S4, CONFIRMED) — Evidence records carry placeholder statistics

`harness.py:466-469` (and `:661-664`) write
`p_value = 0.0 if discovery else 1.0`, `ci_low = min(effect_1, effect_2)`,
`ci_high = max(...)` into the `evidence` table. These are not the results of
any statistical test; they are encodings. `README`/invariant text states
"promotion claims require the statistical analysis stored with them"
(`implementation/algolab/README.md:150-151`), which these fields do not satisfy.
The real analysis lives in the bundle's `statistics.json`, so the risk is
contained — but the evidence schema's `p_value`/`ci_*` fields are misleading if
read literally.

### D-8 (S4, HYPOTHESIS) — Empty-artifact directories in the working tree

`experiments/{protocol-230-beta-analysis, ...}` contain only `REPORT.md`
(no checksums). `experiments/protocol-236-v1` is incomplete (D-2). Whether these
are intended derived-summary dirs or accidental is unconfirmed; no code path
generates them.

### D-9 (S1, CONFIRMED) — CI never executes: the workflow is in the wrong directory

**Found during the post-push review, after this audit's first version.** Adding
the workflow at a subdirectory path means GitHub Actions ignores it entirely.

- The only Actions file was `implementation/algolab/.github/workflows/ci.yml`.
  GitHub only runs workflows from the **repository root** `.github/workflows/`;
  a nested path is never registered.
- Evidence (2026-10-14, authenticated as `NullLabTests`):
  `gh api repos/NullLabTests/AlgoLab/actions/workflows` → `total_count: 0`, and
  `gh run list` → `[]`. Actions is `enabled: true`; there was simply no runnable
  workflow. **CI has never run on this repository.**
- Consequences: the project's central verification loop was never exercised on
  the remote; lint/type/test were only ever run locally. Every prior statement
  that "CI installs / CI checks" (audit E2/E6 evidence, `README`, runbook) was
  unbacked. This also makes D-4 worse than first recorded: the marker-filter
  mismatch was moot because nothing ran at all.

**Fix (this pass):** a corrected root-level `.github/workflows/ci.yml`
(`working-directory: implementation/algolab`, `-m "not slow"` fast lane, plus a
`workflow_dispatch` full job); the dead nested file was removed.

**Second finding, exposed the moment CI first ran (D-9b).** The pytest
collection failed with `ModuleNotFoundError: No module named 'tests'` on 16
files. Cause: tests do `from tests.conftest import ...`, which resolves only if
the package directory (which contains `tests/`) is on `sys.path`. `make test`
uses `python -m pytest`, and `python -m` prepends the current directory to
`sys.path`, so it works locally; the bare `pytest` console script used by CI
does not, and there was no `tests/__init__.py`. **The suite was therefore only
runnable via `python -m pytest` from `implementation/algolab/`.** Fix: add an
empty `tests/__init__.py` so pytest's prepend import mode puts
`implementation/algolab/` on `sys.path` and `tests.conftest` resolves under any
invocation. Verified: `pytest -m "not slow"` → 365 passed via the console
script.

Severity **S1** because it silently defeated the primary automated safeguard.

### D-10 (S3, CONFIRMED) — The "byte-reproducible" golden test is environment-dependent

**Found when CI first ran on Python 3.11 (run `38493302776`), after D-9/D-9b were
fixed.** `tests/test_protocol_230_golden.py::test_deterministic_artifacts_match_committed_bytes`
compares the regenerated protocol-230-v1 bundle against the committed bytes. It
passes on the dev environment (Python 3.14.4, numpy 2.5.2, scikit-learn 1.9.0)
but fails on CI Python 3.11: the assertion reads `b'{"ablat...' == b'{"ablat...'`,
differing only in the last digit of full-precision floats in `statistics.json`
(e.g. `0.020295238095238095` vs `...092`, a ~1e-16 relative difference).

- **Cause:** the derived statistics come from bootstrap/permutation routines
  whose results carry libm/BLAS/Python-build-dependent rounding in the last ULP.
  The committed bundle's `environment.json` (schema version 1.1.0) records no
  interpreter or library versions, so the sealing environment is unrecoverable.
- **Consequence:** the byte-exact guarantee holds only on the machine that
  sealed the bundle. The golden test's docstring and the "byte-reproducible"
  phrasing in `implementation/algolab/README.md` over-claimed.
- **Important boundary:** the raw per-attempt condition streams (exact integers)
  **do** reproduce byte-for-byte in CI, and `report.md` rounds its numbers and is
  also byte-identical. Only the full-precision statistics JSON differs, so the
  *behavioral* reproduction guarantee (same arms, counts, structure, and effects
  to 1e-9) is intact.

**Fix (this pass):** the golden test now compares JSON artifacts **numerically**
(recursive, structure-exact, relative/absolute tolerance 1e-9) and keeps
**byte-exact** comparison for `report.md` and the raw condition streams; the
docstring records the honest contract and the docs were qualified accordingly.

Severity **S3**: no scientific result is invalidated, but the reproducibility
claim was stronger than reality and, until CI ran, was never exercised.

---

## 5. Missing evidence and unresolved items

### 5.1 Missing evidence

- **No sealed protocol-236 bundle** (higher-N real workload or S2). The status
  row in `docs/STATUS.md:27` is "*(pending — this sprint)*".
- **No `protocol-235-v2` bundle**, despite `docs/STATUS.md:21` citing it.
- **No higher-power replication of 235.** Finding 6 rests on n=32; the strict
  ≥2-family promotion bar was not met. This is the largest open scientific gap.
- **No independent re-execution** of any committed bundle was performed in this
  audit (only at-rest checksum verification). Re-execution requires re-running
  the harness; the protocol-230-v1 golden test covers only that one bundle.

### 5.2 The aborted 236 bundle

The untracked `protocol-236-v1/manifest.json` (created 2026-09-19T15:06:51Z) was
written, along with the prior knowledge snapshots, but no `conditions/`,
`statistics.json`, `report.md`, or `checksums.json` exist. HEAD's commit message
names the cause ("shebang 126, stale sqlite WAL lock, tool time cap") and states
the advance was **not** executed. It must not be presented as a result.

### 5.3 Documentation vs. implementation drift (beyond D-1)

- The root README milestone table (working-tree revision) marks M4/M5 "Not
  started" while the KL line is delivered; the accompanying note is accurate but
  the table and `docs/STATUS.md:31-33` are terse and easy to misread.
- `docs/BASELINE_STATE.md` is a snapshot of commit `5b302a5` (M1 era) and is
  **stale** relative to current HEAD; it is useful history but must not be read
  as current.

---

## 6. Highest-leverage improvement opportunities (ranked)

1. **Reconcile the protocol-236 identity (D-2).** Without this, any future 236
   run is scientifically ambiguous and unciteable. Requires a human decision on
   naming; the audit records the conflict and defers the choice.
2. **Fix the provenance label (D-3).** Cheap, high integrity value; makes
   real-workload evidence self-describing.
3. **Make the `slow` lane and CI honest (D-4).** Removes a dead gate and aligns
   CI with the documented CPU budget.
4. **Correct documentation drift (D-1).** Cheap; directly improves the
   contributor path and the "docs match implementation" criterion.
5. **Add artifact-integrity regression coverage.** Turn this audit's ad-hoc
   checksum sweep into a permanent test over committed bundles.
6. **Bring the S2 workload under test or remove it from the registered set
   (D-5, D-6).** Either wire it (CLI + a smoke test) or stop registering it.

---

## 7. Prioritized issue list

| ID | Sev | Impact | Effort | Affects prereg? | Verification method |
|---|---|---|---|---|---|
| D-9 | S1 | CI never ran (workflow in subdir); central safeguard defeated | S | no | root workflow registered; `gh run list` shows a run |
| D-10 | S3 | "Byte-reproducible" claim is environment-dependent (over-claimed) | S | no | CI green across matrix; numeric-tolerance golden test |
| D-2 | S2 | Any 236 claim is ambiguous; governance risk | decision + doc (M) | **yes** | **RESOLVED** 2026-10-14 (Option 1); 236 = higher-N, S2 → 237 |
| D-1 | S2 | Contributor dead-ends; false references | S | no | link check vs `git ls-files` |
| D-3 | S3 | Mis-recorded provenance for real runs | S | no | new regression test on `tasks.workload` |
| D-5/D-6 | S3/S4 | Unreachable, uncov. registered workload | M | no | smoke test / CLI wiring |
| D-4 | S3 | Dead `slow` lane; CI not per docs | S | no | `make test-slow` no longer silent; CI filter |
| D-7 | S4 | Misleading evidence fields | M | no | schema/doc clarification |
| D-8 | S4 | Ambiguous summary dirs | S | no | doc note |

Effort: S ≤ 1 h, M ≤ half a day, L ≥ a day (CPU-only). "Affects prereg?" marks
items that could change a scientific question and therefore require human
approval before implementation.

---

## 8. Baseline commands (for reproduction)

```bash
cd implementation/algolab
make lint          # ruff: All checks passed
make type          # mypy strict: Success (45 files)
make test          # pytest -m "not slow": 345 passed in ~98 s
```
