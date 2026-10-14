"""Provenance: the schema-v3 ``tasks`` table must name the real workload.

Regression guard for the defect where every task row was hardcoded to the toy
workload label regardless of the configured workload (see
``docs/audits/initial-audit.md`` D-3). Also smoke-covers the ``s2`` workload,
which is registered in the harness but otherwise untested, and checks that its
environment metadata lists the held-out family (D-6).
"""

from __future__ import annotations

import json

from algolab.search import ExperimentConfig, PolicyComparison
from algolab.search.harness import resolve_workload
from algolab.storage.db import connect


def _tiny_run(workload: str, tmp_path):
    cfg = ExperimentConfig(
        experiment_id=f"smoke-{workload}",
        workload=workload,
        trials=1,
        episodes_per_trial=1,
        prior_attempts_per_family=1,
        budget_credits=20.0,
        arms=("static",),
        ablations=(),
    )
    d = tmp_path / "art"
    conn = connect(":memory:", initialize=True)
    comp = PolicyComparison(cfg, conn, d)
    results = comp.run()
    stats = comp.analyze(results)
    held_out = comp.analyze_held_out(comp.run_held_out())
    comp.write_report(results, stats, held_out)
    comp.write_artifact_bundle(stats, held_out)
    return conn, d


def _task_workloads(conn) -> set[str]:
    rows = conn.execute("SELECT DISTINCT workload FROM tasks").fetchall()
    return {r[0] for r in rows}


def test_hpo_tasks_record_the_hpo_workload(tmp_path) -> None:
    conn, _ = _tiny_run("hpo", tmp_path)
    assert _task_workloads(conn) == {"hpo"}


def test_toy_tasks_record_the_toy_workload(tmp_path) -> None:
    conn, _ = _tiny_run("toy", tmp_path)
    assert _task_workloads(conn) == {"toy"}


def test_tasks_never_claim_toy_for_a_real_workload(tmp_path) -> None:
    conn, _ = _tiny_run("hpo", tmp_path)
    assert "toy-discovery" not in _task_workloads(conn)
    assert "toy" not in _task_workloads(conn)


class TestS2Substrate:
    def test_resolves_and_metadata_lists_all_families(self) -> None:
        view = resolve_workload("s2")
        assert view.key == "s2"
        assert not view.has_oracle
        meta = view.environment_metadata()
        assert view.held_out_family in meta["families"]
        assert view.held_out_family in meta["workload_metadata"]["dataset_shapes"]

    def test_tiny_s2_run_produces_a_bundle(self, tmp_path) -> None:
        conn, d = _tiny_run("s2", tmp_path)
        assert (d / "manifest.json").is_file()
        assert (d / "statistics.json").is_file()
        manifest = json.loads((d / "manifest.json").read_text())
        assert manifest["workload"] == "s2"
        env = json.loads((d / "environment.json").read_text())
        assert env["held_out_family"] in env["families"]
        assert _task_workloads(conn) == {"s2"}
