# Protocol 241 — Meta-Search: replay-grounded search-policy improvement

**Status:** PRE-REGISTERED (frozen before pilot execution) — 2026-11-19
**Owner:** AlgoLab meta-search capability (MASTER_SPEC §13, milestone M5 concept)
**Prior art:** protocols 230–240; DREAM-RSI audit
`docs/research/DREAM_RSI_INTEGRATION_AUDIT.md`

## Research question

Can a versioned, cost-aware search policy, evaluated against frozen discovery
traces and then tested prospectively, improve AlgoLab's rate of validated
algorithm discoveries per compute credit relative to the existing fixed search
policy — without degrading generalization to a held-out task family?

## Hypotheses

- **H0 (null):** the candidate policy's discovery rate per credit is equal to
  or worse than the fixed baseline on prospective experiments.
- **H1 (alternative):** the candidate policy's discovery rate per credit is
  strictly greater than the fixed baseline prospectively **and** is not
  degraded on the held-out family.

## Arms (all deterministic, no paid APIs)

1. `fixed-baseline` — existing fixed lexicographic search policy (A).
2. `replay-cost-aware` — DREAM-RSI-inspired per-credit success scoring with
   bounded exploration (B).
3. `evolved` — committed cost-efficiency plus effect-size term (C).
4. `random-control` — seeded uniform random selection (D, calibration floor).

## Preregistered design

- **Substrate:** `algolab.search.toy` (planted truth, two-seed replication
  gate), identical to the knowledge-loop line for continuity.
- **Training families:** alpha, beta. **Held-out confirmation family:** gamma.
- **Primary outcome:** validated discoveries per compute credit.
- **Secondary outcome:** distinct useful methods discovered per credit.
- **Seeds:** measurement base `424242`; confirmation base `989898`; replay seed
  `17`; trace seed `77100`. All preregistered and embedded in the bundle.
- **Trials:** 4 per family (pilot). **Episodes:** 8 per trial. **Budget:** 10
  credits per trial; selection stops when the budget would be exceeded.
- **Statistics:** paired bootstrap 95% CI (1000 resamples) on per-trial deltas,
  Welch p-value, Cohen's d; Benjamini-Hochberg correction is applied when more
  than one arm is tested against the baseline.
- **Missing data / unexplored branches:** replay records counterfactual
  decisions with `uncertain=true` and **no outcome label**. No estimate is
  manufactured. Replay output is marked `is_prospective_evidence=false`.
- **Multiple comparisons:** four arms versus one baseline; BH-FDR across the
  three non-baseline arms if the pilot is treated as confirmatory (it is not).

## Promotion gate (fixed before results; fail-closed)

- Stage A — historical replay: diagnostic only; **can never promote**.
- Stage B — prospective: primary delta > 0, CI lower bound > 0, p < 0.05;
  secondary CI lower bound ≥ 0.
- Stage C — independent confirmation on fresh seeds and held-out gamma:
  delta ≥ 0 and CI lower bound ≥ −0.001.
- Stage D — explicit, checksummed decision with rollback pointer. Any missing
  or failed stage → rejection.

## Exploratory vs confirmatory

This run is an **exploratory pilot** on a *synthetic* frozen trace (labelled as
such in the bundle). It validates the mechanism and gates; a policy promoted
here would still require a new confirmatory run on real recorded traces before
eligibility for research use. Negative results are valid and will be reported
as measured.

## Stopping rules and resource limits

Pilot is one bounded run (≤ 4 arms × 2 families × 4 trials × 8 episodes).
No unbounded loops, no network access at runtime, no generated code deployment,
no automatic changes to governance or promotion criteria.

## Reproduction

```bash
cd implementation/algolab
.venv/bin/python -m algolab.cli.main meta-search-run --dir experiments/protocol-241-v1
.venv/bin/python -m algolab.cli.main meta-verify --dir experiments/protocol-241-v1
```
