# ADR-0007 — Artifact store

- **Status:** Accepted
- **Date:** 2026-08-03

## Context

`MASTER_SPEC.md` §9 requires every run to produce a reproducible artifact
set; §14 requires an immutable, auditable record. The worker may be killed
at any point, so artifacts must be verifiable without trusting the worker's
memory. Recovery (ADR-0008) needs to distinguish "run truly succeeded and
its evidence is intact" from "run was interrupted before finishing".

## Decision

- **Per-run directory, write-once files.** Each run owns
  `<artifacts_dir>/runs/<RUN_ID>/`. The worker writes
  `manifest.json`, `resolved_config.json`, and `environment.json` *before*
  execution; `stdout.log`/`stderr.log`/`resource_usage.json` during/after;
  the workload itself writes `metrics.json`.
- **Hash sealing.** `artifact_manifest.json` is written **last** and records
  a sha256 per file. After that, the directory is frozen:
  `verify()` re-hashes every file and only intact sets are trusted.
- **`completion.json` is the terminal record:** status, error code, exit
  code, start/finish times, final credits and cost, and reservation id —
  written only after the manifest.
- **Config is pinned before execution.** The workload never reads
  configuration from the live project; it reads `resolved_config.json`
  written next to it, so artifacts are self-contained evidence of what
  actually ran (canonical sorted-key JSON → byte-identical outputs).
- **Hard size caps.** stdout/stderr/total artifact size are capped by
  configuration; violations fail the run rather than unbounded disk usage.
- **Environment snapshot.** `environment.json` pins interpreter, platform,
  sqlite version, workload version, and the allowlisted environment so a
  run can be reproduced even if the node changes.

## Consequences

- Artifacts are tamper-evident: any modification or truncation breaks the
  manifest hashes and recovery treats the run as incomplete.
- Reproduction is possible from the artifact directory alone.
- Disk cost is bounded by the size caps; large artifacts are a
  post-M1 concern (object storage).
