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
| WP-1 | Recorded the 236 identity conflict; decision **deferred in the first pass**, then **resolved by the owner (Option 1)**: 236 = higher-N real workload, S2 → protocol 237 | `docs/quality/protocol-236-conflict.md`, `spec/research/237_SECOND_SUBSTRATE_TRANSFER.md`; `README.md`, `docs/STATUS.md`, `GREAT_PLAN.md` |
| WP-2 | `tasks.workload` derived from the real workload, not `"toy-discovery"` | `src/algolab/search/harness.py` (3 sites) |
| WP-3 | Permanent at-rest integrity test over all committed bundles | `tests/test_artifact_integrity.py` |
| WP-4 | Removed dead references; corrected 235b/236 status | root `README.md`, `docs/STATUS.md`, `docs/FREE_CPU_RUNBOOK.md`, `implementation/algolab/README.md`, `src/algolab/search/workload_s2.py`, `src/algolab/search/rules.py` |
| WP-5 / D-9 | CI runs the documented fast lane; full lane wired; workflow **moved to repo root** so GitHub actually runs it | `.github/workflows/ci.yml` (root), removed nested copy, `Makefile` |
| WP-6 | S2 metadata lists held-out family; docstring matches code; smoke test; **`s2` wired into the CLI** after D-2 resolved | `src/algolab/search/workload_s2.py`, `src/algolab/cli/main.py`, `tests/test_provenance_and_s2.py`, `tests/test_search.py` |
| WP-7 | Protocol contributor checklist | `implementation/algolab/CONTRIBUTING.md` |

Also corrected three self-inconsistencies found in this session's own
artifacts: the audit's D-4 claim (that `make test-slow` "passes"), and two
arithmetic claims in `acceptance-criteria.md` (56 criteria, not 50; 4 at ≤2,
not 10).

## 3. Verification (evidence)

```text
$ make lint     -> All checks passed!
$ make type     -> Success: no issues found in 45 source files
$ make test     -> 366 passed in ~105 s (fast lane, -m "not slow")
```

- Baseline was 345 tests; +21 new/split tests, all green. The golden
  reproduction guard (`test_protocol_230_golden.py`) still passes, so WP-2 did
  not alter any artifact bytes.
- A post-push CI run (Python 3.11) exposed defect **D-10**: the golden guard
  compared full-precision `statistics.json` byte-for-byte, which is only
  reproducible on the sealing environment (last-ULP libm/BLAS differences).
  The guard now compares JSON artifacts numerically (1e-9) and keeps byte-exact
  comparison for the raw condition streams and `report.md`; see the audit D-10.
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
- The protocol-236 identity conflict was **not** resolved in the first pass
  (it changes a pre-registered scientific question and required a human
  decision). It was **resolved by the owner on 2026-10-14 (Option 1):** 236
  stays the higher-N real workload; the S2 substrate becomes protocol 237 with
  its own pre-registration. The registered 236 alpha-margin lever remains
  unimplemented, so no `protocol-236-v1` bundle was sealed.
- No network/model calls were made; all work was local CPU.

## 6. Results

Mean acceptance score rose **3.59 → 3.98** over 56 criteria; severe defects
(≤2) fell **5 → 0**. The ≥4-everywhere target is **not** fully met: 5 criteria
remain at 3, each with a named blocker (see `final-scorecard.md`).

> **Post-push correction:** the first pass scored CI (E6) at baseline 3 and
> missed **D-9** — the workflow lived under `implementation/algolab/` and was
> never registered by GitHub, so **CI had never run**. A root workflow now
> fixes this; the audit, scorecard and baseline mean above are corrected
> accordingly (baseline mean 3.63 → 3.59; ≤2 defects 4 → 5).
>
> **Second follow-up:** CI's first real run exposed **D-10** (golden guard was
> environment-dependent for full-precision floats). The owner then resolved
> **D-2** (Option 1), re-scoring A12 and F6 (3 → 4), so the final mean rose
> 3.95 → 3.98 and criteria-at-3 fell 7 → 5.

## 7. Recommended next steps (need a human)

1. **Implement the registered 236 alpha-margin lever** (per-family margins:
   alpha 0.0035, beta/gamma 0.005; versions 1.2.0 / gate 1.1.0), verify the
   machinery-invariant control (trials 0..31 byte-reproduce 235-v1 beta/gamma),
   then seal `protocol-236-v1` — requires authorizing the compute.
2. **Authorize the powered replication of finding 6** (A11) if CPU budget
   permits — the largest open scientific gap.
3. Optionally add a per-bundle JSON-schema validator (B4) and a minimal
   runnable example (E1/E4). (`s2` was wired to the CLI in this follow-up.)
