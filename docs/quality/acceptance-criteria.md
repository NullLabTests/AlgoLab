# AlgoLab — Acceptance Criteria and Scoring Rubric

Version: 1.0.0 (frozen before implementation work on 2026-10-14, except where a
criterion is explicitly marked *revision pending*).

These are the gates this project holds itself to. Every criterion is meant to be
verifiable by a command, a test, an artifact, or an explicitly cited source.
A strong rating is earned by evidence, not by wording.

## Scoring scale (five points)

| Score | Meaning |
|---|---|
| 1 | Critical deficiency or absent capability. |
| 2 | Partially implemented, with important gaps. |
| 3 | Functional but with meaningful limitations. |
| 4 | Strong, verified, and well documented. |
| 5 | Excellent, independently verified, robust under relevant edge cases, and supported by reproducible evidence. |
| N/A | Genuinely does not apply; justification required. Distinguish "not assessed" from a score. |

Each score must cite evidence, a verification method, known limitations, and the
next step to improve it. Target: **≥ 4 on every applicable criterion**, and 5
where practical, without compromising scientific integrity. Where 4 is not
reachable, the remaining blocker and best achievable remedy are stated.

Criterion IDs are stable. Initial (pre-improvement) scores are recorded here;
final scores are in `docs/quality/final-scorecard.md`.

---

## A. Scientific validity

| ID | Criterion | Verification |
|---|---|---|
| A1 | Hypotheses are explicit, falsifiable, and scoped to the evidence. | Read `spec/research/23*.md` §Hypotheses; check each is a decision rule. |
| A2 | Baselines are appropriate, competitive, and documented. | Inspect harness arms + `protocol.json`; baseline is split-matched and compute-matched. |
| A3 | Evaluation procedures are specified before confirmatory results. | Manifest is frozen pre-run (`harness.ensure_manifest`); specs predate bundles. |
| A4 | Held-out evaluation is protected against leakage / repeated tuning. | Held-out family excluded from K0 prior; `run_held_out` uses `phase=held-out`. |
| A5 | Randomness and seeds are controlled and recorded. | Manifest records all seeds; determinism test; golden byte test. |
| A6 | Statistical methods match the design. | `statistics.py`: paired bootstrap/permutation when paired, Welch fallback; BH FDR. |
| A7 | Effect sizes and uncertainty are reported alongside significance. | `statistics.json` rows carry `delta`, `ci_low/high`, `effect_size`. |
| A8 | Multiple comparisons are handled. | `benjamini_hochberg` applied within family blocks and held-out block. |
| A9 | Negative/inconclusive results remain visible. | 235 reported unmet; protocol-230-v1 report retained. |
| A10 | Ablations distinguish competing explanations. | `c-permuted`, `b-shuffled`, `c-plus-permuted`; documented as non-definitive. |
| A11 | Generalization claims match the number/diversity of tasks. | README scopes findings per substrate; 235 explicitly n=32. |
| A12 | Promotion criteria cannot be weakened retrospectively. | Criteria live in `evaluate_claim`; prereg specs frozen; **D-2 is an open risk**. |

## B. Experimental reproducibility

| ID | Criterion | Verification |
|---|---|---|
| B1 | Configs are explicit and versioned. | `ExperimentConfig` + manifest with `protocol_version`, policy versions. |
| B2 | Inputs, environment, deps, revision, seeds recorded. | Bundle `environment.json` records dataset shapes, sklearn/numpy/python, measured seconds. |
| B3 | Raw results are distinguishable from derived summaries. | `conditions/*/raw-results.jsonl` vs `statistics.json` vs `report.md`. |
| B4 | Artifact schemas are validated. | Manifest/stats presence checks; **checksum-offer only, no schema validator per bundle**. |
| B5 | Checksums verified against actual bytes. | `test_protocol_230.py::test_checksums_are_consistent_and_complete`; **committed-bundle sweep is ad-hoc (to become a test)**. |
| B6 | Reproduction commands are documented and executable. | README quickstart + `run_protocol_236.py`; `make` targets. |
| B7 | Deterministic experiments are stable within a stated boundary. | `test_determinism.py`; `test_protocol_230_golden.py` byte test. |
| B8 | Nondeterministic results retain enough info for reanalysis. | Raw per-attempt streams retained. |
| B9 | Failed/interrupted runs are represented honestly. | HEAD commit message; untracked 236 bundle not presented as result. |
| B10 | Missing/malformed/conflicting artifacts fail safely. | `verify_reproducibility` returns structured failure; harness refuses to overwrite. |

