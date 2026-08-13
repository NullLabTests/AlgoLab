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
10. Update the knowledge base and search policy.
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
| M4 | Knowledge layer: schema v3, deterministic statistics, evidence records, operator catalog, skill registry | In progress |

## Non-negotiable constraints

- Fixed compute and monetary budgets.
- Reproducible runs and immutable provenance.
- No benchmark result without a baseline.
- No discovery claim without replication and statistical support.
- No self-modification outside versioned, reviewable proposals.
- No uncontrolled external actions or credential use.
- Human approval before scaling compute, publishing, or changing governance.
