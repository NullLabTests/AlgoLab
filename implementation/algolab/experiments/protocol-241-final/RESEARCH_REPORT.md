# Protocol 241 mission — final research report

**Date:** 2026-11-22
**Branch:** `integration/dream-rsi-meta-search`
**Source state:** `integration/dream-rsi-meta-search`, single PR commit
**Scope:** verify the prior DREAM-RSI/meta-search work, preserve all historical
bundles, then preregister and execute Protocol 244 real-workload transfer.
**Resource class:** CPU-only, offline, no paid APIs, no GPU, no new runtime
dependencies.

## Executive verdict

The meta-search capability is real and reproducible **within the toy
substrate**: the unchanged `evolved` policy was promoted by Protocol 243 under
fresh seeds, matched compute, paired bootstrap CIs, held-out confirmation, and
the unchanged fail-closed gate. That result does **not** transfer to the two
real workloads tested here. Protocol 244 rejected promotion on both `transform`
and `hpo`; the primary gains were small, multiplicity-corrected p-values were
≈0.505, and the `transform` confidence interval crossed zero. No deployment,
autonomy expansion, or real-workload performance claim is warranted.

Historical results were not rewritten. Protocols 241–243, their
preregistrations, evaluators, promotion thresholds, and sealed bundles remain
untouched.

## A–J verdicts

Verdict scale: **DEMONSTRATED** = direct preregistered or audited evidence in a
verified artifact; **PARTIALLY DEMONSTRATED** = directional/supporting evidence
that fails at least one preregistered gate; **INCONCLUSIVE** = evidence does not
resolve the claim; **NOT DEMONSTRATED** = the claim was tested and not supported,
or no valid evidence exists.

| ID | Claim | Verdict | Evidence |
|---|---|---|---|
| A | DREAM-RSI audit is source-grounded: frozen replay, prefix-only decisions, qualified-round selection, no bandit or `DiscoverEnv`; Apache-2.0 ideas-only attribution recorded | **DEMONSTRATED** | `docs/research/DREAM_RSI_INTEGRATION_AUDIT.md`, `docs/research/DREAM_RSI_INTEGRATION_REPORT.md`, `THIRD_PARTY_NOTICES.md` |
| B | Reuse is compatible with AlgoLab governance: no source copying from incompatible licenses, no new runtime dependency, no paid API/GPU, no second event/artifact store | **DEMONSTRATED** | `spec/architecture/100_SYSTEM_ARCHITECTURE.md`, `docs/api/README.md`, `pyproject.toml`, audit report §6 |
| C | Frozen, content-addressed traces and read-only replay with explicit counterfactual uncertainty are implemented | **DEMONSTRATED** | `algolab/meta_search/traces.py`, `replay.py`; `tests/test_meta_search.py`; all sealed bundles contain integrity-checked `trace.json` |
| D | Versioned, frozen search policies and structured proposals are implemented without agent-rewritten source | **DEMONSTRATED** | `algolab/meta_search/policies.py`; `tests/test_meta_search.py::TestPolicies` |
| E | Promotion is fail-closed: replay alone cannot promote; missing/degraded stages reject; BH q replaces raw p when required | **DEMONSTRATED** | `algolab/meta_search/evaluation.py::promote`; `tests/test_meta_search.py::TestCorrectedMechanisms`, `TestPromotion`; protocol 242's q-driven rejection |
| F | Protocol 241 pilot found no preregistered improvement; the 10-credit null was budget-scale limited and the post-hoc 40-credit diagnostic also found none | **DEMONSTRATED** | `experiments/protocol-241-v1/`, `experiments/protocol-241-v1-diagnostic/`; all arms `REJECTED_PROSPECTIVE` |
| G | Protocol 242 corrected screen supports a positive direction for `evolved` but fails multiplicity control | **PARTIALLY DEMONSTRATED** | Δ = +0.020833/credit, CI low +0.003819, raw p = 0.0465, held-out Δ = +0.022778, but BH q = 0.0907; `experiments/protocol-242-v1/` |
| H | Protocol 243 promotes `evolved` under the unchanged gate, scoped to the toy substrate | **DEMONSTRATED** | Δ = +0.018720 (CI +0.010324…+0.027454, p = q = 0.0005), held-out Δ = +0.021296 (CI low +0.015046), all gates passed; `experiments/protocol-243-v1/` |
| I | Sealed bundles are independently verifiable and byte-reproducible; replay evidence is never used for promotion | **DEMONSTRATED** | 243 clean-room reproduction: 10 files byte-identical, `verified=true`; 244 fresh-process reproduction: 16 files byte-identical, `verified=true`; both `replay_only_promotion_detected=false` |
| J | The promoted toy policy transfers to real `transform` and `hpo` workloads | **NOT DEMONSTRATED** | Protocol 244: transform Δ = +0.004045 (CI low −0.003175, q = 0.5052, secondary CI low −0.003257, held-out Δ = 0); hpo Δ = +0.002500 (CI low 0, q = 0.5052); both `REJECTED_PROSPECTIVE`; `experiments/protocol-244-v1/` |

## What was verified before Protocol 244

- Repository state: HEAD `a6f54ac`, branch `integration/dream-rsi-meta-search`.
- DREAM-RSI inspected at `8ec35bd2538220517ce1bfca4282db21b8c518db`; audit is
  ideas-only, Apache-2.0 attribution recorded.
