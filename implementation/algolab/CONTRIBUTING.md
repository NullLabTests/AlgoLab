# Contributing a Protocol

How to add a new knowledge-loop protocol (a pre-registered experiment on a
substrate) without breaking this repo's evidence discipline. This is a
checklist over the existing machinery, not a new framework. It complements
`../../spec/research/200_RESEARCH_METHOD.md` (hypothesis/decision rules) and
`../../spec/research/220_EXPERIMENT_PROTOCOL.md`.

## Ground rules

- **Pre-register before running.** The spec (below) must exist and be committed
  *before* the confirmatory run. Never edit a registered lever after seeing
  results; if you must, record an amendment and treat the result as exploratory.
- **No claim without a sealed bundle.** A claim is citable only if it points at
  a checksummed bundle produced by a registered run. Partial/aborted bundles are
  not evidence.
- **Do not reuse a protocol number** for a different design, and do not rename a
  design to match an existing spec. If a number is disputed, stop and record the
  conflict (see `../../docs/quality/protocol-236-conflict.md`) rather than
  picking one silently.
- **CPU-only, offline.** Built-in sklearn datasets only; no downloads, GPU, or
  paid APIs.

## Checklist

1. **Question and claim shape.** State the claim in the form
   "on substrate X, at n=Y, rule R beat S on pre-registered metric M", with an
   explicit disconfirmation condition.
2. **Spec.** Add `spec/research/<number>_<NAME>.md` covering: question; substrate
   and dataset; treatments and control; the single registered lever; sample
   size / seeds; primary and secondary metrics; promotion bar (with margins);
   version pins (`*_VERSION`, gate version); confounding controls; and the
   negative-result interpretation rules from `200_RESEARCH_METHOD.md`.
3. **Workload module** (`src/algolab/search/workload_<name>.py`). Deterministic;
   expose `run_attempt`, `operators`, `operator_cost`, version constants, and
   (for non-oracle workloads) `environment_metadata`.
4. **Register the workload.** Add a `WorkloadView` builder to
   `_WORKLOADS` in `search/harness.py`. Real workloads set `has_oracle=False`;
   list **all** families (including held-out) in `environment_metadata`.
5. **Driver/CLI (optional).** Add a `scripts/run_protocol_<number>.py` or a CLI
   `--workload` choice only once the number is settled.
6. **Smoke test.** Add a fast test that resolves the workload and runs a tiny
   end-to-end pass (2 trials, 1 arm) asserting a manifest + statistics are
   written. Keep it under the fast lane; mark genuinely heavy runs `@slow`.
7. **Run and seal.** Execute the registered run so it writes
   `experiments/<bundle>/` with `manifest.json`, `environment.json`,
   `conditions/`, `statistics.json`, `report.md`, and `checksums.json`. Do not
   hand-edit artifacts.
8. **Integrity.** `checksums.json` must verify; the at-rest check in
   `tests/test_artifact_integrity.py` will include it once the bundle name is
   added to `EXPECTED_SEALED_BUNDLES`.
9. **Report.** Write `report.md` separating **observation** (what the numbers
   are) from **interpretation** (what it might mean) from **limitations**
   (power, confounds, scope). Update `docs/STATUS.md` and the root README with
   the claim, n, spec link, and bundle link — or record the negative result
   honestly.

## Verify before pushing

```bash
make lint && make type && make test
```

All three must be clean. Never weaken a goal, margin, or criterion to make a
test or a run pass.
