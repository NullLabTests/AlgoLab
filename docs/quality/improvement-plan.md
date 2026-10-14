# AlgoLab — Improvement Plan

Companion to `acceptance-criteria.md` and `initial-audit.md`. Each work item
lists the problem, intended change, affected files, acceptance test, regression
risk, dependencies, rollback, whether it touches a pre-registered design, and
resource cost. Items are ordered by dependency and leverage.

Effort: S ≤ 1 h, M ≤ half a day, L ≥ a day. All work is CPU-only, offline.

---

## WP-1 — Reconcile the protocol-236 identity (governance) — **RESOLVED 2026-10-14**

- **Problem / evidence:** `initial-audit.md` §4 D-2. The pre-registered
  `spec/research/236_HIGHER_N_REAL_WORKLOAD_PROMOTION.md` (higher-N KNN, alpha
  margin 0.0035, versions 1.2.0) conflicts with the implemented/tested S2
  substrate and the docs, which call 236 "S2". No sealed run exists for either.
- **First pass (intended change):** **Record, do not resolve.** Write
  `docs/quality/protocol-236-conflict.md` capturing the exact divergence, the
  provenance of the aborted bundle, and the decision required. Do **not** edit
  the pre-registered spec or numerically weaken any goal.
- **Resolution (owner, Option 1):** 236 = the higher-N real workload (committed
  spec authoritative); the S2 substrate becomes **protocol 237** with its own
  pre-registration (`spec/research/237_SECOND_SUBSTRATE_TRANSFER.md`). Applied
  under a separate follow-up to code/tests/docs (no goal weakened).
- **Files:** `docs/quality/protocol-236-conflict.md`;
  `spec/research/237_SECOND_SUBSTRATE_TRANSFER.md`; `README.md`,
  `docs/STATUS.md`, `GREAT_PLAN.md`, `src/algolab/search/workload_s2.py`,
  `tests/test_rules_library.py`.
- **Acceptance test:** a reviewer can state, from the record, which design owns
  236 (higher-N) and which owns 237 (S2).
- **Regression risk:** none (docs + a neutral-name code key).
- **Depends on:** none.
- **Rollback:** revert the relabelling commit.
- **Affects preregistered design:** **yes — was a human decision (now made).**
- **Cost:** S.

## WP-2 — Fix provenance mislabel for non-toy workloads (code)

- **Problem / evidence:** `initial-audit.md` §4 D-3; `harness.py:435,633,1544`.
- **Intended change:** derive the `tasks.workload` value (and a short
  description) from `self.wl.key`/`display_name` instead of the hardcoded
  `"toy-discovery"`.
- **Files:** `src/algolab/search/harness.py`.
- **Acceptance test:** new test runs a tiny `hpo` comparison and asserts every
  row in `tasks` has `workload` = the hpo key (and none say `toy-*`); the
  protocol-230-v1 golden byte test still passes.
- **Regression risk:** low; task rows are not part of artifact bundles, so
  golden bytes are unaffected (verified by running the golden test).
- **Depends on:** none.
- **Rollback:** revert the three literals.
- **Affects preregistered design:** no.
- **Cost:** S.

## WP-3 — Make artifact integrity a permanent regression test

- **Problem / evidence:** `initial-audit.md` §4 B5; the audit's 606/606 sweep
  was ad-hoc.
- **Intended change:** add `tests/test_artifact_integrity.py` that, for every
  committed `experiments/*/checksums.json`, re-hashes each referenced file and
  asserts equality, and asserts a known set of sealed bundles is present
  (guarding against accidental deletion).
- **Files:** new test file.
- **Acceptance test:** the test passes at HEAD; it fails if any artifact byte or
  digest is altered (demonstrated locally).
- **Regression risk:** none (read-only).
- **Depends on:** none.
- **Rollback:** delete the test.
- **Affects preregistered design:** no.
- **Cost:** S.

## WP-4 — Fix documentation drift (docs)

- **Problem / evidence:** `initial-audit.md` §4 D-1.
- **Intended change:** correct every dead reference (root `README.md`,
  `docs/STATUS.md`, `docs/FREE_CPU_RUNBOOK.md`, `implementation/algolab/README.md`,
  `workload_s2.py` docstring) to name real files; mark 235b/236 status honestly;
  state that no 235b spec or `protocol-235-v2` bundle exists.
- **Files:** the above docs.
- **Acceptance test:** a link/`git ls-files` check finds no referenced
  `spec/research/*` or `experiments/*` path that is absent.
