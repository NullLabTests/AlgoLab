# Protocol 238 — Completion Report

Quality-Diversity Archive + Basin Escape.

## Summary

Protocol 238 was pre-registered and frozen before any confirmatory run
(`spec/research/238_QD_BASIN_ESCAPE.md`). The QD archive and two new policy
arms were implemented, tested, and wired into the harness and `search-run`
CLI. The first confirmatory run was executed under the frozen pre-registration
as a pre-declared smoke size because the full n=96 exceeds the local CPU
budget; every claim is therefore UNRESOLVED-POWER.

Autonomy remains L1. No paid compute and no GPU were used. No free-form LLM
code generation, evolutionary code mutation, or M3/M4/M5 scope was implemented.
No prior protocol verdicts were altered.

## Pre-registration

- `spec/research/238_QD_BASIN_ESCAPE.md` — frozen before execution.
- Substrate: `hpo` KNN micro-HPO (alpha=breast_cancer, beta=wine,
  gamma=digits-900 held out).
- Operators: the 7 KNN knobs; flat nominal 10.0 credits; 0.005 absolute
  5-fold CV accuracy gate, both replicates.
- Primary metric: validated_discoveries / credits_consumed.
- Full grid: trials=96, episodes/trial=2, prior=20/family, budget=150,
  prior_seed=101, analysis_seed=11, seed_base=7, top_k=3.
- Smoke fallback: trials=2, prior=2/family, budget=60 (used).
- Promotion bar: same style as 231/235 (>=2-family, adjusted p < 0.05, CI
  excluding 0, held-out persistence).
- Outcome classes: A confirmed / B partial / C falsified.

## Implementation

- `implementation/algolab/src/algolab/search/qd_archive.py` — deterministic,
  serializable MAP-Elites archive; cost tier + family-affinity signature +
  outcome-statistic embedding; novelty query; selection-rule-as-query.
- `implementation/algolab/src/algolab/search/policies.py`:
  - `QDAdaptiveCostAwarePolicy` — cost-aware Thompson selection biased toward
    / restricted to the current QD archive.
  - `BasinEscapePolicy` — every N=25 steps or on stagnation (no discovery in
    the last 5 attempts), forks a high-quality, high-novelty parent into a
    fresh adaptive trajectory with a reserved exploration budget of 3 steps.
- Harness + CLI: both arms are first-class (`ARMS_PROTOCOL_238`,
  `_policy_factory`, manifest policy_versions, comparison matrix); archive
  snapshots are written into the sealed bundle as `qd-archive.json`.
- Golden protocol-230-v1 reproduction remains byte-identical.

## Checks

- `make test` (fast lane): **382 passed** in ~2m53s.
- `make lint` (ruff): **All checks passed**.
- `make type` (mypy strict): **Success: no issues found in 46 source files**.
- No network calls in tests. No golden bundles were modified.

## Evidence bundle

Sealed at `implementation/algolab/experiments/protocol-238-v1/` (68 files,
SHA-256).

Selected hashes:

| file | sha256 |
|---|---|
| manifest.json | `8a5669d81c741cbe77e98917b43d2bf181cae44545a0f8857dd4c1ce19f18c8c` |
| statistics.json | `a730defa591f01fe1cc610d420bd45eef041e49e6fba7ecf76eb2ed8ac8f4670` |
| qd-archive.json | `7eb5b5061872649481243763f90ae5baca19eec3b9134a2ef78c2d90794202f3` |
| report.md | `300d7cfb3b527bd609e29f06b03684f4c26701ae12215ebf1f3ad76c6e78f176` |
| checksums.json | `6c9f7fc19bf35a3fc98d53b6fff0b609aa8893b5145045db4c2821650385d58d` |

`checksums.json` itself is excluded from its own hash set; 68 deterministic
files are covered.

## Run record (claim-by-claim)

The full n=96 was not run (CPU budget < 10 minutes at 2-4 cores); the
pre-declared smoke size was used. n=2 is below the registered full grid, so no
claim reached the promotion bar.

| Claim | Pre-registered | Smoke observation (n=2) | Outcome |
|---|---|---|---|
| H1 | QD helps vs C+ | qd-adaptive-cost-aware 0.025000 vs adaptive-cost-aware 0.029167 (training); held-out 0.020833 vs 0.012500 | C — falsified / UNRESOLVED-POWER |
| H2 | basin escape helps under shift | held-out gamma 0.029167 vs 0.012500; training 0.025000 vs 0.029167 | C — directional smoke signal only, UNRESOLVED-POWER |
| H3 | no harm vs random | both new arms >= random on both training families (directional) | C — directional, UNRESOLVED-POWER |
| H4 | inspectability | qd-archive.json + parent IDs present in sealed bundle | A — confirmed (mechanism check) |

No claim is promoted. No archive/basin-escape tuning was performed after seeing
outcomes.

## Reproduce

```bash
cd implementation/algolab
make setup
make test          # 382 passed
make lint          # ruff clean
make type          # mypy strict clean

# Sealed smoke bundle (CPU only, no GPU, no paid compute)
.venv/bin/python -m algolab.cli.main search-run protocol-238-v1 \
  --workload hpo \
  --dir experiments/protocol-238-v1 \
  --trials 2 --episodes 2 --prior-attempts 2 --budget 60 \
  --arms static,knowledge-informed,adaptive,adaptive-cost-aware,random,\
knowledge-informed-cost-rank,knowledge-informed-family,\
knowledge-informed-family-cost-rank,adaptive-cost-aware-family,\
knowledge-informed-family-commit,knowledge-informed-family-alloc,\
qd-adaptive-cost-aware,basin-escape \
  --force
```

## Remaining risks

- Power: n=2 cannot establish multi-family promotion; H1/H2/H3 remain open.
- Substrate: KNN micro-HPO is the only substrate used in this run; no
  transfer claim is made to S2 or other task surfaces.
- Fork policy smoke validation is directional only; cadence/novelty weights
  were frozen before execution, not tuned post hoc.
- The archive snapshot in the bundle is the prior-seeded archive; per-trial
  archive states are inspectable via the arm selection streams.
EOF
