# Protocol 244 — Real-workload transfer of the evolved search policy

**Status:** PRE-REGISTERED — frozen before execution, 2026-11-22.
**Predecessor:** protocol 243 (`experiments/protocol-243-v1/`).
**Decision scope:** research evidence only; no deployment and no change to any
promotion criterion.

## Question

Does the unchanged `evolved` policy that was promoted on the toy substrate
transfer to real, deterministic scikit-learn workloads, or was protocol 243's
gain specific to the toy generator?

This is a transfer test, not a new policy search. The candidate policy,
baseline policy, statistic, and promotion gate are unchanged from protocol 243.
Historical replay is diagnostic only and cannot promote.

## Preregistered design

- **Arms:** `fixed-baseline` (control) versus `evolved` only. The policy
  definitions and checksums are unchanged from protocol 243.
- **Primary workload:** `algolab.search.workload_transform` (version 1.0.0,
  14 typed transform operators, non-flat costs). **Secondary workload:**
  `algolab.search.workload_hpo` (version 1.1.0, 7 fixed KNN configurations,
  flat costs). Both are frozen, offline, CPU-only workloads with no network
  access and no ground-truth policy labels.
- **Training families:** `alpha` and `beta` for each workload. **Independent
  confirmation family:** `gamma` for each workload, with a distinct seed base.
- **Trials:** 8 per family for both stage B and stage C. **Episodes:** 8 per
  trial. **Budget:** 40 credits per trial, matched across arms and unchanged
  from protocol 243.
- **Fresh seeds:** prospective base `924_211`; independent confirmation base
  `351_773`; historical replay `17`; frozen trace construction `77_100`.
  Bootstrap resamples: 2000. Alpha: 0.05.
- **Primary outcome:** validated discoveries per credit. **Secondary
  outcome:** distinct useful methods per credit.
- **Multiplicity:** Benjamini–Hochberg FDR across the two prospective p-values
  (one `evolved`-versus-baseline comparison per workload). The BH-adjusted
  q-value, not the raw p-value, gates promotion.
- **Promotion gate:** unchanged and fail-closed. Stage A replay alone never
  promotes. Stage B requires Δ > 0, 95% CI low > 0, q < 0.05, and secondary CI
  low ≥ 0. Stage C requires held-out Δ ≥ 0 and CI low ≥ −0.001.
- **Trace class:** a frozen trace of real workload attempts used only for
  historical replay diagnostics; it is explicitly not prospective evidence.

## Stopping and resources

One bounded run, with no adaptation after outcomes are observed:

```
2 workloads × 2 arms × (2 training families + 1 held-out family)
  × 8 trials × 8 episodes = 768 prospective attempts
```

Plus 2 arms × 2 workloads = 4 diagnostic replay evaluations and 6 real
attempts used to build the frozen trace. CPU-only, no paid APIs, no GPU, no
network access.

## Reproduce

```bash
cd implementation/algolab
.venv/bin/python -m algolab.cli.main meta-transfer-run \
  --dir experiments/protocol-244-v1 --protocol-id protocol-244 \
  --workloads transform,hpo --trials 8 --episodes 8 --budget 40 \
  --seed-base 924211 --confirmation-seed-base 351773 \
  --bootstrap-iterations 2000 --apply-bh --force
.venv/bin/python -m algolab.cli.main meta-verify \
  --dir experiments/protocol-244-v1
```

The runner writes `manifest.json`, `report.md`, `trace.json`, per-workload
environment metadata, per-workload replay artifacts, per-workload/arm stage
A/B/C evaluations, per-workload/arm promotion decisions, and `checksums.json`.

## Reporting rule

All outcomes, including negative, null, and inconclusive results, are reported
as measured. A nonnegative result on the toy substrate does not become a
real-workload claim without this protocol's own gates passing. No threshold,
seed, arm, evaluator, or promotion definition may be changed after execution.
