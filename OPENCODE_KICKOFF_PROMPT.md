# OpenCode Kickoff Prompt

Read the entire repository before changing files.

You are implementing AlgoLab v1 from the canonical `MASTER_SPEC.md`. The
existing archived scaffold under the user's earlier `spec/` directory is
historical and must not override this master specification.

## Immediate mission

Implement **Milestone M0 only** from `planning/MILESTONES.md`.

Do not implement LLM agents, evolutionary search, distributed execution,
automatic publication, or self-improvement yet.

## Required actions

1. Create a new implementation directory named `implementation/algolab`.
2. Copy or reference the canonical JSON schemas without changing their meaning.
3. Produce `implementation/algolab/PLAN.md` containing:
   - architecture decisions;
   - exact files to create;
   - dependency choices;
   - risks;
   - acceptance-test mapping.
4. Implement:
   - Python package layout;
   - typed ID helpers;
   - entity models;
   - lifecycle state machine;
   - append-only SQLite event store;
   - budget ledger;
   - JSON-schema validation;
   - configuration loading;
   - CLI commands for initializing the database and validating manifests.
5. Add tests for every invariant in `spec/foundation/001_CORE_ONTOLOGY.md`.
6. Add CI configuration and a reproducible local setup command.
7. Do not claim completion until all M0 acceptance tests pass.
8. Do not delete or rewrite `planning/initial_analysis.md`.
9. Keep commits small and record decisions in
   `implementation/algolab/docs/decisions/`.
10. Stop after M0 and produce `M0_COMPLETION_REPORT.md` with test output,
    remaining risks, and exact commands for the operator.

## Engineering constraints

- Python 3.11 or newer.
- Prefer standard library and small dependencies.
- Use SQLite for M0.
- Use Pydantic for runtime models and JSON Schema for interchange contracts.
- Use pytest, ruff, and mypy.
- No network calls in tests.
- No credentials.
- No background infinite loops.
- No destructive shell commands.
- No code generation outside the repository.
- Every mutation of state must append an audit event.
- Invalid state transitions must fail closed.

Begin by writing `PLAN.md`, then implement M0, run tests, repair failures, and
stop only after writing the completion report.
