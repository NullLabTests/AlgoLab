# AlgoLab v1 — Autonomous AI Algorithm Discovery Laboratory

AlgoLab is a bounded, reproducible research platform for proposing,
implementing, testing, rejecting, refining, and reporting candidate
improvements to AI systems.

Its objective is not to "invent AGI on command." Its objective is to
maximize the rate of valid, reproducible algorithmic discoveries per unit
of compute and human oversight — by encoding the scientific method as an
executable pipeline with hard budgets, immutable provenance, and
statistical gates no claim may bypass.

## The canonical research loop

1. Observe existing evidence.
2. Form a falsifiable hypothesis.
3. Estimate novelty and prior probability.
4. Generate a candidate method.
5. Plan a compute-bounded experiment.
6. Implement and validate the candidate.
7. Train and benchmark against strong baselines.
8. Perform statistical analysis and ablation.
9. Accept, reject, revise, or archive.
10. Update the knowledge base and search policy — the causal loop at the
    heart of the platform; demonstrated in the toy environment
    (protocols 230–233; see "What we learned" below); real-workload
    transfer remains unproven.
11. Publish reproducible reports.

Every step in this loop has a versioned contract in this repository; no step
is left to an unconstrained agent.

## Repository layout

```text
MASTER_SPEC.md                  canonical master specification (source of truth)
OPENCODE_KICKOFF_PROMPT.md      agent kickoff contract — read before implementing
spec/                           ontology, architecture, research method, governance
planning/                       milestones and roadmaps
schemas/                        canonical JSON Schemas for manifests
prompts/                        agent role definitions
templates/                      hypothesis and artifact templates
workflows/                      reference workflow definitions
implementation/algolab/         the executable core (see its README)
```

## Start here

1. Read `MASTER_SPEC.md` — the canonical specification.
2. Read `OPENCODE_KICKOFF_PROMPT.md` — the agent onboarding contract.
3. Give the kickoff prompt to OpenCode from the repository root.
4. OpenCode must produce plans and contracts *before* implementation.
5. The first executable milestone is a deterministic toy rediscovery
   pipeline, not unrestricted autonomous operation. See `planning/`.

## Milestone status

| Milestone | Scope | Status |
|---|---|---|
| M0 | Contracts: IDs, models, state machines, append-only event store, budget ledger, manifest validation, CLI | Delivered |
| M1 | Deterministic execution core: expansion, persistent queue, isolated workers, hash-sealed artifacts, recovery, aggregation | Delivered |
| M4 | Knowledge layer: schema v3, deterministic statistics, evidence records, operator catalog, skill registry | Delivered |
| M5 | Causal loop evaluation: pre-registered protocols 230–233 executed (see findings below) | Demonstrated in toy environment; real-workload transfer unproven |

## What we learned (M5 knowledge-loop research line, protocols 230–233)

All results come from pre-registered, checksummed experiments on the
deterministic toy-discovery environment; every claim below is scoped to
that substrate. Artifacts: `implementation/algolab/experiments/`, specs:
`spec/research/23{0,1,2,3}_*.md`.

1. **The knowledge loop is real — but only with the right selector
   objective.** Plain Thompson-sampling adaptation (C) beat static and
   random everywhere, yet *failed* its pre-registered ≥2-family promotion
   bar because it tied frozen knowledge (B) on the beta family
   (`experiments/protocol-230-v1/`). Post-hoc diagnosis: prior saturation +
   exploration starvation + a cost-blind selection rule.
2. **One mechanism change — score candidates by success probability per
   credit — fixed it.** Cost-aware C+ beats A and B decisively on both
   training families and transfers to the held-out family: the first
   promotion-criterion pass of the loop claim
   (`spec/research/231_COST_AWARE_SELECTION.md`,
   `experiments/protocol-230-v2/`; beta d = 8.6).
3. **Knowledge representation was silently destroying most of history's
   value.** Pooling per-family history into one aggregate made useful-in-
   one-family operators look mediocre. Family-conditioned priors more than
   doubled/tripled frozen-policy performance (d = 3.9–11.4) and lifted even
   the adaptive arm to ~99.5% of the theoretical oracle
   (`spec/research/232_FAMILY_CONDITIONED_KNOWLEDGE.md`,
   `experiments/protocol-232-v1/`).
4. **The remaining adaptive margin is structural, not informational.**
   Sweeping prior size 30→240 attempts/family left the frozen-vs-adaptive
   gap unchanged (~+0.03 on beta): more history made frozen policies
   *better informed and worse scheduled*, because a top-K cycle cannot
   express "concentrate spend on cheap-and-good." Adaptation value does
   NOT shrink with history quality
   (`spec/research/233_PRIOR_SIZE_DOSE_RESPONSE.md`,
   `experiments/protocol-233-p{30,60,120,240}/`).

**Design conclusions carried forward:** store family-tagged aggregates;
prefer adaptive cost-aware consumers of knowledge over any frozen schedule;
treat frozen schedules as bounded-quality baselines regardless of how much
history they read.

## Non-negotiable constraints

- **Human oversight by default, autonomy by exception** — autonomy is
  earned experimentally, stage by stage, never asserted by design changes.
- Fixed compute and monetary budgets.
- Reproducible runs and immutable provenance.
- No benchmark result without a baseline.
- No discovery claim without replication and statistical support.
- No self-modification outside versioned, reviewable proposals.
- No uncontrolled external actions or credential use.
- Human approval before scaling compute, publishing, or changing governance.
