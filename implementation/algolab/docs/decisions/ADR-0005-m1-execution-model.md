# ADR-0005 — M1 execution model

- **Status:** Accepted
- **Date:** 2026-08-03

## Context

`MASTER_SPEC.md` §9 requires a planner that turns an approved experiment into
runs, per-seed candidates with declared config changes, budget reservation,
and deterministic outcomes. The system has no compute cluster and no message
broker in M1; it runs on a single node with SQLite storage.

## Decision

- **Plan-per-experiment, runs-per-cell:** expansion of an approved experiment
  creates one baseline run per seed plus one candidate run per
  (candidate × seed); each run's resolved config = adapter defaults + the
  candidate's declared changes.
- **Content-addressed fingerprints:** every run is identified for dedup by
  sha256 of `experiment_id + workload + resolved config + seed +
  is_baseline` (canonical sorted-key JSON), not by any human key.
- **Idempotent expansion:** re-running expansion with the same idempotency
  key is a no-op; a different key whose fingerprints already exist reuses the
  existing runs and never duplicates them.
- **All-or-nothing planning:** if any step fails — status gate, fingerprint
  planning, budget estimation, or reservation — nothing is persisted.
- **Execution via isolated subprocess:** the worker launches the workload
  adapter's argv in a fresh subprocess with cwd = run directory and an
  allowlisted environment; no in-process execution of third-party code.
- **Determinism as a requirement:** repeated runs of the same experiment in
  fresh projects must produce identical metrics and logs (enforced by tests).

## Consequences

- Planning and dedup are simple, auditable, and crash-safe (no partial
  expansion states possible).
- The budget ledger is the single reservation point; expansion cannot
  overspend even if estimates are off.
- Isolation costs a process spawn per run, acceptable for M1's
  second-scale workloads.
- Fingerprint stability becomes part of the contract: any change to
  defaults, change-merging, or seed handling changes the fingerprint and
  therefore (deliberately) re-plans runs.
