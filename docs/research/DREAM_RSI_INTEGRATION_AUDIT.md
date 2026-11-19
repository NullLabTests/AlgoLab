# DREAM-RSI → AlgoLab integration audit

**Audited upstream:** `google-research/dream-rsi`, commit
`8ec35bd2538220517ce1bfca4282db21b8c518db` (shallow clone at
`/tmp/opencode/dream-rsi`, outside the AlgoLab source tree).
**Audit date:** 2026-11-19. **Auditor:** implementation agent, Phase 1 of the
master mission. This document records source-level findings, not README claims.

## 1. Architecture comparison

| Concern | DREAM-RSI | AlgoLab (this checkout) | Integration decision |
|---|---|---|---|
| Discovery tree | filesystem `NodeStore` (`explore_b<B>/attempt_<AA>/meta.json`), flat parent ids; `export_graph()` emits nodes+edges | append-only SQLite entities + event store, hash-sealed artifacts, lineage queries | **C** — AlgoLab persistence is the authority; no second tree store |
| Frozen replay world | `env/trace/raw.py`: `CellRaw`, `RawNode`, `RawTrace` (schema v1), `raw_scores.json` | checksummed JSON bundle + `append-only` tables | **B → rewritten** as content-addressed `DiscoveryTrace` in `algolab.meta_search.traces` |
| Replay env | `env/trace_env.py` `TraceEnv`: prefix-only `probe`/`probe_batch`, budget/round bookkeeping | none | **B** — `meta_search.replay.ReplayEnv` keeps prefix-only decisions + explicit uncertainty, drops agent/live half |
| Observation type | `Observation` (score, valid, fail_class, deltas) | `Attempt`, `Evidence`, `SelectionRecord` | **C** — new minimal `Observation` avoids coupling to agent traces |
| Policy | Python module `OptimalPolicy(LLMDesignedMethod)`, rewritten by an agent | versioned, deterministic policy classes in `algolab.search.policies` | **C** — structured frozen `SearchPolicy`, no self-modifying code |
| Policy rewrite loop | `learning/heuristic_search/workflow.py` (agent writes one editable file) | none; MASTER_SPEC §13 requires versioned, shadow-tested proposals | **C** — `propose_policy()` produces reviewable config changes; LLM optional, not required |
| Evaluation | `heuristic_search/eval.py`: `_trace_auc`, `_pareto_summary`, reward = `auc - λ·parallel_penalty`, beta sweep | `statistics.py` (bootstrap CI, Welch, Cohen's d, BH-FDR), `PolicyComparison` | **C** — reuse AlgoLab statistics; keep DREAM-RSI's *qualification-before-selection* idea |
| Promotion | `_qualification_reason` + `_select_best_round` + sha256 check; incumbent stays if not beaten | governance gates, promotion bar ≥2 families | **B/C** — fail-closed 4-stage gate in `meta_search.evaluation.promote` |
| Trace pool | `learning/trace_pool.py` directory of frozen traces + manifest | artifact store | **C** — append traces to the existing artifact store; no parallel pool |
| Orchestration | `orchestrate.py` explore→learning→promote cycles, archive/reset | CLI + sealed `search-run` bundles | **C** — one CLI command (`meta-search-run`) writes one sealed bundle |
| Agents/LLM | Gemini/Codex/Claude backends, 273-line proposer prompt | LLM adapter default off (M3) | **D** — not imported; core works without paid APIs |
| Tasks | KernelBench + SimpleTES (AGPL-3.0 fetched tasks) | toy / hpo / s2 / transform / compose substrates | **D** — use AlgoLab's CPU-friendly toy substrate |

## 2. Components examined (source level)

Files inspected (all under `/tmp/opencode/dream-rsi/`):

- `dream_rsi/env/types.py` — `CellMeta`, `Observation`, `SearchEnv` protocol.
- `dream_rsi/env/trace_env.py` — `TraceEnv`, replay/live probe semantics,
  `execution_trace()`, cost model, `_reveal`.
- `dream_rsi/env/trace/{types,raw,export}.py` — `Node`, `Trace`, `CellRaw`,
  `RawNode`, `RawTrace`, `raw_trace_to_trace`, zombie/failure classification.
- `dream_rsi/env/{observation,runner,trace_store}.py`, `env/runner.py`.
- `dream_rsi/exploration/store.py` — `NodeStore`, `export_graph`.
- `dream_rsi/learning/trace_pool.py` — frozen trace pool + manifest.
- `dream_rsi/policy/{api,baseline,load,grid_planning,observation_signal,constants}.py`
  — `LLMDesignedMethod`, `SimResult`, `GridPlan`, `ParallelRefineMethod`,
  `resolve_grid_plan`, pure observation signal helpers.
- `dream_rsi/learning/discover.py` — offline discovery driver / baseline
  benchmark (deliberately hides the grid ceiling from the proposer).
- `dream_rsi/learning/heuristic_search/eval.py` — `_resolve_target`,
  `evaluate_on_trace`, `evaluate_multi_trace`, `_trace_auc`, `_pareto_summary`,
  `run_beta_sweep`; reward = attainment AUC minus parallelism penalty.
- `dream_rsi/learning/heuristic_search/workflow.py` — proposal/eval/archive
  rounds, `_qualification_reason`, `_select_best_round`, `promote_best_round`.
- `dream_rsi/orchestrate.py` — stages, `write_live_cycle_manifest` (schema 2,
  policy sha256), `_discover_ok`, cycle archiving.
- `dream_rsi/agents/*`, `dream_rsi/prompts/*`, `dream_rsi/learning/directions/*`,
  `tests/test_*.py`, `pyproject.toml`, `LICENSE`.

Notable source-level corrections to the README: there is **no** `DiscoverEnv`
class; no policy-pool abstraction; no bandit/UCB sampler (selection is a
deterministic argmax over a qualified reward). Code defaults are 2 branches ×
2 refinements, and the default agent in code is `claude` (proposer backend
`codex`), while the README's "gemini default" applies only to launch scripts.

## 3. Reuse classification

| Component (upstream file / function) | Class | Dependencies | License | AlgoLab equivalent | Proposed integration | Benefit | Tests |
|---|---|---|---|---|---|---|---|
| `env/trace/raw.py` schema + `raw_trace_to_trace` | B (rewritten) | stdlib only | Apache-2.0 | event store, artifact checksums | `meta_search/traces.py`: `TraceNode`, `DiscoveryTrace`, canonical JSON + sha256 chain | durable, attributable histories | `TestTraceInfrastructure` |
| `env/trace_env.py` replay half (`legal_actions`, `_reveal`, prefix-only probing, cost accounting) | B | `NodeStore`, `TraceStore`, agents | Apache-2.0 | none | `meta_search/replay.py`: `ReplayEnv`, outcome-kind enum, no manufactured labels | evaluate alternative policies without fabrication | `TestReplay` |
| `policy/api.py` (`SimResult`, `LLMDesignedMethod`, `GridPlan`) + `grid_planning.resolve_grid_plan` | C | stdlib | Apache-2.0 | `search/policies.py` | frozen structured `SearchPolicy` + 4 deterministic presets + `propose_policy()` | reviewable, versioned, no paid API | `TestPolicies` |
| `heuristic_search/eval.py` `_qualification_reason`, `_pareto_summary` reward idea | B/C | numpy-free math, result dicts | Apache-2.0 | `statistics.py`, `PolicyComparison` | 4-stage fail-closed `evaluate_policy`/`promote` | prevents replay-only or overfit promotion | `TestPromotion` |
| `trace_pool.py` + `orchestrate.write_live_cycle_manifest` (sha256 provenance) | C | filesystem | Apache-2.0 | artifact store, sealed bundles | sealed `protocol-241-v1` bundle + `verify_pilot()` | independent verification / reproducibility | `TestPilotAndVerification` |
| `exploration/store.py` `NodeStore`, workspace tree | D | filesystem, agent dirs | Apache-2.0 | repositories, event store | not imported | — | — |
| `learning/heuristic_search/workflow.py` agent rewriter, `agents/*`, prompts | D | paid-model SDKs, subprocesses | Apache-2.0 / MIT vendored | LLM adapter default-off | not imported (optional LLM may be layered later) | — | — |
| KernelBench / SimpleTES tasks | D | external, AGPL-3.0 fetched | MIT / AGPL-3.0 | toy/hpo/transform/compose | not imported | — | — |

## 4. Dependency and licensing audit

- Upstream root license: **Apache License 2.0** (`/tmp/opencode/dream-rsi/LICENSE`).
  Per-file headers: `Copyright 2026 Google LLC`. No `NOTICE` file. Vendored
  `third_party/kernelbench/LICENSE` is MIT (Stanford Scaling Intelligence Lab);
  fetched SimpleTES tasks are AGPL-3.0 and not present in this checkout.
- Upstream runtime dependencies: none in the base install; optional extras add
  numpy/scipy/psutil/scikit-learn, requests/pyyaml, model SDKs, pytest. All are
  already available in AlgoLab (sklearn) or deliberately excluded (model SDKs).
  **No new dependency is introduced by this integration.**
- Decision: **no upstream source code was copied.** Only architectural ideas
  were reimplemented in AlgoLab-native modules, so Apache §4 copying
  obligations do not attach; attribution is nonetheless recorded here and in
  `THIRD_PARTY_NOTICES.md`, together with the Apache-2.0 license text location.
  Nothing from `third_party/` or fetched AGPL tasks was touched.
