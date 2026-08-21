# Initial Architectural Analysis — AlgoLaB

> **STATUS:** Checkpoint/archive of pre-specification analysis.
> Written before the master specification arrives. The scaffold docs (`00`–`22`)
> are **not** to be edited again until the new, substantially expanded master
> specification replaces them. This file records the analysis performed so far
> so that no decisions are lost during the wait.

- Archive date: 2026-08-03
- Source context: `Highest Leverage Activity.html` (ChatGPT conversation that
  generated the scaffold) + reading all 24 scaffold markdown files.
- Author: analysis pass (not the implementer).

---

## 1. Context Recovered From the Conversation HTML

The scaffold was produced from a ChatGPT discussion. The important intent:

1. The system is an **Autonomous AI Algorithm Discovery Laboratory**.
2. Recommended mission wording (verbatim):
   > "Maximize scientific discovery rate in AI algorithm research by iteratively
   > proposing, implementing, benchmarking, analyzing, and evolving candidate
   > algorithms under a fixed compute budget."
3. The user asked **not** for an unconstrained "invent the next AI paradigm"
   prompt, but for a *disciplined research platform*.
4. Realistic expectations the author explicitly flagged in the conversation:
   - Will generate and test many ideas,
   - Will rediscover known techniques,
   - Will combine existing ideas in novel ways,
   - Will find engineering improvements,
   - Will occasionally uncover genuinely interesting new approaches,
   - Is **not guaranteed** to invent a fundamentally new paradigm.
5. The original document list intended each file to contain:
   requirements, algorithms, interfaces, pseudocode, success criteria,
   testing strategies, implementation notes.

### 6. Conversation-implied scope topics

- Multi-agent architecture
- Directory structure
- Task orchestration
- Autonomous research loop
- Experiment scheduler
- Benchmark harness
- Literature mining
- Evolutionary search
- Theorem/id generation
- Paper writing
- GitHub/CI automation
- Long-term memory
- Self-critique
- Distributed execution
- Continuous operation

---

## 3. Inventory of the Scaffold Repo (as delivered)

24 Markdown files, every one a 3–5 line placeholder:

```
README.md
00_EXECUTIVE_SUMMARY.md
01_DESIGN_PRINCIPLES.md
02_RESEARCH_MISSION.md
03_SYSTEM_ARCHITECTURE.md
04_AGENT_HIERARCHY.md
05_KNOWLEDGE_GRAPH.md
06_LITERATURE_MINER.md
07_HYPOTHESIS_ENGINE.md
08_NOVELTY_ESTIMATOR.md
09_ARCHITECTURE_GENERATOR.md
10_MUTATION_ENGINE.md
11_EVOLUTIONARY_SEARCH.md
12_EXPERIMENT_PLANNER.md
13_TRAINING_PIPELINE.md
14_BENCHMARK_SUITE.md
15_STATISTICAL_ANALYSIS.md
16_DISCOVERY_DATABASE.md
17_PAPER_GENERATOR.md
18_SELF_IMPROVEMENT.md
19_GOVERNANCE.md
20_DEPLOYMENT.md
21_FAILURE_MODES.md
22_ROADMAP.md
```

Delivery artifact: `AI-Algorithm-Discovery-Lab-Spec-Scaffold.zip` (unzipped to
`spec/AI-Algorithm-Discovery-Lab-Spec/`).

---

## 4. Draft Architectural Decisions (Provisional — for the new spec)

These were my working decisions for the abandoned draft. Keep or revise them
when the new master spec replaces the scaffold. **None of this is fixed policy
until the new spec says so.**

### 4.1 System identity
- System name: **AlgoLaB** (from the repo folder name).
- Version scheme: spec v1.x, modules numbered `00`–`22`.

### 4.2 Design principles derived (short list)
- Discovery rate = the objective; breakthroughs are rare, not scheduled.
- Compute is the primary, hard currency (a fixed budget is non-negotiable).
- Reproducibility is a hard precondition (config-hash-pinned runs).
- Hypothesis-driven search: every candidate is attached to a falsifiable
  hypothesis with mechanism, predicted effect, and failure modes.
- Statistical rigor gates all claims (power analysis, multiple-comparison
  correction, seed replication).
- Lineage/provenance for all artifacts; no free-form "agent memory" as truth.
- Human oversight by default; autonomy by exception (governance levels L0–L2).
- Fail loud, fail early, with a structured failure code.
- Everything versioned, nothing overwritten.
- Simple typed interfaces between modules; complex internals are private.
- Resilience: no single non-fatal failure halts the loop.

### 4.3 The Research Loop (canonical)
Observe → Hypothesize → Vet → Plan → Execute → Analyze → Learn → Report.
Stages map to modules: LM(`06`), HE(`07`), NE(`08`), AG(`09`), ME(`10`),
ES(`11`), EP(`12`), TP(`13`), BH(`14`), SA(`15`), PG(`17`), SI(`18`).

### 4.4 Candidate lifecycle (normative state machine)
```
DRAFT → VETTING → PLANNED → READY → RUNNING → ANALYZED →
        ACCEPTED|REJECTED|ARCHIVED ; ACCEPTED ⇄ DISCOVERY
```

### 4.5 Discovery taxonomy (draft)
- **Tier A** — Major: ≥5% relative gain on ≥1 primary benchmark OR ≥1% on ≥3.
- **Tier B** — Minor: ≥1% on ≥1 primary benchmark.
- **Tier C** — Engineering: ≥30% compute/latency/memory reduction at parity, or
  correctness/reproducibility fix.
