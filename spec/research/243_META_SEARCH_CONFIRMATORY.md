# Protocol 243 — Confirmatory evaluation of the evolved search policy

**Status:** PRE-REGISTERED — frozen before execution, 2026-11-19.
**Predecessor:** protocol 242 (`experiments/protocol-242-v1/`).

## Why this is confirmatory, not another screen

Protocol 242 was a preregistered screen of three non-baseline arms. The
`evolved` arm was the only one that passed **every** gate except the
multiplicity correction (Δ = +0.020833 discoveries/credit, 95% CI low
+0.003819, raw p = 0.0465, BH q = 0.0907; held-out Δ = +0.022778; secondary CI
low +0.00243 prospectively and +0.00472 held-out). Its raw p is borderline and
its direction is consistent on the held-out family, so a larger, **fresh-seed**
test of this single arm is justified. This protocol fixes the arm, seeds and
threshold before looking at new data. The screen's seeds are not reused.

## Preregistered design

- **Arms:** `fixed-baseline` (control) vs `evolved` only. No other arm is
  tested; BH-FDR is therefore applied to a single comparison (q = p).
- **Substrate and families:** `algolab.search.toy`, alpha + beta training;
  gamma held-out with a different fresh seed base.
- **Trials:** 24 per family (3× protocol 242). **Episodes:** 8. **Budget:** 40
  credits/trial (unchanged, matched to operator costs).
- **Fresh seeds:** training base `1_337_711`; confirmation base `2_711_337`;
  replay `17`; trace `77100`. Bootstrap resamples: 2000. Alpha: 0.05.
- **Primary outcome:** validated discoveries per credit. **Secondary:**
  distinct useful methods per credit.
- **Promotion gate:** unchanged and fail-closed — prospective Δ > 0, CI low > 0,
  p < 0.05, secondary CI low ≥ 0; held-out Δ ≥ 0 and CI low ≥ −0.001.
  Replay remains diagnostic only and cannot promote.
- **Scope of any promotion:** makes the policy eligible for use in subsequent
  toy-substrate research only. It is not deployment, not a real-workload claim,
  and not a change to governance criteria.

## Stopping and resources

One bounded run: 2 arms × 2 families × 24 trials × 8 episodes = 768
measurements, CPU-only, no network, no generated-code deployment.

## Reproduction

```bash
cd implementation/algolab
.venv/bin/python -m algolab.cli.main meta-search-run \
  --dir experiments/protocol-243-v1 --protocol-id protocol-243 \
  --arms fixed-baseline,evolved --trials 24 --episodes 8 --budget 40 \
  --seed-base 1337711 --confirmation-seed-base 2711337 \
  --bootstrap-iterations 2000 --apply-bh --record-historical-choice --force
.venv/bin/python -m algolab.cli.main meta-verify --dir experiments/protocol-243-v1
```
