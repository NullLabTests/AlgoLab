# Protocol 242 — Corrected meta-search policy comparison

**Status:** PRE-REGISTERED — frozen before execution, 2026-11-19.
**Supersedes:** protocol 241 as an *informative* test. Protocol 241's bundle is
retained as provenance of a mis-scaled pilot; its negative result is not a
finding about policy quality. This protocol is a new, preregistered experiment.

## Defects corrected before preregistration (disclosed)

1. **Cold-start prior:** the replay/cost-aware and evolved policies assigned a
   constant optimistic prior to untried methods, so the deterministic tie-break
   selected `decompose` (20 credits) rather than a cheap operator. The prior is
   now cost-normalised: `(alpha + beta) / cost`. Same prior, cost-aware now.
2. **Replay agreement:** previously compared a policy's choice to the first
   child appended to the trace, not to a recorded decision. The synthetic trace
   now records `historical_choice` on the decision state, and agreement is
   computed only where such a decision exists (`n_agreement_applicable`).

Neither fix changes a promotion threshold; they fix the implementation that
the thresholds evaluate.

## Research question

Under a budget matched to the operator cost scale, does either cost-aware
policy discover more validated algorithms per credit than the fixed AlgoLab
search policy, and does any gain survive a held-out family and FDR correction?

## Preregistered design

- **Substrate:** `algolab.search.toy` (same planted-truth generator as 241).
- **Arms:** fixed-baseline (A), replay-cost-aware (B), evolved (C),
  random-control (D). Policies are frozen, versioned objects; no agent rewrites
  policy source; no paid API.
- **Training families:** alpha, beta. **Held-out:** gamma (fresh seeds).
- **Trials:** 8 per family. **Episodes:** 8 per trial.
- **Budget:** 40 credits per trial (≥ the most expensive single operator), so a
  trial cannot terminate before a measurement is recorded.
- **Seeds:** training base `555111`; confirmation base `777333`; replay `17`;
  trace `77100`. Bootstraps: 2000 resamples. Alpha: 0.05.
- **Primary outcome:** validated discoveries per credit.
- **Secondary:** distinct useful methods per credit.
- **Statistics:** paired percentile bootstrap CI, Welch p-value, Cohen's d;
  Benjamini-Hochberg FDR across the three non-baseline arms; q-values compared
  to alpha for promotion.
- **Promotion gate (unchanged):** Stage A replay-only never promotes; Stage B
  requires delta > 0, CI low > 0 and q < 0.05; Stage C requires held-out
  delta ≥ 0 and CI low ≥ −0.001 on fresh seeds; any failure → rejection.
- **Stopping / resources:** one bounded run (4 arms × 2 families × 8 trials ×
  8 episodes = 512 measurements), CPU-only, no network at runtime.

## Separate exploratory vs confirmatory

This is a **preregistered screening experiment**, not a final confirmation. A
promotion here makes a policy *eligible* for a later independent confirmation
on a different substrate; it is not automatic deployment. Negative results are
valid and will be reported as measured.

## Reproduction

```bash
cd implementation/algolab
.venv/bin/python -m algolab.cli.main meta-search-run \
  --dir experiments/protocol-242-v1 --protocol-id protocol-242 \
  --trials 8 --episodes 8 --budget 40 --seed-base 555111 \
  --confirmation-seed-base 777333 --bootstrap-iterations 2000 \
  --apply-bh --record-historical-choice --force
.venv/bin/python -m algolab.cli.main meta-verify --dir experiments/protocol-242-v1
```
