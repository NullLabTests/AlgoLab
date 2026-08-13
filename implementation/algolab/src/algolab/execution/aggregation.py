"""Experiment aggregation (M1).

Machine-readable, seed-level, baseline-vs-candidate statistics over the runs
of one experiment. Aggregation **cannot** declare a discovery — that gate is
explicitly refused here and left to later milestones.
"""

from __future__ import annotations

import sqlite3
import statistics
from datetime import UTC, datetime
from typing import Any

from algolab.storage.run_repository import RunRepository

# Metrics that describe cost/timing rather than scientific outcome; they are
# reported but excluded from effect statistics.
_NON_SCIENTIFIC_METRICS = frozenset({
    "compute_units",
    "elapsed_s",
    "seed",
})


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class AggregationError(RuntimeError):
    """Base class for aggregation failures."""


class DiscoveryDeclarationNotSupported(AggregationError):
    """Declaring a discovery is out of scope for M1."""


def _numeric_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    return {
        key: float(value)
        for key, value in metrics.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        and key not in _NON_SCIENTIFIC_METRICS
    }


def _stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0.0, "mean": 0.0, "median": 0.0, "std": 0.0,
                "min": 0.0, "max": 0.0}
    return {
        "count": float(len(values)),
        "mean": round(statistics.fmean(values), 9),
        "median": round(statistics.median(values), 9),
        "std": round(statistics.stdev(values), 9) if len(values) > 1 else 0.0,
        "min": round(min(values), 9),
        "max": round(max(values), 9),
    }


def aggregate_experiment(conn: sqlite3.Connection, experiment_id: str
                         ) -> dict[str, Any]:
    """Aggregate all runs of *experiment_id* into a machine-readable report."""
    runs = RunRepository(conn).list_runs(experiment_id=experiment_id)
    if not runs:
        raise AggregationError(f"no runs for experiment {experiment_id}")

    by_status: dict[str, int] = {}
    succeeded: list[Any] = []
    for run in runs:
        by_status[run.status] = by_status.get(run.status, 0) + 1
        if run.status == "SUCCEEDED" and run.metrics:
            succeeded.append(run)

    baselines = [r for r in succeeded if r.is_baseline]
    candidates = [r for r in succeeded if not r.is_baseline]

    metric_names: list[str] = []
    for run in succeeded:
        for key in _numeric_metrics(run.metrics):
            if key not in metric_names:
                metric_names.append(key)

    # Per-seed table: seed -> {baseline: metrics, <candidate_id>: metrics}.
    by_seed: dict[str, dict[str, Any]] = {}
    for run in succeeded:
        seed = str(run.seed)
        table = by_seed.setdefault(seed, {})
        key = "baseline" if run.is_baseline else str(run.candidate_id)
        table[key] = run.metrics

    # Per-metric statistics + baseline-vs-candidate effects.
    metrics_report: dict[str, Any] = {}
    for metric in metric_names:
        baseline_values = [
            float(r.metrics[metric]) for r in baselines
            if isinstance(r.metrics.get(metric), (int, float))
        ]
        candidate_values: dict[str, list[float]] = {}
        for run in candidates:
            if not isinstance(run.metrics.get(metric), (int, float)):
                continue
            cid = run.candidate_id or "unknown"
            candidate_values.setdefault(cid, []).append(float(run.metrics[metric]))
        baseline_stats = _stats(baseline_values)
        candidates_stats = {
            cid: _stats(values) for cid, values in candidate_values.items()
        }
        effects: dict[str, dict[str, Any]] = {}
        for cid, stats in candidates_stats.items():
            if baseline_stats["count"] > 0 and stats["count"] > 0:
                delta = stats["mean"] - baseline_stats["mean"]
                relative = (
                    delta / baseline_stats["mean"]
                    if baseline_stats["mean"] != 0 else None
                )
                effects[cid] = {
                    "delta": round(delta, 9),
                    "relative_delta": (
                        round(relative, 9) if relative is not None else None
                    ),
                }
        metrics_report[metric] = {
            "baseline": baseline_stats,
            "candidates": candidates_stats,
            "effect": effects,
        }

    warnings: list[str] = []
    pending = [s for s, n in by_status.items() if s not in ("SUCCEEDED",)]
    if pending:
        warnings.append(
            f"{sum(by_status[s] for s in pending)} run(s) not succeeded: "
            + ", ".join(f"{s}={by_status[s]}" for s in sorted(pending))
        )
    if len(baselines) == 0:
        warnings.append("no succeeded baseline runs; effects are undefined")
    if len(candidates) == 0:
        warnings.append("no succeeded candidate runs")

    total_credits = sum(r.credits_charged for r in runs)
    total_cost = sum(r.cost_charged for r in runs)

    return {
        "schema_version": "1.0.0",
        "experiment_id": experiment_id,
        "generated_at": _utc_now(),
        "run_counts": by_status,
        "succeeded_runs": len(succeeded),
        "total_credits_charged": round(total_credits, 6),
        "total_cost_charged": round(total_cost, 6),
        "metrics": metrics_report,
        "by_seed": by_seed,
        "warnings": warnings,
    }


def declare_discovery(*args: Any, **kwargs: Any) -> None:
    """Refuse discovery declaration (M1 scope boundary)."""
    raise DiscoveryDeclarationNotSupported(
        "declaring a discovery is not supported in M1; aggregation is "
        "observational only"
    )