- Protocol 241 pilot: negative; diagnostic: negative.
- Protocol 242 screen: positive raw effect, BH failure, no promotion.
- Protocol 243 confirmatory toy run: `PROMOTED`, with all thresholds unchanged.
- Protocol 243 clean-room reproduction from `/tmp/opencode/algolab-clean-241`
  into `/tmp/opencode/repro-243` used the documented CLI command. Results were
  identical (`PROMOTED`, same deltas), `diff -rq` reported `IDENTICAL_TREES`, and
  `meta-verify --json` reported `verified=true`, 10 files, `trace_integrity=true`,
  no replay-only promotion.

## Protocol 244 (preregistered before execution)

Preregistration: `spec/research/244_META_SEARCH_REAL_WORKLOAD_TRANSFER.md`,
frozen 2026-11-22 before the run. Design: `fixed-baseline` versus unchanged
`evolved`; primary workload `transform`, secondary `hpo`; alpha/beta training
families and gamma held-out; 8 trials/family/stage; 8 episodes; 40-credit trial
budget; seeds `924211 / 351773 / 17 / 77100`; 2000 bootstrap resamples; BH across
the two workload p-values; unchanged promotion gate.

Executed command:

```bash
cd implementation/algolab
.venv/bin/python -m algolab.cli.main meta-transfer-run \
  --dir experiments/protocol-244-v1 --protocol-id protocol-244 \
  --workloads transform,hpo --trials 8 --episodes 8 --budget 40 \
  --seed-base 924211 --confirmation-seed-base 351773 \
  --bootstrap-iterations 2000 --apply-bh --force
.venv/bin/python -m algolab.cli.main meta-verify \
  --dir experiments/protocol-244-v1 --json
```

### Results

| Workload | Arm | Primary Δ/credit | 95% CI low | raw p | BH q | Secondary CI low | Held-out Δ | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| transform | evolved | +0.004045 | −0.003175 | 0.4093 | 0.5052 | −0.003257 | 0.000000 | REJECTED_PROSPECTIVE |
| hpo | evolved | +0.002500 | +0.000000 | 0.5052 | 0.5052 | +0.000000 | +0.012500 | REJECTED_PROSPECTIVE |

Stage A replay agreement was 0.5 for both arms on both workloads and is
diagnostic only. `meta-verify` reported `verified=true`, 16 files verified,
`trace_integrity=true`, no mismatches/extra files, and no replay-only
promotion.

### Reproduction

A fresh process using a copied source tree (`/tmp/opencode/algolab-244-src`)
wrote `/tmp/opencode/repro-244`. Both summary lines matched, `diff -rq` reported
`IDENTICAL_TREES`, and `scripts/verify_meta_reproduction.py` reported
`pass=True`, 16 files, no failures, no extra files. See
`protocol-244-reproduction-verification.json`.

### Known reporting defect

`experiments/protocol-244-v1/manifest.json` doubles two non-decision-relevant
planning upper bounds (records 1536 attempts / 7680 credits; correct values are
768 attempts / 3840 credits) because an extra factor of two was applied inside
the already per-arm accounting loop. The sealed bundle was not rewritten, and
the runner was not changed after execution; this preserves byte-reproducibility.
The correction, derivation, and non-decision relevance are recorded in
`compute-accounting-correction.json`.

## Automated checks

- `.venv/bin/python -m pytest -q --durations=15`: **474 passed, 0 failed**.
  Complete output: `test-results.txt`. Warnings were pre-existing Pydantic,
  NumPy/sklearn deprecation, and ResourceWarnings; none were test failures.
- `.venv/bin/python -m ruff check src tests scripts`: **All checks passed!**
  (`ruff.txt`).
- `.venv/bin/python -m mypy`: **Success: no issues found in 59 source files**
  (`mypy.txt`).
- New regression tests cover the Protocol 244 runner, CLI, sealing/verification,
  tamper detection, determinism, and fail-closed unknown workload handling
  (`tests/test_meta_transfer.py`).

### Review correction before merge

PR review found that this final-summary bundle initially recorded checksums as
`{bytes, sha256}` objects. The repository convention, enforced by
`tests/test_artifact_integrity.py`, is a flat `filename -> sha256` map. The
format was corrected before merge; no research result, threshold, historical
bundle, or sealed protocol artifact was changed. All checks above were re-run
after the correction.

## Failure analysis and limitations

- The toy positive effect did not replicate on real workloads. Both primary
  intervals fail the strict positive-lower-bound requirement after BH control.
- `transform` additionally has a negative secondary CI low and zero held-out
  delta. `hpo` has a zero primary CI low despite a positive held-out delta; a
  point estimate is not enough under the preregistered gate.
- Sample size is modest (8 trials/family/stage). This is an absence of
  preregistered evidence, not proof of an exactly zero transfer effect.
- Replay traces for Protocol 244 are built from a small real-attempt prefix and
  remain diagnostic. Off-policy branches are not evidence.
- Protocol 244 workloads are offline sklearn benchmarks, not a production
  search environment. Verdict J is scoped accordingly.
- The Protocol 241 budget defect and Protocol 242 multiplicity failure remain
  recorded as historical facts; neither was repaired retrospectively.

## Final position

The research line supports a **toy-substrate meta-search capability** with
auditable, fail-closed promotion. It does **not** support a real-workload
transfer or autonomy claim. The correct next step, if pursued, would be a new
preregistered protocol with a prespecified power analysis and a candidate policy
selected independently of Protocols 242/243 — not a post-hoc threshold change.
