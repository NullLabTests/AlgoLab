# ADR-0006 — Persistent queue and leases

- **Status:** Accepted
- **Date:** 2026-08-03

## Context

`MASTER_SPEC.md` §9 requires a durable run queue with claiming semantics
such that any worker can pick up queued runs, and a crashed worker cannot
permanently strand a run it claimed. M1 has no broker; the run set already
lives in SQLite, and the append-only audit requirement (§14) means every
queue mutation must be recorded.

## Decision

- **The run set is the queue.** No separate queue table or external broker:
  `runs` rows carry `status`, `priority`, `next_eligible_at`,
  `attempt_number`, and `max_attempts`; eligibility is a SQL predicate.
  `claim_next(worker_id)` atomically moves the best
  `QUEUED -> CLAIMED` row (highest priority, then FIFO) and stamps
  `lease_expires_at = now + lease_seconds`.
- **Leases are optimistic and heartbeated.** `lease_seconds` bounds a claim;
  the owning worker refreshes the lease every
  `heartbeat_interval_seconds`. A claim by a different worker fails
  (`CLAIM_CONFLICT`); heartbeats for a run owned by another worker are
  ignored.
- **Cancellation is cooperative:** queued runs cancel immediately;
  claimed/running runs are flagged `CANCEL_REQUESTED` and aborted by the
  owner at the next poll.
- **Backoff is enforced in the predicate:** requeued runs set
  `next_eligible_at` in the future and cannot be claimed before it.
- **Concurrency guards:** transitions, claims, heartbeats, and
  cancellations run in transactions with `PRAGMA busy_timeout`; a worker
  that loses the claim race simply fails and moves on. One worker process
  is assumed per node in M1 (no inter-worker coordination protocol yet).

## Consequences

- Zero infrastructure: the queue survives restarts with the database, and
  every mutation is audited in the same transaction.
- Crash safety is delegated to leases + recovery (ADR-0008): a dead worker's
  runs become orphans after the lease expires.
- `claim_next` needs care with transaction boundaries (a claim must be
  committed before the worker starts heartbeating); enforced by tests with
  concurrent connections.
