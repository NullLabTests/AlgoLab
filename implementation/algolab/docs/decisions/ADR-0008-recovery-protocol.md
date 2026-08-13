# ADR-0008 — Recovery protocol

- **Status:** Accepted
- **Date:** 2026-08-03

## Context

`MASTER_SPEC.md` §14 requires the system to keep functioning after worker
crashes and node loss. Lease expiration alone (ADR-0006) leaves runs in an
inconsistent-looking state: `CLAIMED`/`RUNNING` rows with no live worker,
possibly with complete artifacts already sealed. Recovery must reconcile
these without race conditions and without violating the append-only audit
invariant.

## Decision

- **Reconciliation as an explicit, idempotent pass.** A recovery sweep
  examines the run set in transactions; every action it takes is guarded
  by the run state machine and emits audit events. The sweep is safe to run
  concurrently with workers because transitions are transactional.
- **Live leases are skipped.** Only `CLAIMED` runs with
  `lease_expires_at < now` (or whose heartbeat is stale) are orphans.
- **Verify-then-complete.** An orphan whose artifact manifest verifies
  (ADR-0007) is completed `ORPHANED -> SUCCEEDED` and its reservation is
  charged — a worker that died after sealing still counts its evidence.
- **Requeue with backoff and attempt limits.** Otherwise the orphan becomes
  `QUEUED` again with a fresh reservation, an incremented
  `attempt_number`, and `next_eligible_at = now + backoff`; at
  `max_attempts` it is failed with `ATTEMPTS_EXHAUSTED`.
- **Budget reconciliation:** orphan releases the previous reservation;
  verified completion charges reported credits (partial → release
  remainder); requeue creates a new reservation.
- **Run/worker lease race handling:** a run in `STARTING`/`RUNNING` with a
  live lease is left alone; a worker whose heartbeat keeps winning never
  collides with recovery because lease expiry is the single point of
  hand-off.
- **Cancellation** is implemented in the worker + request layer, never in
  the recovery sweep.

## Consequences

- Crashes at any point (before prepare, during run, after seal) converge to
  a terminal, consistent state without operator intervention.
- Recovery is cheap and composable; it can run from the CLI or embedded in
  worker startup.
- The cost is a small set of transition rules (`ORPHANED -> {QUEUED,
  FAILED, SUCCEEDED}`) that are tightly tested in `tests/test_recovery.py`.