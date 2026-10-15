# Protocol 239 — Completion Report

Typed Feature-Transform Substrate + Powered QD Evaluation.

## Summary

Protocol 239 was pre-registered and frozen before any confirmatory run
(`spec/research/239_TYPED_TRANSFORM_SUBSTRATE.md`). A new typed
feature-transform substrate (`transform`) was implemented, wired into the
harness/CLI, and evaluated under a pre-registered powered design. The target
n=32 exceeded the local CPU budget; the pre-registered fallback (trials=8,
prior=20/family, budget=100, 7 arms) was executed and sealed.

Autonomy remains L1. No paid compute and no GPU were used. No free-form LLM
code generation, evolutionary code mutation, or M3/M4/M5 scope was implemented.
No prior protocol verdicts were altered.

## Pre-registration

- `spec/research/239_TYPED_TRANSFORM_SUBSTRATE.md` — frozen before execution.
- Substrate: `transform` — 14 typed feature transforms over
  `StandardScaler -> LogisticRegression`; 5-fold stratified CV, two
  replicates, 0.005 absolute margin; varying operator costs (5.0–18.0).
- Families: alpha=breast_cancer, beta=wine, gamma=digits-900 (held out).
- Primary metric: validated_discoveries / credits_consumed.
- Full grid target: trials=32 (rejected: projected 45 min > 10-min CPU budget).
- Fallback (executed): trials=8, episodes/trial=2, prior=20/family,
  budget=100, prior_seed=101, analysis_seed=11, seed_base=7, top_k=3.
- Promotion bar: >=2-family, adjusted p < 0.05, CI excluding 0, held-out
  persistence.

## Implementation

- `implementation/algolab/src/algolab/search/workload_transform.py` —
  deterministic sklearn-compatible substrate; 14 typed transformers cloned
  per CV fold (fit on train only; no leakage); varying costs; paired
  split-matched baseline.
- Harness + CLI: `--workload transform` is first-class (`_transform_view`,
  manifest versions, comparison matrix). QD archive + basin-escape arms run
  unmodified on the new substrate.
- Golden protocol-230-v1 reproduction remains byte-identical.

## Checks

- `make test` (fast lane): **388 passed** in ~5m00s.
- `make lint` (ruff): **All checks passed**.
- `make type` (mypy strict): **Success: no issues found in 47 source files**.
- No network calls in tests. No golden bundles were modified.

## Evidence bundle

Sealed at `implementation/algolab/experiments/protocol-239-v1/` (SHA-256).

Selected hashes:

| file | sha256 |
|---|---|
| manifest.json | `1d6c8a73542ea566749df628b1028fbbad1a9b74989dbf3dc0550bbb3bebaac9` |
| statistics.json | `7e659ab7c661385f718b65781b728d4fbee931523c28ceac2e1920cb68c11227` |
| qd-archive.json | `6683d14e9f151132152ca5020104bda9234b4116fee8d787083a98bdc7ce29c3` |
| report.md | `cb786cee9e865d9071a29c892c1153cc7a3c0572cff642429e8b59967deafdfe` |
| checksums.json | `de2b8d0d362d867edc98a0b3ed9cb44c266a41f55ebbd413b50affd4debec265` |

## Run record (claim-by-claim, n=8)

| Claim | Pre-registered | Observation (n=8) | Outcome |
|---|---|---|---|
| H1 QD > C+ | qd-adaptive-cost-aware > adaptive-cost-aware on >=2 families (adj p<0.05) | beta d=+0.0045 (q=0.66); alpha d=0.000 (q=1.0); directional positive on beta only | C — UNRESOLVED-POWER (n=8 < 32 target) |
| H2 basin escape helps under shift | basin-escape held-out gamma > adaptive-cost-aware (directional) | gamma: 0 discoveries vs C+ 28; training: 0 vs 16 | C — FALSIFIED (below random) |
| H3 no harm vs random | both new arms >= random on every family | basin-escape 0 < random 8 (training); 0 < random 22 (gamma) | C — FALSIFIED |
| H4 archive richness | transform archive populates more distinct cells than 238 KNN smoke | 13 cells / 1806 attempts (transform) vs 4 cells / 384 attempts (KNN smoke); 3.2x more distinct behaviours per cell | A — confirmed (descriptive) |

**Overall outcome class: C (falsified / UNRESOLVED-POWER).**

- The QD archive arm itself did not harm: it was the second-best training arm
  (eff 0.0125 vs C+ 0.0104) and survived on held-out gamma (eff 0.0171). The
  directional beta gain is consistent with the 238 mechanism but is not
  significant at n=8.
- The basin-escape arm is cleanly falsified on this substrate: it scores zero
  discoveries on both training families and held-out gamma, below the random
  floor. The fork-and-flush mechanism (forced replay of a high-quality,
  high-novelty parent for a reserved budget) does not escape any useful basin
  here — it removes the adaptive loop's ability to reallocate spend.
- The 235 commitment-collapse finding replicates: knowledge-informed-family-
  commit scores 20 discoveries in training but **zero** on held-out gamma
  (operator-value structure inverts), while the adaptive arms survive. This is
  the adaptation-as-insurance hypothesis demonstrated again on a second
  substrate.

## Comparison to 238 smoke

| arm | 238 KNN smoke (n=2) eff | 239 transform (n=8) eff |
|---|---|---|
| adaptive-cost-aware | 0.0292 | 0.0104 |
| qd-adaptive-cost-aware | 0.0208 | 0.0125 |
| basin-escape | 0.0250 | 0.0000 |

The 238 smoke showed basin-escape competitive; the powered 239 run shows it
destructive. The 238 smoke was plumbing, not evidence; 239 is the first
adequately-sized measurement and it falsifies the fork mechanism.

## Reproduce

```bash
cd implementation/algolab
make setup && make test && make lint && make type

.venv/bin/python -m algolab.cli.main search-run protocol-239-v1 \
  --workload transform --dir experiments/protocol-239-v1 \
  --trials 8 --episodes 2 --prior-attempts 20 --budget 100 \
  --arms static,adaptive,adaptive-cost-aware,random,\
knowledge-informed-family-commit,qd-adaptive-cost-aware,basin-escape \
  --path /tmp/algolab-239-v1.sqlite --force
```

## Remaining risks

- Power: n=8 cannot establish multi-family promotion; H1 remains open. A
  powered replication (trials>=32, ~45 min CPU) is required to resolve it.
- Substrate: one new substrate (transform); no claim of transfer to other
  tabular families or to the KNN substrate beyond the directional consistency
  noted above.
- Mechanism: basin-escape is falsified on this substrate; the fork policy's
  reserved-budget replay removes adaptation. A redesigned fork (fresh-posterior
  forking rather than replay) would be a new mechanism requiring a new
  pre-registration.
- The transform catalog is hand-designed; a different catalog could change
  the QD arm's margin.
