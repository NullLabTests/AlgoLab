# ADR-0009: Quality-Diversity Archive + Basin Escape (Protocol 238)

**Status:** Accepted (pre-registered, frozen).
**Date:** 2026-10-15.

## Context

Protocol 230-235 established cost-aware selection, family-conditioned
knowledge, decision-rule isolation, and the adaptation-as-insurance finding
under shift. The strict multi-family promotion bar was not met at n=32 on the
real KNN micro-HPO workload. Protocol 238 tests whether a quality-diversity
archive plus periodic basin-escape forking improves validated discoveries per
fit-credit under shift.

## Decision

Implement a deterministic, serializable MAP-Elites archive
(`search/qd_archive.py`) and two first-class policy arms:

- `QDAdaptiveCostAwarePolicy` — cost-aware Thompson selection biased toward /
  restricted to the current QD archive.
- `BasinEscapePolicy` — every N=25 steps or on stagnation (no discovery in the
  last 5 attempts), fork a high-quality, high-novelty parent into a fresh
  adaptive trajectory with a reserved exploration budget of 3 steps.

The archive descriptors are (a) cost tier, (b) family-affinity signature
(performance vector across families), and (c) a simple outcome-statistic
embedding. Archive snapshots are written into the sealed evidence bundle as
`qd-archive.json`. Arm ids `qd-adaptive-cost-aware` and `basin-escape` are
supported by the harness and CLI alongside the carried-over arms.

No post-hoc tuning of archive bins, novelty weights, or fork parameters after
seeing outcomes.

## Consequences

- Existing arms and golden protocol-230-v1 reproduction remain byte-identical.
- Archive and fork state are fully inspectable in selection streams and the
  sealed bundle.
- The first confirmatory run is a smoke-size bundle (trials=2) under CPU-only
  constraints; all claims are UNRESOLVED-POWER and no promotion is claimed.
- Design sources: AgentDiscover (Farahbakhsh et al., arXiv:2610.05334),
  Kernel Autoresearch (Suwandi et al., arXiv:2610.10394), Fork-and-Flush
  (Ziakas et al., arXiv:2610.07447), AlgoLab protocols 230-235.
