# Execution Report — Quality Hardening Pass

- **Date:** 2026-10-14
- **Baseline commit:** `93e5f11220f8b98bb97a2c63d95be5054cd380e4`
- **Working tree:** `/home/illy/AlgoLaB`
- **Constraint honored:** CPU-only, offline, no GPU/paid APIs, no push/tag, no
  commit. Pre-existing uncommitted work preserved (see §4).

## 1. What was done

In mission order: (1) audited the repository and its scientific record; (2)
froze intent, acceptance criteria and an improvement plan; (3) implemented
bounded fixes with tests; (4) re-verified; (5) scored against the frozen rubric.

Deliverables produced:

| Artifact | Path |
|---|---|
| Intent | `intent.md` |
| Baseline audit (D-1..D-8, evidence) | `docs/audits/initial-audit.md` |
| Acceptance criteria + rubric | `docs/quality/acceptance-criteria.md` |
| Improvement plan | `docs/quality/improvement-plan.md` |
| Protocol-236 conflict record | `docs/quality/protocol-236-conflict.md` |
| Final scorecard (+ JSON) | `docs/quality/final-scorecard.md`, `docs/quality/scorecard.json` |
| Protocol contributor guide | `implementation/algolab/CONTRIBUTING.md` |
| New tests | `implementation/algolab/tests/test_artifact_integrity.py`, `tests/test_provenance_and_s2.py` |

## 2. Changes by work package

| WP | Change | Files |
|---|---|---|
| WP-1 | Recorded the 236 identity conflict; **deferred the decision** | `docs/quality/protocol-236-conflict.md`; notes in `docs/STATUS.md`, `GREAT_PLAN.md` |
| WP-2 | `tasks.workload` derived from the real workload, not `"toy-discovery"` | `src/algolab/search/harness.py` (3 sites) |
| WP-3 | Permanent at-rest integrity test over all committed bundles | `tests/test_artifact_integrity.py` |
| WP-4 | Removed dead references; corrected 235b/236 status | root `README.md`, `docs/STATUS.md`, `docs/FREE_CPU_RUNBOOK.md`, `implementation/algolab/README.md`, `src/algolab/search/workload_s2.py`, `src/algolab/search/rules.py` |
| WP-5 | CI runs the documented fast lane; full lane wired | `.github/workflows/ci.yml`, `Makefile` |
| WP-6 | S2 metadata lists held-out family; docstring matches code; smoke test | `src/algolab/search/workload_s2.py`, `tests/test_provenance_and_s2.py` |
| WP-7 | Protocol contributor checklist | `implementation/algolab/CONTRIBUTING.md` |

Also corrected three self-inconsistencies found in this session's own
artifacts: the audit's D-4 claim (that `make test-slow` "passes"), and two
arithmetic claims in `acceptance-criteria.md` (56 criteria, not 50; 4 at ≤2,
not 10).

## 3. Verification (evidence)

```text
$ make lint     -> All checks passed!
$ make type     -> Success: no issues found in 45 source files
$ make test     -> 365 passed, 3 warnings in 111.05s
```

- Baseline was 345 tests; +20 new tests, all green. Golden byte-reproduction
  (`test_protocol_230_golden.py`) still passes, so WP-2 did not alter any
  artifact bytes.
- `pytest -m slow` collects 0 tests and exits 5 (a hard failure) — documented
  as such now.
- All `spec/research/*` and `experiments/*` paths referenced by the edited docs
  were checked against `git ls-files` and exist.

## 4. Preserved pre-existing work (not reverted, not claimed)

- `M README.md` — the baseline's uncommitted edit; the drift fixes build on it.
- `?? implementation/algolab/experiments/protocol-236-v1/` — untracked aborted
  bundle (manifest + snapshots only). **Not** treated as evidence; labeled as
  aborted in `docs/STATUS.md`.

## 5. Scientific integrity statement

- No hypothesis, promotion margin, threshold, sample size, or acceptance
  criterion was changed.
- No experiment was run, re-run, or fabricated; no result was manufactured.
- The protocol-236 identity conflict was **not** resolved: resolving it changes
  a pre-registered scientific question and requires a human decision.
- No network/model calls were made; all work was local CPU.

## 6. Results

Mean acceptance score rose **3.63 → 3.95** over 56 criteria; severe defects
(≤2) fell **4 → 0**. The ≥4-everywhere target is **not** fully met: 7 criteria
remain at 3, each with a named blocker (see `final-scorecard.md`).

## 7. Recommended next steps (need a human)

1. **Resolve protocol 236** (`docs/quality/protocol-236-conflict.md`): choose
   higher-N-real-workload vs S2, then re-label/re-pre-register accordingly.
2. **Authorize the powered replication of finding 6** (A11) if CPU budget
   permits — the largest open scientific gap.
3. Optionally wire `s2` to the CLI and add a per-bundle JSON-schema validator.