## C. Software engineering

| ID | Criterion | Verification |
|---|---|---|
| C1 | Clear module boundaries and responsibilities. | Package layout in `implementation/algolab/README.md`; imports. |
| C2 | Explicit, validated interfaces and domain invariants. | Pydantic models; schema validator; DB triggers. |
| C3 | Correct state transitions and recovery. | `core/state.py`, `execution/recovery.py`, lifecycle tests. |
| C4 | Reliable persistence and provenance. | Append-only triggers; `tasks.workload` provenance (**D-3**). |
| C5 | Meaningful errors and failure handling. | Error taxonomy `docs/ERROR_CODES.md`; CLI exit codes 0/1/2. |
| C6 | Strict typing where practical. | `mypy --strict` clean on 45 files. |
| C7 | Consistent formatting and linting. | `ruff` clean. |
| C8 | Unit/integration/regression/property tests where appropriate. | 345 tests incl. golden + invariants; **no property-based tests**. |
| C9 | Backward-compatible public interfaces where feasible. | Golden byte test guards protocol-230-v1. |
| C10 | No unnecessary dependency or architectural complexity. | Runtime deps: pydantic, jsonschema, PyYAML, scikit-learn only. |

## D. Research governance and budget controls

| ID | Criterion | Verification |
|---|---|---|
| D1 | Compute budgets are enforced, not merely reported. | Ledger reserve/charge (M1); search loop bounded by `budget_credits`. |
| D2 | Expensive operations require explicit config with documented bounds. | `run_protocol_236.py` requires `--force`; FREE_CPU_RUNBOOK caps. |
| D3 | Failed ops do not silently exceed budgets or bypass gates. | Budget ledger partial-charge/overrun; harness breaks on cost overflow. |
| D4 | Research claims have traceable evidence. | Bundles → manifest → spec; **D-2 weakens this for 236**. |
| D5 | Promotion decisions are auditable. | `evaluate_claim` verdict written into bundle; `held-out-statistics.json`. |
| D6 | State changes/events have reliable provenance. | Append-only events; audit-log CLI. |
| D7 | Recovery does not corrupt/duplicate results. | `test_recovery.py`; no double charge. |
| D8 | Policy changes are distinguishable from scientific results. | Versioned policy constants; manifest `policy_versions`. |
| D9 | No automatic promotion from a self-reported agent conclusion. | Promotion is a computed criterion, not a narrative; autonomy stays L1. |

## E. Developer experience and open-source quality

| ID | Criterion | Verification |
|---|---|---|
| E1 | New contributor can understand architecture and run a minimal example. | READMEs; quickstart; **`search-run` default is heavy — a minimal example is needed**. |
| E2 | Install/test instructions work from a clean environment. | `scripts/setup.sh`; local editable install verified (CI never ran — D-9). |
| E3 | CLI help and errors are useful. | argparse help; exit codes; error taxonomy. |
| E4 | Examples are executable, not decorative. | README quickstart commands; **`docs/FREE_CPU_RUNBOOK.md` Codespace block partly aspirational**. |
| E5 | Documentation matches implementation. | **D-1 drift is the current blocker.** |
| E6 | CI checks the actual supported workflow. | **D-9**: the only Actions file was nested under `implementation/algolab/`, so GitHub never registered a workflow; CI never ran. |
| E7 | Dependencies and license obligations are clear. | `pyproject.toml`, MIT `LICENSE`. |
| E8 | Contribution guidance explains adding a protocol + validating evidence. | **Missing — no protocol template / CONTRIBUTING.** |
| E9 | README communicates current capabilities and limitations accurately. | Root README scopes findings; **D-1 references**. |

## F. Maintainability and feedback loops

| ID | Criterion | Verification |
|---|---|---|
| F1 | Failures become actionable regression tests. | Golden test exists; **artifact-integrity test missing**. |
| F2 | Repeated issues drive targeted doc/test/validation improvements. | This audit + `improvement-plan.md`. |
| F3 | Review processes identify independent failure classes. | Independent reviewer roles in this mission (§4.3). |
| F4 | Harness changes trigger relevant regression/calibration checks. | Golden test + protocol tests. |
| F5 | Quality metrics reveal regressions vs. reward test-count growth. | `final-scorecard.md` rubric; not test-count-based. |
| F6 | New abstractions justified by current requirements. | `rules.py` justified as substrate-agnostic core; **S2 (`workload_s2.py`) is not yet justified by a working consumer (D-5)**. |

