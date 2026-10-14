# AlgoLab — Final Quality Scorecard

- **Baseline:** HEAD `93e5f11220f8b98bb97a2c63d95be5054cd380e4` (audit in
  `docs/audits/initial-audit.md`).
- **This pass:** 2026-10-14. Verification: `make lint`, `make type`,
  `make test` → **366 passed** (fast lane), ruff clean, mypy strict clean (45
  files). CI green on Python 3.11 and 3.12.
- **Criteria:** `docs/quality/acceptance-criteria.md` (56 applicable, five-point
  scale). Initial scores there; final below.
- **Machine-readable:** `docs/quality/scorecard.json`.

## Method

Scores were re-rated against the *same* evidence standard as the baseline. A
score rose only where a concrete, verifiable change landed (a committed test,
a doc that now matches `git ls-files`, a workflow change, or a resolved
governance decision). The protocol-236 identity conflict (D-2) was resolved by
human decision on 2026-10-14, so the two criteria it had blocked (A12, F6) are
re-scored now that the blocker is **removed** rather than merely recorded.

## Final scores

| ID | Base | Final | Δ | Evidence / remaining blocker |
|---|---|---|---|---|
| A1 | 4 | 4 | — | Decision-rule hypotheses in each `23x` spec. |
| A2 | 4 | 4 | — | Split-matched, compute-matched baseline. |
| A3 | 4 | 4 | — | Pre-run manifest freeze; goldens. |
| A4 | 4 | 4 | — | Held-out family never in K0; `phase=held-out`. |
| A5 | 4 | 4 | — | Seeds in manifest; determinism + golden tests. |
| A6 | 4 | 4 | — | Design-matched statistics. |
| A7 | 4 | 4 | — | CI + effect size in stats rows. |
| A8 | 4 | 4 | — | BH within family and held-out blocks. |
| A9 | 4 | 4 | — | 235 unmet reported. |
| A10 | 4 | 4 | — | Ablation arms; caveats documented. |
| A11 | 3 | 3 | — | Real-substrate breadth still one workload at n=32. Needs a powered run (blocked, CPU). |
| A12 | 2 | 4 | ▲2 | **Resolved (D-2).** 236 = higher-N real workload (committed spec now authoritative); S2 re-designated protocol 237 with its own prereg (`237_SECOND_SUBSTRATE_TRANSFER.md`). No promotion criterion can be silently re-labelled; the ambiguous identity is gone. |
| B1 | 4 | 4 | — | Versioned config + manifest. |
| B2 | 4 | 4 | — | Environment incl. shapes/versions recorded. |
| B3 | 4 | 4 | — | Raw vs derived separated. |
| B4 | 3 | 3 | — | Still presence checks; no per-bundle schema validator. |
| B5 | 3 | 5 | ▲2 | **New** `tests/test_artifact_integrity.py` re-hashes every committed bundle's bytes, checks well-formedness, presence, and report/statistics; fails on any tamper. |
| B6 | 4 | 4 | — | Documented commands; scripts. |
| B7 | 4 | 4 | — | Determinism + golden byte tests. |
| B8 | 4 | 4 | — | Raw streams retained. |
| B9 | 4 | 4 | — | Aborted 236 bundle labeled as such in `docs/STATUS.md`. |
| B10 | 4 | 4 | — | Fail-safe refusal; structured repro result. |
| C1 | 4 | 4 | — | Clear layout. |
| C2 | 4 | 4 | — | Models + triggers. |
| C3 | 4 | 4 | — | Tested state machines/recovery. |
| C4 | 3 | 5 | ▲2 | D-3 fixed: `tasks.workload` now derives from `self.wl.key` (`harness.py`), not `"toy-discovery"`; guarded by `tests/test_provenance_and_s2.py`. |
| C5 | 4 | 4 | — | Taxonomy + exit codes. |
| C6 | 4 | 4 | — | mypy strict clean. |
| C7 | 4 | 4 | — | ruff clean. |
| C8 | 4 | 4 | — | 365 tests incl. golden, invariants, integrity, provenance. Still no property-based tests. |
| C9 | 4 | 4 | — | Golden byte compat. |
| C10 | 4 | 4 | — | Minimal deps. |
| D1 | 4 | 4 | — | Ledger + bounded search loop. |
| D2 | 4 | 4 | — | `--force` guard; runbook caps. |
| D3 | 4 | 4 | — | Partial-charge/overrun audit; loop break. |
| D4 | 3 | 4 | ▲1 | 236 status on `docs/STATUS.md` no longer implies sealed evidence; the conflict is documented. Traceability gap now honest, not misleading. |
| D5 | 4 | 4 | — | Computed verdict in bundle. |
| D6 | 4 | 4 | — | Append-only events. |
| D7 | 4 | 4 | — | Recovery tests. |
| D8 | 4 | 4 | — | Versioned policies. |
| D9 | 4 | 4 | — | Computed criterion; L1 autonomy. |
| E1 | 3 | 3 | — | README quickstart present; `search-run` default still heavy, no minimal example added. |
| E2 | 4 | 4 | — | setup.sh + local editable install verified; evidence corrected: the earlier "CI installs" citation was void (CI never ran, D-9). |
| E3 | 4 | 4 | — | Help + exit codes. |
| E4 | 3 | 3 | — | Quickstart works; Codespace section still partly aspirational. |
| E5 | 2 | 4 | ▲2 | D-1 fixed: dead references removed from root README, `docs/STATUS.md`, `FREE_CPU_RUNBOOK.md`, impl README, `workload_s2.py`, `rules.py`; every referenced path verified present. |
| E6 | 1 | 5 | ▲4 | **Correction (post-push review).** Baseline is 1, not 3: the only Actions file was nested under `implementation/algolab/`, so GitHub never registered a workflow (`total_count: 0`) and **CI never ran** (D-9). Now a correct root `.github/workflows/ci.yml` runs the fast lane `-m "not slow"` plus a manual full job; nested file removed. |
| E7 | 4 | 4 | — | pyproject + MIT. |
| E8 | 1 | 4 | ▲3 | **New** `implementation/algolab/CONTRIBUTING.md`: concrete protocol checklist over existing machinery. |
| E9 | 3 | 4 | ▲1 | Root README table now states 236 (higher-N, pre-registered, not run) and 237 (S2) with honest status; no dead 235b/236 references. |
| F1 | 3 | 5 | ▲2 | **New** artifact-integrity regression test (see B5). |
| F2 | 3 | 4 | ▲1 | This audit → plan → scorecard loop is the exercised mechanism. |
| F3 | 3 | 3 | — | Reviewer roles defined in the mission; not yet exercised in-repo. |
| F4 | 4 | 4 | — | Golden + protocol tests. |
| F5 | 4 | 4 | — | Rubric scorecard + machine-readable `scorecard.json`, not test-count-based. |
| F6 | 2 | 4 | ▲2 | S2 is now protocol 237: pre-registered (`237_SECOND_SUBSTRATE_TRANSFER.md`), covered by `test_provenance_and_s2.py`, and CLI-reachable (`search-run --workload s2`, guarded by `test_search.py`). Abstraction justified by a current, runnable requirement. |

