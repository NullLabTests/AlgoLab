# AlgoLab v1 — Autonomous AI Algorithm Discovery Laboratory

AlgoLab is a bounded, reproducible research platform for proposing, implementing,
testing, rejecting, refining, and reporting candidate improvements to AI systems.

Its objective is not to "invent AGI on command." Its objective is to maximize the
rate of valid, reproducible algorithmic discoveries per unit of compute and human
oversight.

## Canonical research loop

1. Observe existing evidence.
2. Form a falsifiable hypothesis.
3. Estimate novelty and prior probability.
4. generate a candidate method.
5. plan a compute-bounded experiment.
6. implement and validate the candidate.
7. train and benchmark against strong baselines.
8. perform statistical analysis and ablation.
9. accept, reject, revise, or archive.
10. update the knowledge base and search policy.
11. publish reproducible reports.

## Start here

1. Read `MASTER_SPEC.md`.
2. Read `OPENCODE_KICKOFF_PROMPT.md`.
3. Give the kickoff prompt to OpenCode from the root of the repository.
4. OpenCode must produce plans and contracts before implementation.
5. The first executable milestone is a deterministic toy rediscovery pipeline,
   not unrestricted autonomous operation.

## Non-negotiable constraints

- Fixed compute and monetary budgets.
- Reproducible runs and immutable provenance.
- No benchmark result without a baseline.
- No discovery claim without replication and statistical support.
- No self-modification outside versioned, reviewable proposals.
- No uncontrolled external actions or credential use.
- Human approval before scaling compute, publishing, or changing governance.
