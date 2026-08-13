"""Workload adapter contract + quadratic_optimizer determinism."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from algolab.workloads import (
    ConfigInvalid,
    MetricsInvalid,
    WorkloadUnknownError,
    get_workload,
    list_workloads,
)

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "algolab"
SCRIPT = PACKAGE / "workloads" / "quadratic_optimizer.py"


@pytest.fixture
def adapter():
    return get_workload("quadratic_optimizer")


def test_registry() -> None:
    assert "quadratic_optimizer" in list_workloads()
    with pytest.raises(WorkloadUnknownError):
        get_workload("does-not-exist")


def test_config_from_changes_overrides_defaults(adapter) -> None:
    config = adapter.config_from_changes([
        {"component": "activation"},          # unrelated keys ignored
        {"strategy": "momentum", "max_iterations": 500, "learning_rate": 0.05},
    ])
    assert config["strategy"] == "momentum"
    assert config["max_iterations"] == 500
    assert config["learning_rate"] == 0.05
    assert config["dim"] == 16  # default retained


def test_baseline_config_uses_defaults(adapter) -> None:
    config = adapter.config_from_changes([{"baseline": "small_mlp/gelu"}])
    assert config == adapter.defaults()


@pytest.mark.parametrize("bad", [
    {"strategy": "adam"},
    {"learning_rate": -1},
    {"max_iterations": 0},
    {"dim": 0},
    {"convergence_tolerance": 0},
    {"noise_scale": -0.5},
    {"raise_on_start": "yes"},
])
def test_invalid_configs_fail_closed(adapter, bad) -> None:
    with pytest.raises(ConfigInvalid):
        adapter.config_from_changes([bad])


def test_command_is_argv_without_shell(adapter, tmp_path) -> None:
    argv = adapter.command(tmp_path, adapter.defaults(), 7)
    assert isinstance(argv, list)
    assert all(isinstance(a, str) for a in argv)
    assert argv[0] == sys.executable
    assert "--config" in argv and "--out" in argv
    assert "&&" not in argv and "|" not in argv and ";" not in argv


def test_estimate_compute_units(adapter) -> None:
    config = adapter.config_from_changes([{"dim": 10, "max_iterations": 100}])
    assert adapter.estimate_compute_units(config) == 1000.0


def _run_script(config: dict, seed: int, tmp_path: Path) -> dict:
    run_dir = tmp_path / f"run-{seed}-{len(list(tmp_path.glob('*')))}"
    run_dir.mkdir(exist_ok=True)
    (run_dir / "resolved_config.json").write_text(json.dumps(config))
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--config",
         str(run_dir / "resolved_config.json"), "--seed", str(seed),
         "--out", str(run_dir / "metrics.json")],
        capture_output=True, text=True, cwd=run_dir,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads((run_dir / "metrics.json").read_text())


def test_script_is_deterministic_per_seed(adapter, tmp_path) -> None:
    config = adapter.config_from_changes(
        [{"strategy": "nesterov", "dim": 8, "max_iterations": 300}])
    m1 = _run_script(config, seed=42, tmp_path=tmp_path)
    m2 = _run_script(config, seed=42, tmp_path=tmp_path)
    assert m1 == m2  # byte-identical scientific metrics
    m3 = _run_script(config, seed=43, tmp_path=tmp_path)
    assert m1["final_objective"] != m3["final_objective"]


def test_script_multimetric_and_pass_fail(adapter, tmp_path) -> None:
    config = adapter.config_from_changes(
        [{"max_iterations": 2000, "dim": 16}])
    metrics = _run_script(config, seed=1, tmp_path=tmp_path)
    adapter.validate_metrics(metrics)
    assert {"final_objective", "initial_objective", "converged",
            "iterations", "compute_units", "gradient_norm"} <= set(metrics)
    assert metrics["converged"] is True
    # A threshold makes the same run "fail" at workload level.
    failing = adapter.config_from_changes(
        [{"max_iterations": 2000, "dim": 16, "objective_threshold": 1e-30}])
    metrics_fail = _run_script(failing, seed=1, tmp_path=tmp_path)
    assert metrics_fail["converged"] is False


def test_raise_on_start_hook_exits_nonzero(tmp_path) -> None:
    config = {"raise_on_start": True}
    run_dir = tmp_path / "boom"
    run_dir.mkdir()
    (run_dir / "resolved_config.json").write_text(json.dumps(config))
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--config",
         str(run_dir / "resolved_config.json"), "--seed", "1",
         "--out", str(run_dir / "metrics.json")],
        capture_output=True, text=True,
    )
    assert proc.returncode != 0


def test_emit_invalid_metrics_hook(tmp_path) -> None:
    config = {"emit_invalid_metrics": True}
    run_dir = tmp_path / "bad"
    run_dir.mkdir()
    (run_dir / "resolved_config.json").write_text(json.dumps(config))
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--config",
         str(run_dir / "resolved_config.json"), "--seed", "1",
         "--out", str(run_dir / "metrics.json")],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    bad = json.loads((run_dir / "metrics.json").read_text())
    from algolab.workloads import get_workload

    with pytest.raises(MetricsInvalid):
        get_workload("quadratic_optimizer").validate_metrics(bad)


def test_timeout_seconds_explicit(adapter) -> None:
    assert adapter.timeout_seconds(adapter.defaults()) > 0
    config = adapter.config_from_changes([{"timeout_seconds": 3}])
    assert adapter.timeout_seconds(config) == 3.0
