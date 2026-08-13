# Artifact Format

- **Related ADR:** ADR-0007
- **Layout:** `<artifacts_dir>/runs/<RUN_ID>/` — one directory per run.

## Immutability rule

Files are written once and never modified afterwards. `artifact_manifest.json`
is written **last** and snapshots a sha256 of every file in the directory;
recovery and verification trust only files whose hashes match.

## Files

| file | written by | contents |
| --- | --- | --- |
| `manifest.json` | worker (before run) | the run's immutable record: `run_id`, `experiment_id`, `candidate_id`, `is_baseline`, `seed`, `workload`, resolved `config`, `config_fingerprint`, `status`, `attempt_number`, `max_attempts`, `priority`, `created_at` |
| `resolved_config.json` | worker (before run) | the exact config the workload executes (canonical JSON, sorted keys) |
| `environment.json` | worker (before run) | `schema_version`, `captured_at`, `python` (executable, version), `platform`, `sqlite_version`, `workload` (name, version), `env_allowlist` (pinned environment snapshot) |
| `stdout.log` | worker | captured workload stdout (capped at `max_stdout_bytes`) |
| `stderr.log` | worker | captured workload stderr (capped at `max_stderr_bytes`) |
| `metrics.json` | **workload itself** | validated against the adapter's metric schema |
| `resource_usage.json` | worker (after exit) | timing/resource summary of the run |
| `artifact_manifest.json` | worker (last) | sha256 manifest, see below |
| `completion.json` | worker (after manifest) | final record, see below |

The workload may write additional files (e.g. `junk.bin` in tests); they are
included in the artifact manifest and count against `max_artifact_bytes`.

## `artifact_manifest.json`

```json
{
  "schema_version": "1.0.0",
  "run_id": "RUN-XXXXXXXX",
  "artifacts": [
    {
      "path": "metrics.json",
      "size": 512,
      "sha256": "a1b2c3...",
      "media_type": "application/json",
      "created_at": "2026-08-03T12:00:00+00:00"
    }
  ]
}
```

`verify()` re-hashes every listed file and returns false if any file is
missing, unreadable, or mismatched. `artifact_manifest.json` itself is not
listed.

## `completion.json`

```json
{
  "schema_version": "1.0.0",
  "run_id": "RUN-XXXXXXXX",
  "status": "SUCCEEDED",
  "error_code": null,
  "exit_code": 0,
  "started_at": "2026-08-03T12:00:00+00:00",
  "finished_at": "2026-08-03T12:00:10+00:00",
  "credits": 64.0,
  "cost": 0.0,
  "reservation_id": "RSV-XXXXXXXX"
}
```

`error_code` is one of the codes in `docs/ERROR_CODES.md` (null on success);
`credits` is the final charged compute units.

## Size limits

- `execution.max_stdout_bytes` (default 1 MiB) — stdout capture cap; overflow
  fails the run with `ARTIFACT_LIMIT_EXCEEDED`.
- `execution.max_stderr_bytes` (default 1 MiB) — stderr capture cap.
- `execution.max_artifact_bytes` (default 10 MiB) — total size of all files
  in the run directory; exceeded → `ARTIFACT_LIMIT_EXCEEDED`.
- Overflow is checked both during the poll loop and again after process exit
  (a workload may emit more output than the poll interval notices).

## Determinism

Because `resolved_config.json` is written before execution with sorted-key
canonical JSON, identical inputs produce byte-identical artifact content
(verified in `tests/test_determinism.py`).
