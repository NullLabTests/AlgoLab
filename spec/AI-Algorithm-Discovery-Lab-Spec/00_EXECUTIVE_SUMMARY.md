# 00 EXECUTIVE SUMMARY

- **Status:** v1.0 — Complete specification
- **Document version:** 1.0.0
- **Supersedes:** scaffold placeholders
- **Read with:** `README.md` (index + glossary), `22_ROADMAP.md` (phased build plan)

---

## 1. Purpose

This repository is the complete engineering specification for **AlgoLaB** — an
Autonomous AI Algorithm Discovery Laboratory. AlgoLaB is a multi-agent research
system that continuously proposes, implements, benchmarks, analyzes, and
evolves candidate machine-learning algorithms under a **fixed, auditable
compute budget**. Its output is not code that runs a single experiment; it is a
*discovery engine* that maximizes the scientific discovery rate of algorithmic
research.

This is a **specification repository only**. No production code is implemented
here. Every module is specified to the level of detail required for an
autonomous coding agent (e.g., OpenCode) to implement it module by module:
interfaces, data schemas, algorithms, pseudocode, failure modes, acceptance
tests, and milestones.

## 2. The Mission in One Sentence

> Maximize the scientific discovery rate in AI algorithm research by
> iteratively proposing, implementing, benchmarking, analyzing, and evolving
> candidate algorithms under a fixed compute budget.

## 3. What AlgoLaB Is and Is Not

| Is | Is Not |
|---|---|
| A disciplined research platform | A "singularity machine" |
| A hypothesis factory with statistical gates | An unbounded creative prompt |
| A rediscovery-capable baseline harness | A guarantee of paradigm-shifting invention |
| A reproducible, lineage-tracked experiment registry | A one-off experiment runner |
| A compute-budget optimizer | An unlimited-compute explorer |
| A system that can recombine ideas in novel ways | A system that reliably invents fundamentally new paradigms |

A realistic expectation: AlgoLaB will **generate and test many ideas, rediscover
known techniques, combine existing ideas in novel ways, find engineering
improvements, and occasionally uncover genuinely interesting new approaches**.
Fundamentally new paradigms are rare and no known recipe reliably produces
them; the value of the system is that it **dramatically increases the rate at
which hypotheses are generated and evaluated**.

## 4. System at a Glance

```mermaid
flowchart LR
    subgraph KNOWLEDGE["Knowledge Plane"]
        KG[("Knowledge Graph\n(05)")]
        DDB[("Discovery Database\n(16)")]
    end

    LM[Literature Miner\n(06)] --> KG
    HE[Hypothesis Engine\n(07)] --> NE[Novelty Estimator\n(08)]
    AG[Architecture Generator\n(09)] --> NE
    ME[Mutation Engine\n(10)] --> NE
    ES[Evolutionary Search\n(11)] --> NE
    NE --> EP[Experiment Planner\n(12)]
    EP --> TP[Training Pipeline\n(13)]
    TP --> BH[Benchmark Suite\n(14)]
    BH --> SA[Statistical Analysis\n(15)]
    SA --> DDB
    SA --> ES
    SA --> PG[Paper Generator\n(17)]
    ES --> HE
    DDB --> HE
    DDB --> ES
    DDB --> SI[Self-Improvement\n(18)]
    GV[Governance\n(19)] -.gates.-> EP
    GV -.gates.-> PG
    SI -.meta-controls.-> HE
    SI -.meta-controls.-> EP
```

The central loop: **Observe → Hypothesize → Vet → Plan → Execute → Analyze →
Learn → Report** (detailed in `03_SYSTEM_ARCHITECTURE.md` §6).

## 5. Architecture at a Glance

- **23 modules** (`00`–`22`), each a standalone specification with interfaces,
  schemas, algorithms, failure modes, and acceptance tests.
- **One orchestrator** controlling the research loop; specialized agents for
  each stage (`04_AGENT_HIERARCHY.md`).
- **Two persistent stores**: a Knowledge Graph (`05`) for literature/method
  relationships, and a Discovery Database (`16`) for experiments, runs,
  metrics, budget, lineage, and events.
- **Asynchronous event bus** connecting all modules; every action is an event,
  every event is logged, every decision is traceable.
