"""Aggregation: stats, baseline-vs-candidate effects, no discovery."""

import pytest

from algolab.execution.aggregation import (
    AggregationError,
    DiscoveryDeclarationNotSupported,
    aggregate_experiment,
    declare_discovery,
)
from tests.conftest import expand, make_approved_experiment, run_through_success


def _completed_experiment(conn, candidate_count: int = 1,
                          seeds=(11, 23, 37)) -> str:
    exp_id = make_approved_experiment(conn, candidate_count=candidate_count,
                                      seeds=seeds)
    result = expand(conn, exp_id)
    for run_id in result.run_ids:
        run_through_success(conn, run_id)
    return exp_id


def test_aggregate_reports_runs_and_metrics(conn) -> None:
    exp_id = _completed_experiment(conn)
    report = aggregate_experiment(conn, exp_id)
    assert report["experiment_id"] == exp_id
    assert report["run_counts"]["SUCCEEDED"] == 6  # 1 baseline + 1 cand x 3 seeds
    assert report["succeeded_runs"] == 6
    assert "final_objective" in report["metrics"]
    baseline = report["metrics"]["final_objective"]["baseline"]
    assert baseline["count"] == 3
    assert report["by_seed"]["11"]["baseline"] is not None


def test_aggregate_baseline_vs_candidate_effect(conn) -> None:
    exp_id = make_approved_experiment(conn, candidate_count=1,
                                      seeds=(11, 23, 37))
    result = expand(conn, exp_id)
    from algolab.storage.run_repository import RunRepository

    repo = RunRepository(conn, producer="test")
    for run_id in result.run_ids:
        run_through_success(conn, run_id)
        if not repo.get(run_id).is_baseline:
            with conn:
                repo.set_metrics(run_id, {
                    **repo.get(run_id).metrics,
                    "final_objective": 2.0,
                })
    report = aggregate_experiment(conn, exp_id)
    metric = report["metrics"]["final_objective"]
    assert metric["baseline"]["mean"] == 0.0
    cand_id = next(iter(metric["candidates"]))
    assert metric["candidates"][cand_id]["mean"] == 2.0
    assert metric["effect"][cand_id]["delta"] == 2.0
    assert metric["effect"][cand_id]["relative_delta"] is None  # 0 baseline


def test_aggregate_reports_warnings_for_incomplete_runs(conn) -> None:
    exp_id = make_approved_experiment(conn, candidate_count=1,
                                      seeds=(11, 23, 37))
    result = expand(conn, exp_id)
    run_through_success(conn, result.run_ids[0])  # only one run succeeds
    report = aggregate_experiment(conn, exp_id)
    assert any("not succeeded" in w for w in report["warnings"])


def test_aggregate_requires_runs(conn) -> None:
    exp_id = make_approved_experiment(conn)
    with pytest.raises(AggregationError):
        aggregate_experiment(conn, exp_id)


def test_declare_discovery_is_refused() -> None:
    with pytest.raises(DiscoveryDeclarationNotSupported):
        declare_discovery("EXP-12345678")


def test_aggregate_output_is_json_serializable(conn) -> None:
    import json

    exp_id = _completed_experiment(conn, candidate_count=2)
    report = aggregate_experiment(conn, exp_id)
    json.dumps(report)  # must not raise
