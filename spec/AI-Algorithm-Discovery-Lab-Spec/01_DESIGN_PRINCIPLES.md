# 01 DESIGN PRINCIPLES

- **Status:** v1.0 — Complete specification
- **Purpose:** The immutable engineering and scientific principles that govern every module of AlgoLaB.
- **Cross-references:** `00_EXECUTIVE_SUMMARY.md`, `02_RESEARCH_MISSION.md`, `03_SYSTEM_ARCHITECTURE.md`, `19_GOVERNANCE.md`

---

## 1. Role of This Document

Every module in this repository shall be designed, implemented, and accepted
according to these principles. If a module-level requirement conflicts with a
principle, the principle wins and the conflict is surfaced as a design review
(`19_GOVERNANCE.md` §9). Principles have a **rationale** and an **engineering
consequence** that tells implementers how to apply them.

The name of the system is **AlgoLaB**.

## 2. The Principles

### P1. Discovery rate is the objective; breakthroughs are asymptotes.
- **Statement.** The success metric is *discoveries per unit of compute*,
  not "invent AGI." The lab optimizes the process, not any single miracle
  output.
- **Rationale.** Breakthroughs cannot be scheduled; discovery throughput can.
- **Consequence.** Every module is scored by how it increases hypothesis
  throughput and evaluation quality per credit. Modules that consume budget
  without increasing discovery rate are de-prioritized (`12`, `18`).
- **Falsification.** If doubling a module's budget does not raise discovery
  rate, redesign or remove the module.

### P2. The fixed compute budget is the primary currency and a hard constraint.
- **Rationale.** Without scarcity, there is no prioritization pressure, and
  the system degenerates into brute-force search.
- **Consequence.** All planning, accounting, and reporting is denominated in
  **compute credits** (1 credit = 1 A100-80GB GPU-hour, `03` §9.2). The budget
  ledger in `16_DISCOVERY_DATABASE.md` §6 is authoritative and monotonic; the
  planner (`12`) cannot schedule work the ledger cannot fund.

### P3 Reproducibility is a hard gate, not a preference.
- **Consequence.** Every run carries a **config hash** (SHA-256 over canonical
  config + code tree hash) and pinned seeds. A run that cannot be reproduced
  from its hash is not an experiment, it is a malfunction. See
  `13_TRAINING_PIPELINE.md` §4, `16_DISCOVERY_DATABASE.md` §7.

### P4 Hypothesis-driven search beats shuffling knobs.
- **Consequence.** Mutation/architecture generation must be attached to a
  falsifiable hypothesis with an explicit mechanism, predicted effect size,
  and failure mode. Knob-gridding without a hypothesis is disallowed as a
  primary strategy (it may be used as a post-discovery ablation). See
  `07_HYPOTHESIS_ENGINE.md`.

### P5 Statistical rigor gates every claim.
- **Consequence.** No metric difference becomes a "discovery" (or a "negative
  result" usable as evidence) without power analysis, multiple-comparison
  correction, seed replication, and effect-size reporting (`15`). False
  positives are the most expensive failure mode in the system
  (`21-FM-0501`).

### P6 Lineage and provenance are mandatory, free-form memory is not.
- **Consequence.** Every artifact (candidate, hypothesis, run, paper) records
  parents, operating modules, mutation operator, config hash, and timestamps.
  Unstructured agent "memory" is disallowed as a source of scientific truth;
  only the DDB and KG are authoritative. See `16`, `05`.

### P7 One orchestrator; deterministic control plane; asynchronous effects.
- **Consequence.** There is exactly one orchestrator charged with dispatching
  the research loop; all other modules observe events and write results. This
  prevents conflicting writers corrupting the loop state. See `03` §7, `04`.

### P8 Human oversight by default, autonomy by exception.
- **Consequence.** Governance gates (`19`) are open for low-cost in-budget
  experiments and closed for high-cost, high-risk, or irreversible actions.
  The lab can earn autonomy by demonstrating statistical trustworthiness over
  sustained operation (`19` §7).

### P9 Fail loud, fail early, fail with a citation.
- **Consequence.** A failing run must stop promptly, emit a structured failure
  event with the module location and a failure-mode code (`21`), and never be
  silently swallowed. Silent tolerance of failures corrodes the budget ledger
  and statistical corpus.

### P10 Everything is versioned; nothing is overwritten.
- **Consequence.** Configs, code trees, prompts, KG snapshots, and result
  artifacts are immutable+addressed (content-addressed storage). Mutation must
  fork a new version, never edit an old one. `16` §7, `05` §6.

### P11 Simple interfaces, complex internals.
- **Consequence.** Module-to-module communication is limited to well-typed
  events and REST/queue calls with normative JSON schemas. Internal
  complexity (LLM sampling, evolution, stats) is confined inside modules.
  This is what allows 23 modules to be built out of order.

### P12 The lab must survive the failure of any one component.
- **Consequence.** No single non-fatal failure may halt the whole loop. The
  orchestrator must be able to restart dispatch from the last checkpointed
  event sequence, and the runner must tolerate worker loss. `20` §7, `21` §4.

### P13 Efficiency is a first-class research output.
- **Consequence.** A candidate that matches baseline accuracy at a fraction of
  compute/latency/memory is a valid Tier-C discovery even with zero accuracy
  gain. Benchmarks must always record cost alongside score. `14` §5.

### P14 Guardrails that limit intellectual risk and permit known-bad exploration.
- **Consequence.** Exploration may target known-bad regions cheaply (negative
  results are valuable), but may not exceed safety/bias/security gates
  (`19`) or spend beyond the credit envelope (`12`). Cheap negatives are
  encouraged; expensive, uninformative runs are the enemy.

### P15 Self-improvement is a module, not ambient behavior.
- **Consequence.** The lab's own search strategy changes only through the
  gated meta-pipeline (`18`), with A/B tests against the current champion
  strategy. No module may freelancing tweak its own prompt to chase a
  metric in a way that bypasses its governance.

## 3. Secondary Principles (operational hygiene)

1. **Secrets never enter artifacts.** Model keys, API tokens, credentials are
   injected at deployment layer only (`20` §8). Papers, run reports, and
   artifacts are scrubbed.
2. **Determinism by default, nondeterminism only where scientifically
   authorized.** LLM sampling is pinned per agent+candidate.
3. **A numeric result without its CIs is a rumor.** CIs ship with all metrics.
4. **One seed is a screenshot; three seeds are a result; five seeds trigger
   discovery confirmation.**
5. **The artifact is the unit of analysis.** A paper is not written to text
   from another text; it is assembled from run reports + lineage + evidence
   records (`17` §4).
6. **`Km` — the knowledge metric.** Novelty is estimated relative to the KG and
   literature corpus (`08`), never to the agent's *memory*.

## 6. Priority & Trade-off Rules

When principles conflict, the resolution order (highest priority first):

1. **P2** there is a hard budget.
2. **P3** and **P5** reproducibility + statistical gates.
3. **P8** governance gates are not suspendable by any module including the
   orchestrator.
4. **P1** discovery rate ascends over elegance.
5. **P7** orchestration ownership ascends over concurrency shortcuts.

These are **not normative; the top five and the trade-off order are
non-negotiable.** Change requires a design-rule amendment
(`19` §9).

## 8. How Principles Are Enforced

- **PRP-1** — Every PR must reference the principle(s) it serves.
  `(a local CI hook)`
- **PRP-2** — Architecture reviews (`19` §9) check principle compliance per
  module doc.
- **PRP-3** — The Roadmap (`22`) milestones are defined in terms of these
  principles (e.g., M2 gates the budget ledger correctness).