- **Compute credits** as the universal currency: 1 credit = 1 A100-80GB
  GPU-hour. All planning, accounting, and reporting is credit-denominated.

## 6. Key Quantitative Targets (KPIs)

Defined in full in `02_RESEARCH_MISSION.md` §4. Headline numbers:

| KPI | Target (steady state, post-M2) |
|---|---|
| Discoveries per 1,000 compute credits | ≥ 1 |
| Hypothesis → discovery conversion rate | ≥ 0.5% |
| Median compute per tested hypothesis | ≤ 10 credits |
| Rediscovery rate (known-method recall) | ≥ 25% of a held-out known-method set |
| Run success rate (no operator error) | ≥ 95% |
| Experiments in parallel | ≥ 8 |
| Full research loop cycle time | ≤ 7 days |
| Compute spent on unplanned/debug work | ≤ 10% of budget |

## 7. Discovery Definition (abbreviated)

A **Discovery** is a candidate that passes all of the following (full
definition in `02_RESEARCH_MISSION.md` §5):

1. **Improvement**: ≥ 1% relative gain over the best baseline on ≥ 1 primary
   benchmark (Tier B), or ≥ 5% on ≥ 1 / ≥ 1% on ≥ 3 benchmarks (Tier A).
2. **Significance**: p < 0.05 after multiple-comparison correction, ≥ 3 seeds,
   bootstrap 95% CI excluding zero.
3. **Compute fairness**: compute-normalized gain ≥ 80% of raw gain.
4. **Reproducibility**: config-hash-pinned rerun matches.
5. **Attribution**: ablations explain ≥ 50% of the gain.
6. **Safety**: passes all governance gates (`19_GOVERNANCE.md`).

## 8. Notable Design Decisions

1. **Compute budget is the primary currency** — every experiment is priced
   before it runs, and the budget ledger is authoritative (`12`).
2. **Statistical rigor is a gate, not an afterthought** — no result is declared
   a discovery without power analysis, multiple-comparison correction, and
   seed replication (`15`).
3. **Rediscovery is a capability signal, not a failure** — a lab that
   re-discovers AdamW from scratch is measurably learning; the capability
   ladder is scored (`02` §6).
4. **Human oversight by default, autonomy by exception** — governance gates
   relax only when the lab demonstrates trustworthy behavior over sustained
   operation (`19`).
5. **Everything is lineage-tracked** — every candidate knows its parents,
   mutations, runs, and downstream impact; nothing is orphaned (`16`).
6. **Self-improvement is gated and A/B tested** — the lab can tune its own
   search strategy, but every meta-change must beat its predecessor
   statistically (`18`).

## 9. Risk Statement

The primary risks and their mitigations are catalogued in `21_FAILURE_MODES.md`.
Top-level risks: runaway compute consumption (mitigated by hard budget ledger
and kill switch), statistical false positives (mitigated by correction and
replication gates), drift into unproductive search directions (mitigated by
stagnation detection and extinction), code bugs masquerading as discoveries
(mitigated by scaffold verification and config hashing), and model
hallucination in generated papers (mitigated by claim→evidence linking).

## 10. Reading Guide

- **Start here** → `README.md`, `01_DESIGN_PRINCIPLES.md`, `02_RESEARCH_MISSION.md`.
- **Understand the whole system** → `03_SYSTEM_ARCHITECTURE.md`, `04_AGENT_HIERARCHY.md`.
- **Understand the data** → `16_DISCOVERY_DATABASE.md`, `05_KNOWLEDGE_GRAPH.md`.
- **Understand a module** → read its numbered doc plus `21_FAILURE_MODES.md`
  entries that reference it.
- **Build the system** → `22_ROADMAP.md` (phases M0–M5, each with acceptance
  tests) and `20_DEPLOYMENT.md` for the operational environment.

## 11. Document Conventions

- Module references use the form **`NN_MODULE_NAME.md` §X** (e.g., `16_DISCOVERY_DATABASE.md` §5).
- Pseudocode is executable-by-inspection pseudocode, not a language mandate.
- Every interface and schema is normative: implementers must not deviate
  without a change request documented in `19_GOVERNANCE.md` §9.
- All timestamps are ISO 8601 UTC; all identifiers follow `16_DISCOVERY_DATABASE.md` §3.
