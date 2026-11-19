# DREAM-RSI → AlgoLab integration report

**Date:** 2026-11-19 · **Protocol:** 241 (preregistered, frozen before run)
**Starting commit:** `ac1df7d8b838a92dd5a5d751ca419bb558666b7c` (`main`, clean tree)
**DREAM-RSI commit inspected:** `8ec35bd2538220517ce1bfca4282db21b8c518db`
**Branch:** `integration/dream-rsi-meta-search`

## 1. What was learned from DREAM-RSI

DREAM-RSI's reusable insight is not "let an agent rewrite policy source"; it is
the separation of a *frozen replay world* from *live search*, a prefix-only
decision interface, and a promotion step that refuses to select a policy that
failed qualification. Its `TraceEnv` reveals only recorded outcomes, its
`raw_scores.json` freezes a world, and its `heuristic_search/eval.py` scores
policies by attainment AUC minus a parallelism penalty. Selection in
`workflow.py` is a deterministic argmax over *qualified* rounds, never a bandit.
Source-level facts that differ from the README: no `DiscoverEnv`, no bandit/UCB,
code default agent is `claude`, code grid default 2×2.

## 2–4. Reused / rewritten / rejected

Full file-by-file classification is in
`DREAM_RSI_INTEGRATION_AUDIT.md`. Summary:

- **Ideas adapted (no source copied):** frozen replay trace, prefix-only
  probing, explicit cost accounting, qualification-before-promotion.
- **Rewritten AlgoLab-native:** `algolab/meta_search/traces.py`
  (content-addressed append-only trace with sha256 chain and canonical JSON),
  `replay.py` (read-only replay + outcome-kind enum + counterfactual
  uncertainty), `policies.py` (frozen structured versioned policy + proposals),
  `evaluation.py` (four-stage fail-closed gate using the existing
  `algolab.statistics`), `protocol_241.py` (one sealed, deterministic bundle).
- **Rejected:** agent-rewritten policy modules and model SDKs (violates
  MASTER_SPEC §13 / no-paid-API requirement); `NodeStore` filesystem tree and
  trace-pool (would duplicate the event store/artifact store); KernelBench and
  SimpleTES/AGPL tasks (wrong substrate, incompatible license).

## 5. Architecture changes

```text
search-run bundles (230–240)          meta-search (241)
  toy/hpo/transform/compose  ──seed──▶  DiscoveryTrace (append-only, checksummed)
                                          │
                                          ▼
                                      ReplayEnv ── Stage A (diagnostic only)
                                          │
                    SearchPolicy (versioned, frozen) ── Stage B (prospective, toy substrate)
                                          │           ── Stage C (held-out gamma, fresh seeds)
                                          ▼
                                      promote() ── Stage D (fail-closed, checksummed verdict)
                                          │
                                  meta-search-run / meta-verify (sealed bundle)
```

No second event store, budget ledger, experiment registry or artifact manager
was introduced. The toy substrate and `algolab.statistics` are reused directly.

## 6. Dependencies and licenses

No new runtime dependency. DREAM-RSI is Apache-2.0 (`Copyright 2026 Google
LLC`); ideas-only reuse means no copying obligations attach, but attribution is
recorded in `implementation/algolab/THIRD_PARTY_NOTICES.md` and the audit.
Nothing from MIT-vendored or AGPL-fetched upstream trees was imported.

## 7–8. Hypothesis and methodology

Preregistered in `spec/research/241_META_SEARCH_POLICY_IMPROVEMENT.md` before
execution: H0 = no improvement in validated discoveries per credit; H1 =
improvement with no held-out degradation. Four deterministic arms (fixed
baseline, replay/cost-aware, evolved, seeded random control), matched seeds and
budgets, paired bootstrap 95% CI + Welch p + Cohen's d, held-out family gamma
for confirmation. Promotion requires prospective significance and non-negative
held-out delta; replay alone cannot promote.

## 9. Results (pilot vs diagnostic — clearly distinguished)

**Preregistered pilot** (`experiments/protocol-241-v1/`): all four arms scored
0 discoveries/credit on training families; every arm `REJECTED_PROSPECTIVE`
(primary p = 1.0 for the three non-control arms). **No policy was promoted.**
Independent verification: `verified=True`, 16 files verified, trace integrity
OK, no replay-only promotion.

