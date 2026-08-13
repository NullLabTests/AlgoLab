# Recovery

- **Related ADR:** ADR-0008
- **Scope:** M1 recovery of orphaned runs, abandoned reservations, and
  interrupted execution states. Runs the CLI `recover` command (or the
  worker's startup sweep).

## What can go wrong

| failure | observable state | recovery action |
| --- | --- | --- |
| worker killed mid-run | `CLAIMED`/`STARTING`/`RUNNING`, lease expired | reclaim via recovery |
| worker killed while running | `RUNNING`, lease still live | skip (worker may be alive); heartbeat refreshes lease |
| node lost | lease expires, no heartbeat | same as first row |
| worker crashes after completing | artifacts sealed, `CLAIMED`, lease expired | verify artifacts → `SUCCEEDED` (verified) |
| reservation abandoned | `reservation active`, run no longer active | release reservation |
| repeated failures | `ORPHANED`, attempts exhausted | `FAILED` with `ATTEMPTS_EXHAUSTED` |

## The recovery pass

For each run the recovery pass examines:

1. **Live leases are skipped.** A run in `CLAIMED`/`STARTING`/`RUNNING`
   whose lease is not expired is left alone — its worker may be mid-step.
   (Recovery also never races the worker: transitions are transactional and
   guarded by the run state machine, so a claim wins exactly once.)
2. **Orphan detection.** `CLAIMED` runs with
   `lease_expires_at < now` are moved `CLAIMED -> ORPHANED` with
   `error_code=LEASE_EXPIRED`. The run's reservation is **released** here.
3. **Verified completion.** If the run directory exists and
   `artifact_manifest.json` verifies (every file re-hashed, run id matches),
   the run is completed `ORPHANED -> SUCCEEDED` and the reservation is
   re-charged for the reported credits. This is how a worker that died after
   sealing artifacts still counts its run as successful.
4. **Requeue.** Otherwise, if `attempt_number < max_attempts`, the run is
   re-queued `ORPHANED -> QUEUED` with `attempt_number + 1` and
   `next_eligible_at = now + requeue_backoff_seconds`, and a **new**
   reservation is created for the requeued attempt (the old one was
   released). The queue refuses to hand out a requeued run before its
   backoff window.
5. **Exhaustion.** If attempts are exhausted, the run is failed
   `ORPHANED -> FAILED` with `ATTEMPTS_EXHAUSTED`.
6. **Abandoned reservations.** Any `active` reservation whose run is not in
   a live state (`QUEUED`, `CLAIMED`, `STARTING`, `RUNNING`) is released.

Every step appends an audit event and commits atomically; a crash between
steps is harmless because each step is idempotent.

## Reconciliation with the budget

- Orphan release: `release` entry (idempotency key per reservation).
- Verified completion: `charge` entry for the credits in `completion.json`
  (a partial charge releases the remainder).
- Requeue: a fresh `reserve` entry for the new attempt; the old reservation
  stays released.

## Cancellation

Cancellation is part of the same model: `request_cancellation` marks a
`QUEUED` run `CANCELLED` immediately (reservation released); for
`CLAIMED`/`RUNNING` runs it sets `CANCEL_REQUESTED` and the owning worker
aborts at the next poll (outcome `CANCELLED`). Recovery never cancels live
runs.

## Invariants guaranteed after a pass

1. No run is in `CLAIMED` with an expired lease.
2. No active reservation points at a run that is not live.
3. `attempt_number <= max_attempts`; runs at the cap are terminal.
4. Verified artifacts are never re-executed: `ORPHANED -> SUCCEEDED` is the
   only way an orphaned run ends, and it requires intact hashes.
5. Audit events exist for every mutation performed by recovery.

## Configuration

`recovery.requeue_backoff_seconds` (default `5.0`) controls the backoff
window before a requeued attempt becomes eligible. `execution.max_attempts`
(default `2`) caps attempts per run. See `configs/algolab.yaml`.

## Testing

`tests/test_recovery.py` covers: orphan detection, verified-artifact
completion, tampered-artifact requeue, attempts exhaustion, reservation
release, live-lease skipping, and audit-event emission. `tests/test_queue.py`
covers the requeue backoff window and claim semantics.
