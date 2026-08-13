# Workload Adapters

Workloads plug into AlgoLab through a typed adapter interface
(`src/algolab/workloads/base.py`). An adapter owns everything the execution
plane needs to know about a workload: its name/version, default
configuration, argv for the worker, timeout, compute-unit estimation, and
metric/artifact validation.

## Interface

```python
class WorkloadAdapter:
    name: str
    version: str
    description: str

    def defaults(self) -> dict[str, Any]: ...
    def config_from_changes(self, changes: list[dict[str, Any]]) -> dict[str, Any]: ...
    def validate_config(self, config: dict[str, Any]) -> None: ...
    def command(self, run_dir: Path, config: dict[str, Any],
                seed: int) -> list[str]: ...
    def timeout_seconds(self, config: dict[str, Any]) -> float: ...
    def estimate_compute_units(self, config: dict[str, Any]) -> float: ...
    def validate_metrics(self, metrics: dict[str, Any]) -> None: ...
    expected_artifacts: tuple[str, ...]
```

- **`name`/`version`** — the name selects the adapter (`execution.workload`
  in the config); the version is pinned into `environment.json` and the
  config fingerprint.
- **`defaults()`** — full resolved configuration. Adapters *must* validate
  the complete config, not a partial override: a partial config (e.g. only
  `max_iterations`) is invalid until merged with defaults, because the
  subprocess runs with exactly the resolved config.
- **`command()`** — the argv the worker runs. It may reference `run_dir`,
  which contains the pre-written `resolved_config.json`.
- **`timeout_seconds()`** — workload-level deadline; the worker additionally
  enforces `execution.default_timeout_seconds` as a ceiling.
- **`estimate_compute_units()`** — used for budget reservation *before*
  scheduling; actual charges use the compute units reported by the run.
- **`validate_metrics()`** — raises `MetricsInvalid` on schema violations;
  the worker maps that to `METRICS_INVALID`.
- **`expected_artifacts`** — file names the workload must produce; missing
  or hash-failed files map to `ARTIFACT_MISSING`.

## Invocation contract

The worker launches the adapter's command with:

- a **clean environment**: only keys in `execution.env_allowlist`
  (default `PATH`, `PYTHONPATH`, `LANG`, `LC_ALL`, `TMPDIR`, `TZ`) are
  passed through — untrusted/unrelated variables never leak into runs;
- **cwd = the run directory** `<artifacts_dir>/runs/<RUN_ID>/`;
- stdout/stderr captured to `stdout.log`/`stderr.log` with hard limits;
- the workload's *effective* timeout = `min(adapter timeout, default_timeout_seconds)`.

The workload must write `metrics.json` into its cwd and exit 0 on success.

## Built-in: `quadratic_optimizer` (v1.0.0)

A deterministic, dependency-free quadratic-form minimizer used to exercise
the whole M1 pipeline:

```
python quadratic_optimizer.py --config resolved_config.json \
    --seed <int> --out metrics.json
```

Minimizes `sum(a_i * (x_i - target_i)^2)` with a seeded optimizer
(strategies `gradient_descent`, `momentum`, `nesterov`; optional gaussian
noise on gradients). Every random draw comes from `random.Random(seed)` in a
fixed order, so identical config + seed produce bit-identical metrics.

### Config keys (all validated)

| key | default | notes |
| --- | --- | --- |
| `strategy` | `gradient_descent` | one of the three strategies |
| `learning_rate` | `0.1` | positive number |
| `max_iterations` | `2000` | positive integer |
| `dim` | `16` | positive integer |
| `convergence_tolerance` | `1e-9` | positive number |
| `noise_scale` | `0.0` | non-negative; gradient noise |
| `objective_threshold` | `null` | if set, `final_objective > threshold` forces `converged=false` |
| `timeout_seconds` | `60.0` | adapter-level timeout |

### Test hooks (integration tests only)

`sleep_seconds`, `raise_on_start` (exit 1 before optimizing),
`emit_invalid_metrics` (write a schema-invalid `metrics.json`),
`extra_bytes` (write an oversized binary file),
`print_bytes` (flood stdout past the capture limit).

### Metrics (validated, must all be present)

`final_objective`, `initial_objective`, `converged` (bool), `iterations`
(int), `compute_units` (float), `gradient_norm` (float), plus the
informational `strategy`, `seed`, `dim`.

Compute units = `iterations * dim`; the planner's estimate is
`max_iterations * dim`.

## Registration

Adapters register through `src/algolab/workloads/__init__.py`; the registry
is consulted by `get_workload(name)`, which raises `WorkloadUnknownError`
(→ `WORKLOAD_UNKNOWN`) for unknown names. The registry keeps the built-in
adapter (and the standalone script next to it) co-located so the script can
be invoked by absolute path regardless of cwd.

## Contract for new workloads (M2+)

1. Implement `WorkloadAdapter` in `src/algolab/workloads/`, ship the
   standalone script alongside it.
2. Validate the *complete* config in `validate_config`.
3. Write `metrics.json` into the cwd; exit 0 only on success.
4. Document the metric schema; the aggregate step keys candidates by seed
   and expects numeric primary/secondary metrics.
5. Add the adapter to the registry and cover it with `tests/test_workloads.py`.