**Post-hoc exploratory diagnostic** (`experiments/protocol-241-v1-diagnostic/`,
NOT preregistered, NOT confirmatory): budget raised 10 → 40 credits after the
pilot revealed that most operator costs (10–40 credits) exceed the 10-credit
preregistered trial budget, so most trials terminated before a measurement.
At the feasible budget the cost-aware and evolved arms were slightly *worse*
than baseline (Δ = −0.006548/credit, 95% CI low −0.0125, p = 0.14) and the
random control Δ = −0.007540 (p = 0.31); held-out deltas also non-positive.
All arms again `REJECTED_PROSPECTIVE`, bundle independently verified.

**Protocol 242 — preregistered corrected screen** (`experiments/protocol-242-v1/`,
spec committed before run). Defects fixed: cost-normalised cold-start prior and
replay agreement against a *recorded* decision. Budget 40 (matched to operator
costs), 8 trials/family, BH-FDR. Both cost-aware arms improved: evolved Δ =
+0.020833/credit (CI low +0.003819, raw p = 0.0465) and held-out Δ = +0.022778,
but BH q = 0.0907 → **not promoted**. Replay agreement is now well-defined and
measured against an actual recorded decision.

**Protocol 243 — preregistered confirmatory run**
(`experiments/protocol-243-v1/`, spec committed before run). Single arm
`evolved` vs fixed baseline, 24 trials/family, fresh seeds
`1337711 / 2711337`, BH across one comparison. Prospective Δ = +0.018720
discoveries/credit (95% CI +0.010324 to +0.027454, p = q = 0.0005, d = 1.01);
secondary Δ = +0.011594 (CI low +0.007701); held-out gamma Δ = +0.021296
(CI low +0.015046, d = 1.38); secondary held-out Δ = +0.006019 (CI low
+0.004861). All gates passed → **PROMOTED** (checksum
`355ec5510eb46ed7910997a65b35f29e7cd4826a8f1409d03d809e6b073b2f99`).
Bundle independently verified (10 files, trace integrity OK).

**Conclusion:** the capability is now scientifically informative. Within the
**toy substrate**, the evolved cost-aware policy measurably improves
discoveries per credit under fresh, matched, FDR-corrected conditions and on a
held-out family. This is *not* a real-workload or deployment claim; it makes
the policy eligible for subsequent research runs only.

## 10. Limitations

- The pilot's frozen "history" is a **synthetic trace** (labelled as such); no
  real meta-search histories existed prior to protocol 241.
- Replay cannot estimate outcomes for branches never explored; those decisions
  are recorded with `uncertain=true` and no label.
- Toy substrate only; no real-workload transfer shown.
- The protocol-241 budget was mis-scaled to operator costs; its null is a
  methodology artifact, explicitly superseded by protocols 242/243.
- Protocol 243 is confirmatory **within the toy substrate only**; transfer to
  real workloads (hpo/transform/compose) remains untested. The policy was
  selected by the protocol-242 screen, so an independent replication on a
  different substrate is still required before any broader claim.
- Replay agreement is defined only on states whose trace records a decision;
  it remains diagnostic, never a promotion criterion.

## 11. Reproduction

```bash
cd implementation/algolab
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests scripts
.venv/bin/python -m mypy
.venv/bin/python -m algolab.cli.main meta-search-run --dir experiments/protocol-241-v1 --force
.venv/bin/python -m algolab.cli.main meta-verify --dir experiments/protocol-241-v1
# post-hoc diagnostic only:
.venv/bin/python -m algolab.cli.main meta-search-run --dir experiments/protocol-241-v1-diagnostic --budget 40 --force
# preregistered corrected screen and confirmatory run:
.venv/bin/python -m algolab.cli.main meta-search-run --dir experiments/protocol-242-v1 --protocol-id protocol-242 --trials 8 --budget 40 --seed-base 555111 --confirmation-seed-base 777333 --apply-bh --record-historical-choice --force
.venv/bin/python -m algolab.cli.main meta-search-run --dir experiments/protocol-243-v1 --protocol-id protocol-243 --arms fixed-baseline,evolved --trials 24 --budget 40 --seed-base 1337711 --confirmation-seed-base 2711337 --apply-bh --record-historical-choice --force
```

## 12. Future research

1. Re-scale the *preregistered* budget and episodes to operator costs and
   rerun as a new protocol (242) with ≥ 8 trials/family and BH-FDR.
2. Replace the synthetic trace with real accumulated search traces from
   `search-run` bundles (requires a trace-export bridge).
3. Add a held-out *task* (not only family) and an LLM-proposer arm that is
   strictly optional and gated by the same promotion logic.
