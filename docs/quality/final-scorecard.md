# AlgoLab — Final Quality Scorecard

- **Baseline:** HEAD `93e5f11220f8b98bb97a2c63d95be5054cd380e4` (audit in
  `docs/audits/initial-audit.md`).
- **This pass:** 2026-10-14. Verification: `make lint`, `make type`,
  `make test` → **365 passed, 3 warnings**, ruff clean, mypy strict clean (45
  files).
- **Criteria:** `docs/quality/acceptance-criteria.md` (56 applicable, five-point
  scale). Initial scores there; final below.
- **Machine-readable:** `docs/quality/scorecard.json`.

## Method

Scores were re-rated against the *same* evidence standard as the baseline. A
score rose only where a concrete, verifiable change landed (a committed test,
a doc that now matches `git ls-files`, or a workflow change). Where the
underlying risk is only *recorded* rather than *removed* (the protocol-236
identity conflict), the score rose modestly and the open blocker is named.

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
| A12 | 2 | 3 | ▲1 | D-2 now explicitly recorded (`docs/quality/protocol-236-conflict.md`) and flagged in `GREAT_PLAN.md`; run is non-silent. Blocker: identity still unresolved (human decision). |
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
| E2 | 4 | 4 | — | setup.sh + CI install. |
| E3 | 4 | 4 | — | Help + exit codes. |
| E4 | 3 | 3 | — | Quickstart works; Codespace section still partly aspirational. |
| E5 | 2 | 4 | ▲2 | D-1 fixed: dead references removed from root README, `docs/STATUS.md`, `FREE_CPU_RUNBOOK.md`, impl README, `workload_s2.py`; every referenced path verified present. |
| E6 | 3 | 5 | ▲2 | CI now runs `pytest -q -m "not slow"` (matches `make test`) plus a manual `workflow_dispatch` full job; marker lane wired. |
| E7 | 4 | 4 | — | pyproject + MIT. |
| E8 | 1 | 4 | ▲3 | **New** `implementation/algolab/CONTRIBUTING.md`: concrete protocol checklist over existing machinery. |
| E9 | 3 | 4 | ▲1 | Root README table now states 235b not run and 236 designation unresolved. |
| F1 | 3 | 5 | ▲2 | **New** artifact-integrity regression test (see B5). |
| F2 | 3 | 4 | ▲1 | This audit → plan → scorecard loop is the exercised mechanism. |
| F3 | 3 | 3 | — | Reviewer roles defined in the mission; not yet exercised in-repo. |
| F4 | 4 | 4 | — | Golden + protocol tests. |
| F5 | 4 | 4 | — | Rubric scorecard + machine-readable `scorecard.json`, not test-count-based. |
| F6 | 2 | 3 | ▲1 | `workload_s2` now has a working, tested consumer (`test_provenance_and_s2.py`) and consistent metadata; still not CLI-reachable pending the A12 decision. |

## Aggregate

| | Baseline | Final |
|---|---|---|
| Sum | 203 | 221 |
| Mean (of 56) | 3.63 | **3.95** |
| Criteria ≤ 2 | 4 (A12, E5, E8, F6) | **0** |
| Criteria = 3 | 12 | 7 (A11, A12, B4, E1, E4, F3, F6) |
| Criteria ≥ 4 | — | 49 |

## Honest assessment

The pass removed every severe (≤2) defect and raised the mean from 3.63 to
3.95. The stated target of **≥ 4 on every criterion is not fully met**: seven
criteria remain at 3, and each is blocked by a named, non-cosmetic reason:

- **A12 / F6** — the protocol-236 identity conflict is a *scientific* decision
  that must not be made autonomously. It is now impossible to overlook.
- **A11** — real-substrate evidence remains thin (one workload, n=32); closing
  it needs compute budget authorization, not code.
- **B4** — no per-bundle JSON-schema validator; presence/hash checks only.
- **E1 / E4 / F3** — a minimal runnable example, a non-aspirational Codespace
  path, and in-repo reviewer exercises are genuine but lower-value follow-ups.

No goal, margin, threshold, or criterion was weakened to reach these scores, and
no result was manufactured. The largest open items are the 236 decision and the
missing powered replication.