- **Regression risk:** none (docs); must not revert the pre-existing uncommitted
  README change (build on it).
- **Depends on:** WP-1 (for 236 wording).
- **Rollback:** revert doc edits.
- **Affects preregistered design:** no.
- **Cost:** S.

## WP-5 — Make the `slow` lane and CI honest

- **Problem / evidence:** `initial-audit.md` §4 D-4.
- **Intended change:** align docs, Makefile and CI. Preferred minimal option:
  keep the marker but make `test-slow` report when it collects nothing and
  clarify in docs that the current suite has no `@slow` tests; change CI to run
  `pytest -q -m "not slow"` (matching the documented PR lane) and add an
  optional, manually-triggered full job. Reassess after seeing whether any test
  should be marked slow.
- **Files:** `.github/workflows/ci.yml`, `Makefile`, `docs/FREE_CPU_RUNBOOK.md`,
  `implementation/algolab/README.md`.
- **Acceptance test:** `make test` and CI both run the same fast set; docs no
  longer claim tests are excluded that are not; `make test-slow` cannot silently
  succeed on an empty selection.
- **Regression risk:** low; do not reduce coverage (marking tests slow would).
- **Depends on:** none.
- **Rollback:** revert workflow/Makefile/doc edits.
- **Affects preregistered design:** no.
- **Cost:** S.

## WP-6 — Resolve the S2 workload: wire it or de-register it

- **Problem / evidence:** `initial-audit.md` §4 D-5/D-6.
- **Intended change:** given WP-1's naming conflict, the minimal safe action is
  to (a) fix the S2 `environment_metadata` families to include the held-out
  family (consistency with hpo), (b) correct its docstring to match the
  implemented KNN knobs, and (c) add a fast smoke test that exercises
  `resolve_workload("s2")` and a tiny S2 run so the registered workload is not
  dead/untested. Exposing `s2` on the CLI is deferred to WP-1's naming decision.
- **Files:** `src/algolab/search/workload_s2.py`, `src/algolab/search/harness.py`
  (metadata contract only), new tests.
- **Acceptance test:** S2 metadata lists all families incl. held-out; smoke test
  produces a manifest and statistics for a 2-trial run in < ~20 s.
- **Regression risk:** low; no sealed S2 bundle exists to break.
- **Depends on:** WP-1 for any CLI/name changes.
- **Follow-up (done):** once WP-1 resolved (S2 = protocol 237), `s2` was exposed
  on the CLI (`search-run --workload s2`) with a reachability test
  (`tests/test_search.py`), and a pre-registration
  (`spec/research/237_SECOND_SUBSTRATE_TRANSFER.md`) was written.
- **Rollback:** revert module docstring/metadata/test.
- **Affects preregistered design:** no (S2 has no sealed preregistration; the
  conflict is WP-1).
- **Cost:** M.

## WP-7 — Contributor workflow: minimal protocol checklist

- **Problem / evidence:** `initial-audit.md` §4 E8; acceptance criterion E8 = 1.
- **Intended change:** add a concise "adding a protocol" section/template
  describing the required artifacts (question, preregistration, baseline/treat-
  ments, config schema, smoke test, run command, results schema, stats +
  acceptance criteria, integrity checks, report separating observation /
  interpretation / limitation). Prefer a doc + existing schemas over a new
  plugin framework.
- **Files:** `implementation/algolab/CONTRIBUTING.md` (or `docs/` equivalent).
- **Acceptance test:** following the checklist reproduces the shape of an
  existing protocol (cross-check against `235_REAL_WORKLOAD_BRIDGE.md`).
- **Regression risk:** none.
- **Depends on:** WP-4.
- **Rollback:** delete doc.
- **Affects preregistered design:** no.
- **Cost:** M.

## Deferred / requires human approval

- **Sealing a protocol-236 run** (either interpretation) and any higher-power
  235 replication: blocked on WP-1 and on CPU budget/authorization.
- **Changing the pre-registered 236 lever** (e.g. margin, n): a scientific
  decision; not autonomous.
- **Any push/tag/release:** not performed without explicit authorization.

---

## Verification loop (per change)

Small relevant test after each item; at checkpoints run the full ladder:
`ruff` → `mypy` → `pytest -m "not slow"` → golden byte test → artifact-integrity
test → CLI smoke. Record counts and any pre-existing failures separately.