- Six gates: G1 improvement, G2 significance (p<0.05, CI excludes 0, ≥3 seeds,
  BH correction), G3 compute-fairness (normalized gain ≥80% of raw), 
  G4 reproducibility (config-hash rerun), G5 attribution (ablations ≥50%),
  G6 safety/governance.
- Negative results are first-class artifacts (feed priors, papers).

### 4.6 Key metrics/targets (draft)
- ≥1 discovery per 1000 compute credits
- ≥0.5% hypothesis→discovery conversion
- ≤10 credits median compute per tested hypothesis
- ≥95% run success rate
- Rediscovery rate ≥25% of a "canonical known-method set" (CKMS):
  e.g. AdamW, GELU, EMA, warmup schedules.
- ≤10% of budget spent on unplanned/debug work.

### 4.7 Compute credit model (draft)
- 1 credit = 1 A100-80GB GPU-hour; normalization factors for H100, V100, CPU.
- Budget ledger is authoritative, append-only; planning freezes when it
  exhausts.

### 4.8 Identifiers (draft)
- `CAND-*, HYP-*, EXP-*, RUN-*, DISC-*, PAP-*, EVT-*, TRC-*`
- All ISO 8601 UTC; sha256 config hashes; trace_id propagates full lineage.

### 4.9 Event bus (draft)
- Redis Streams (prod: Kafka), durable consumer groups, at-least-once +
  idempotent handlers.
- Canonical topics list defined (see full list on the analysis draft):
  `lab.hypothesis.created`, `lab.candidate.created`, `lab.novelty.estimated`,
  `lab.experiment.planned/approved`, `lab.run.started/completed/failed`,
  `lab.experiment.completed`, `lab.discovery.declared`, `lab.kg.updated`,
  `lab.budget.exhausted`, `lab.governance.blocked`, `lab.paper.published`,
  `lab.meta.applied`.

### 4.10 Tech stack (draft)
- Python 3.11+, PyTorch 2.x, Ray 2.x (distributed jobs), Redis Streams/Kafka,
- PostgreSQL 16 (DDB), Neo4j 5 (KG), pgvector/FAISS embeddings,
- FastAPI + Pydantic v2 control plane, YAML config single-source,
- GitHub Actions CI, Docker/K8s, Prometheus/Grafana.

### 4.11 Proposed repo layout (draft)
```
algo-lab/
├── lab.yaml
├── src/algo_lab/{core,control,agents,modules,storage,ops}
├── tests/
├── ops/
├── data/
├── notebooks/
├── papers/
└── docs/  (this spec mirrored)
```

---

## 5. Deliverables Remaining (planned but not done)

Per the draft I had written out:
- `04_AGENT_HIERARCHY.md` — agents, tiers, prompt contracts, escalation.
- `05_KNOWLEDGE_GRAPH.md` — schema, embeddings, ingestion, queries.
- `06_LITERATURE_MINER.md` — sources, pipeline, dedup, KG writes.
- `07_HYPOTHESIS_ENGINE.md` — templates, generation, priors, falsification.
- `08_NOVELTY_ESTIMATOR.md` — signals, composite score, thresholds, rediscovery.
- `09_ARCHITECTURE_GENERATOR.md` — search-space DSL, component catalog, validation.
- `10_MUTATION_ENGINE.md` — operators, provenance, validity checks.
- `11_EVOLUTIONARY_SEARCH.md` — population, fitness, Pareto, stagnation, extinction.
- `12_EXPERIMENT_PLANNER.md` — budget ledger, EIG, scheduling, bandit, priorities.
- `13_TRAINING_PIPELINE.md` — scaffold verification, hashing, retries, checkpointing.
- `14_BENCHMARK_SUITE.md` — registry, protocols, baselines, compute-normalization.
- `15_STATISTICAL_ANALYSIS.md` — pipeline, tests, corrections, power, learning curves,
  scaling laws, anomaly detection.
- `16_DISCOVERY_DATABASE.md` — full relational schema, event log, budget ledger, retention.
- `17_PAPER_GENERATOR.md` — pipeline, claim→evidence linking, review gates.
- `18_SELF_IMPROVEMENT.md` — scope, A/B meta tests, guarded rollout.
- `19_GOVERNANCE.md` — gates, autonomy levels L0–L2, kill switch, audits.
- `20_DEPLOYMENT.md` — topology, CI/CD, observability, security.
- `21_FAILURE_MODES.md` — FM-xxxx catalogue, detection, mitigation, severity.
- `22_ROADMAP.md` — phases M0–M5, milestones, acceptance, exit criteria.
- `README.md` — index, reading order, glossary.

## 6. Interim state of the spec scaffold

Files `00_EXECUTIVE_SUMMARY.md`, `01_DESIGN_PRINCIPLES.md`,
`02_RESEARCH_MISSION.md`, and `03_SYSTEM_ARCHITECTURE.md` were drafted during
the earlier pass. Per the STOP instruction, **no further edits to the scaffold
Markdown files will be made in this session**. These drafts are retained
verbatim for the implementer (they are consistent with §4 but are not final).

## 7. Next Action

Wait for the new, substantially expanded master specification. When it
arrives: replace the scaffold content per that new spec; reconcile any
naming/schema drift with this analysis; then continue the multi-pass
placeholder-elimination work.