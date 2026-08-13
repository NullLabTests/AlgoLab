"""Determinism: identical inputs produce bit-identical outcomes.

Two projects with identical manifests run in fresh directories must
produce identical per-(baseline|candidate, seed) metric values, identical
workload stdout, and identical aggregated statistics.
"""

import json

from algolab.execution.aggregation import aggregate_experiment
from algolab.execution.worker import Worker
from algolab.storage.db import connect
from tests.conftest import (
    expand,
    grant,
    make_approved_experiment,
    tmp_config,
)


def _run_project(root) -> dict:
    config = tmp_config(root)
    conn = connect(config.storage.path, initialize=True)
    grant(conn)
    exp_id = make_approved_experiment(conn, candidate_count=1,
                                      seeds=(11, 23, 37, 41))
    expand(conn, exp_id)
    Worker(conn, config).run_loop()
    report = aggregate_experiment(conn, exp_id)
    stdout_by_key = {}
    for run_dir in (config.storage.artifacts_dir / "runs").iterdir():
        manifest = json.loads((run_dir / "manifest.json").read_text())
        key = (manifest["seed"], manifest["is_baseline"])
        stdout_by_key[key] = (run_dir / "stdout.log").read_bytes()
    conn.close()
    return {"report": report, "stdout": stdout_by_key}


def _metric_snapshot(report: dict) -> dict:
    metric = report["metrics"]["final_objective"]
    by_seed = report["by_seed"]
    baseline_by_seed = {
        seed: table["baseline"]["final_objective"]
        for seed, table in sorted(by_seed.items())
        if table.get("baseline") is not None}
    candidate_by_seed = {
        seed: table[cand]["final_objective"]
        for seed, table in sorted(by_seed.items())
        for cand in table
        if cand != "baseline"}
    return {
        "baseline_mean": metric["baseline"]["mean"],
        "candidate_mean": next(iter(metric["candidates"].values()))["mean"],
        "baseline_by_seed": baseline_by_seed,
        "candidate_by_seed": candidate_by_seed,
    }


def test_deterministic_outcomes_across_clean_projects(tmp_path) -> None:
    project_a = _run_project(tmp_path / "a")
    project_b = _run_project(tmp_path / "b")
    assert _metric_snapshot(project_a["report"]) == \
        _metric_snapshot(project_b["report"])
    assert project_a["stdout"] == project_b["stdout"]


def test_same_config_yields_identical_fingerprint() -> None:
    from algolab.execution.expansion import config_fingerprint

    config_a = {"optimizer": "adamw", "lr": 1e-3, "seed": 11}
    config_b = {"seed": 11, "optimizer": "adamw", "lr": 1e-3}
    fingerprint = lambda cfg: config_fingerprint(  # noqa: E731
        experiment_id="EXP-1", workload="quadratic_optimizer",
        config=cfg, seed=11, is_baseline=False)
    assert fingerprint(config_a) == fingerprint(config_b)
    assert list(config_a) != list(config_b)  # insertion order differs
