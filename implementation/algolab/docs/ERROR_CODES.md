# Error Codes

- **Source of truth:** `src/algolab/execution/errors.py` (`ErrorCode`).
- Every failing run and every operation-level failure carries exactly one
  machine-readable code so operators and automation can branch on a stable
  enum instead of message text.

## Taxonomy

| code | meaning |
| --- | --- |
| `INVALID_TRANSITION` | A state transition was rejected by the run state machine. |
| `CLAIM_CONFLICT` | A run could not be claimed because another worker already owns it. |
| `LEASE_EXPIRED` | A worker's claim lease expired; the run is considered orphaned. |
| `TIMEOUT` | The workload exceeded its configured timeout and was terminated. |
| `CANCELLED` | The run was cancelled before completion. |
| `MANIFEST_INVALID` | A manifest failed validation against its canonical JSON schema. |
| `WORKLOAD_UNKNOWN` | No workload adapter is registered under the requested name. |
| `EXPERIMENT_NOT_APPROVED` | An experiment must be approved before it can be expanded. |
| `SUBPROCESS_FAILURE` | The workload subprocess exited with a non-zero exit code. |
| `METRICS_MISSING` | The workload did not produce a `metrics.json` file. |
| `METRICS_INVALID` | `metrics.json` failed validation against the adapter schema. |
| `ARTIFACT_MISSING` | Expected artifacts are absent or fail hash verification. |
| `ARTIFACT_LIMIT_EXCEEDED` | stdout/stderr or total artifact size exceeded configured limits. |
| `BUDGET_INSUFFICIENT` | Expansion was refused because credits or monetary caps were exceeded. |
| `RECOVERY_CONFLICT` | Recovery could not safely reconcile a run's persisted state. |
| `ATTEMPTS_EXHAUSTED` | An orphaned run exhausted its retry attempts and was failed. |
| `RUN_NOT_FOUND` | The referenced run does not exist. |
| `DATABASE_ERROR` | A database-level failure occurred (schema, integrity, connection). |

## Where each code surfaces

| code | component | context |
| --- | --- | --- |
| `INVALID_TRANSITION` | `core/state.py` | reject illegal state transitions |
| `CLAIM_CONFLICT` | `execution/queue.py` | a different worker owns the run |
| `LEASE_EXPIRED` | `execution/recovery.py` | claim lease expired → `ORPHANED` |
| `TIMEOUT` | `execution/worker.py` | subprocess exceeded timeout |
| `CANCELLED` | `execution/worker.py` | cooperative cancellation |
| `MANIFEST_INVALID` | `importers/`, CLI | rejected manifest json |
| `WORKLOAD_UNKNOWN` | `workloads/__init__.py` | unknown adapter name |
| `EXPERIMENT_NOT_APPROVED` | `execution/expansion.py` | expand of non-approved experiment |
| `SUBPROCESS_FAILURE` | `execution/worker.py` | non-zero subprocess exit |
| `METRICS_MISSING` | `execution/worker.py` | no `metrics.json` after exit 0 |
| `METRICS_INVALID` | `execution/worker.py` | adapter `validate_metrics` failed |
| `ARTIFACT_MISSING` | `execution/worker.py` | expected artifacts absent/hash-failed |
| `ARTIFACT_LIMIT_EXCEEDED` | `execution/worker.py` | capture/artifact size cap violated |
| `BUDGET_INSUFFICIENT` | `execution/expansion.py`, `control/budget.py` | reservation/expansion refused |
| `RECOVERY_CONFLICT` | `execution/recovery.py`, `execution/worker.py` | persisted state could not be reconciled |
| `ATTEMPTS_EXHAUSTED` | `execution/recovery.py` | orphaned run at max attempts |
| `RUN_NOT_FOUND` | `execution/expansion.py`, `storage` | missing run/experiment on expansion |
| `DATABASE_ERROR` | `storage/db.py` | schema, integrity, connection failures |

## Where they appear

Codes are stored in `completion.json` (`error_code`), in run rows after a
failure, in worker/recovery log events (`"error_code": ...`), and surfaced by
`aggregate-experiment` so dashboards can group failures by code. Unknown
codes fail validation (previous-state mismatch → `RECOVERY_CONFLICT`).

## Adding a code

Add the enum member in `src/algolab/execution/errors.py`, document it above,
use it, and cover the surfaced path in tests. Keep codes stable once
released — they are part of the operational contract.