---

## Initial scores (baseline HEAD `93e5f11`)

Scores are the auditor's judgement at baseline, before improvement work.

| Criterion | Score | Primary evidence / blocker |
|---|---|---|
| A1 | 4 | Explicit decision-rule hypotheses in each `23x` spec. |
| A2 | 4 | Split-matched, compute-matched baseline; documented. |
| A3 | 4 | Pre-run manifest freeze; goldens. |
| A4 | 4 | Held-out family never in K0; `phase=held-out` marker. |
| A5 | 4 | Seeds in manifest; determinism + golden tests. |
| A6 | 4 | Design-matched statistics. |
| A7 | 4 | CI + effect size in stats rows. |
| A8 | 4 | BH within family and held-out blocks. |
| A9 | 4 | 235 unmet reported. |
| A10 | 4 | Ablation arms; caveats documented. |
| A11 | 3 | Real-substrate evidence is one workload at n=32; scope caveats present but breadth is thin. |
| A12 | 2 | **D-2**: 236 prereg vs implementation conflict; no sealed run. |
| B1 | 4 | Versioned config + manifest. |
| B2 | 4 | Environment recorded incl. dataset shapes/versions. |
| B3 | 4 | Raw vs derived separated. |
| B4 | 3 | Presence checks only; no per-bundle schema validator. |
| B5 | 3 | Fresh-bundle checksum test exists; committed-bundle integrity only ad-hoc. |
| B6 | 4 | Documented commands; scripts. |
| B7 | 4 | Determinism + golden byte tests. |
| B8 | 4 | Raw streams retained. |
| B9 | 4 | Honest failure representation. |
| B10 | 4 | Fail-safe refusal; structured repro result. |
| C1 | 4 | Clear layout. |
| C2 | 4 | Models + triggers. |
| C3 | 4 | Tested state machines/recovery. |
| C4 | 3 | **D-3** provenance mislabel for real workloads. |
| C5 | 4 | Taxonomy + exit codes. |
| C6 | 4 | mypy strict clean. |
| C7 | 4 | ruff clean. |
| C8 | 4 | 345 tests incl. golden + invariants (no property tests). |
| C9 | 4 | Golden byte compat. |
| C10 | 4 | Minimal deps. |
| D1 | 4 | Ledger + bounded search loop. |
| D2 | 4 | `--force` guard; runbook caps. |
| D3 | 4 | Partial-charge/overrun audit; loop break. |
| D4 | 3 | **D-2** breaks traceability for 236. |
| D5 | 4 | Computed verdict in bundle. |
| D6 | 4 | Append-only events. |
| D7 | 4 | Recovery tests. |
| D8 | 4 | Versioned policies. |
| D9 | 4 | Computed criterion; L1 autonomy. |
| E1 | 3 | Minimal example for a newcomer is heavy/undocumented as "minimal". |
| E2 | 4 | setup.sh + local editable install (CI never ran; D-9). |
| E3 | 4 | Help + exit codes. |
| E4 | 3 | Quickstart works; Codespace section is aspirational. |
| E5 | 2 | **D-1** numerous dead references. |
| E6 | 1 | **D-9**: workflow nested under `implementation/algolab/` → never registered; CI never ran. |
| E7 | 4 | pyproject + MIT. |
| E8 | 1 | No protocol template / contribution guide. |
| E9 | 3 | Scoping is good but references are wrong (D-1). |
| F1 | 3 | Golden test exists; no artifact-integrity regression test. |
| F2 | 3 | This audit/plan is the mechanism (new). |
| F3 | 3 | Mission reviewer roles defined; not yet exercised in-repo. |
| F4 | 4 | Golden + protocol tests. |
| F5 | 4 | Rubric-based scorecard (this doc). |
| F6 | 2 | **D-5** S2 abstraction has no working consumer. |

Aggregate baseline: mean = 201/56 ≈ **3.59** over **56** applicable criteria
(A12=12, B10, C10, D9, E9, F6). **5 criteria score ≤ 2** (A12, E5, E6, E8, F6;
E6 corrected down after the D-9 CI finding). The improvement plan targets those
first. (Final scores: `docs/quality/final-scorecard.md`.)