## Aggregate

| | Baseline | Final |
|---|---|---|
| Sum | 201 | 223 |
| Mean (of 56) | 3.59 | **3.98** |
| Criteria ≤ 2 | 5 (A12, E5, E6, E8, F6) | **0** |
| Criteria = 3 | 11 | 5 (A11, B4, E1, E4, F3) |
| Criteria ≥ 4 | — | 51 |

> **Correction (2026-10-14, post-push review).** The first version of this
> scorecard scored E6 baseline 3 and final 5 on the assumption CI worked. The
> post-push review found **D-9**: the workflow was nested under
> `implementation/algolab/`, GitHub never registered it, and CI never ran.
> E6 baseline is corrected to **1** (raises baseline ≤2 count to 5 and lowers
> the baseline mean to 3.59); E6 final remains **5** only after the workflow was
> moved to the repository root in the follow-up commit. The audit's D-9 records
> the finding.
>
> **Second correction (2026-10-14, after CI first ran).** The Python 3.11 job
> exposed **D-10**: the golden guard compared full-precision `statistics.json`
> byte-for-byte, which only reproduces on the sealing environment (last-ULP
> libm/BLAS differences). No numeric score changed; the guard now compares JSON
> numerically (1e-9) and keeps byte-exact comparison for the raw condition
> streams and `report.md`, and the reproducibility wording was qualified.

> **Third correction (2026-10-14, D-2 resolved).** The owner chose Option 1
> (236 = higher-N real workload; the S2 substrate → protocol 237 with its own
> prereg). The blocker behind A12 and F6 is now **removed** rather than merely
> recorded, so both rose 3 → 4 (final sum 221 → 223, mean 3.95 → 3.98;
> criteria-at-3 7 → 5). The registered 236 alpha-margin lever remains
> unimplemented and no `protocol-236-v1` bundle is sealed.

## Honest assessment

The pass removed every severe (≤2) defect and raised the mean from 3.59 to
3.98. The stated target of **≥ 4 on every criterion is not fully met**: five
criteria remain at 3, and each is blocked by a named, non-cosmetic reason:

- **A11** — real-substrate evidence remains thin (one workload, n=32); closing
  it needs compute budget authorization, not code.
- **B4** — no per-bundle JSON-schema validator; presence/hash checks only.
- **E1 / E4 / F3** — a minimal runnable example, a non-aspirational Codespace
  path, and in-repo reviewer exercises are genuine but lower-value follow-ups.

No goal, margin, threshold, or criterion was weakened to reach these scores, and
no result was manufactured. The largest open items are the unimplemented 236
alpha-margin lever and the missing powered replication. The D-9 finding is a
reminder that "CI passes" was never true here until this pass — it is now
verified by an actual run.
