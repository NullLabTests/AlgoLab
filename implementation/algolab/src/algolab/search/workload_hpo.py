"""Real-workload bridge (protocol 235): KNN hyperparameter selection.

A genuine machine-learning search problem whose answers are unknown ex
ante:

- task families are scikit-learn built-in datasets (offline): breast
  cancer (alpha), wine (beta), digits-900 subsample (gamma, held out);
- operators are seven fixed single-knob configurations over the baseline
  ``StandardScaler -> KNeighborsClassifier`` pipeline;
- an attempt scores the modified pipeline with 5-fold stratified CV,
  twice (two replicate seeds), and is a validated discovery iff BOTH
  replicate CV accuracies beat the cached split-matched baseline by at
  least the registered margin (0.005 absolute);
- costs are flat nominal credits (this bridge deliberately de-emphasizes
  the cost dimension, established in protocols 231-234; KNN fit/predict
  time is near-uniform across knobs). Measured wall-clock seconds are
  accumulated for reporting only and never influence any decision.

Determinism: outcomes depend only on dataset, operator, and integers
derived from (seed_base, trial, episode). Replicate seeds are episode-
scoped so both replicates of every attempt share splits with the cached
baseline (paired design; see spec/research/235 §3).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import sklearn
from sklearn.datasets import load_breast_cancer, load_digits, load_wine
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from algolab.search.toy import Attempt

HPO_WORKLOAD_VERSION = "1.1.0"
HPO_TASK_SUITE_VERSION = "1.1.0"

WORKLOAD_NAME = "hpo"
TASK_FAMILIES: tuple[str, ...] = ("alpha", "beta")
HELD_OUT_FAMILY: str = "gamma"
ALL_FAMILIES: tuple[str, ...] = TASK_FAMILIES + (HELD_OUT_FAMILY,)

BASELINE_PARAMS: dict[str, Any] = {"n_neighbors": 5}

# Fixed single-knob operator configurations (protocol 235 §3, amended).
OPERATOR_DELTAS: dict[str, dict[str, Any]] = {
    "k1": {"n_neighbors": 1},
    "k3": {"n_neighbors": 3},
    "k11": {"n_neighbors": 11},
    "k21": {"n_neighbors": 21},
    "dist-weight": {"weights": "distance"},
    "manhattan": {"p": 1},
    "chebyshev": {"metric": "chebyshev"},
}

# Cost-flat workload: every operator charges the same nominal credit cost.
NOMINAL_COSTS: dict[str, float] = {op: 10.0 for op in OPERATOR_DELTAS}

DISCOVERY_MARGIN = 0.005  # absolute CV accuracy improvement per replicate

_SPLIT_SEED_OFFSET = 777_001


def operators() -> tuple[str, ...]:
    return tuple(OPERATOR_DELTAS)


def operator_cost(operator: str) -> float:
    return NOMINAL_COSTS[operator]


_DATASET_CACHE: dict[str, tuple[np.ndarray, np.ndarray]] = {}


def _dataset(family: str) -> tuple[np.ndarray, np.ndarray]:
    if family not in _DATASET_CACHE:
        if family == "alpha":
            _DATASET_CACHE[family] = load_breast_cancer(return_X_y=True)
        elif family == "beta":
            _DATASET_CACHE[family] = load_wine(return_X_y=True)
        elif family == HELD_OUT_FAMILY:
            X, y = load_digits(return_X_y=True)
            rng = np.random.RandomState(0)
            idx = rng.choice(len(X), 900, replace=False)
            _DATASET_CACHE[family] = (X[idx], y[idx])
        else:
            raise KeyError(f"unknown hpo family {family!r}")
    return _DATASET_CACHE[family]


def _measure_seed(seed_base: int, trial: int, episode: int,
                  replicate: int) -> int:
    """Episode-scoped derivation: replicates are shared by all attempts
    within an episode so the baseline is split-matched (paired design)."""
    return (trial * 100_000_000 + episode * 1_000_000
            + replicate * 1000 + seed_base)


def _cv_accuracy(family: str, params: dict[str, Any], seed: int) -> float:
    X, y = _dataset(family)
    pipe = make_pipeline(StandardScaler(), KNeighborsClassifier(**params))
    cv = StratifiedKFold(
        5, shuffle=True, random_state=(seed + _SPLIT_SEED_OFFSET) % 2 ** 31)
    return float(cross_val_score(pipe, X, y, cv=cv, scoring="accuracy").mean())


_BASELINE_CACHE: dict[tuple[str, int], float] = {}

_TIME_STATS: dict[str, float] = {"operator_seconds": 0.0, "attempts": 0}


def timing_stats() -> dict[str, float]:
    return dict(_TIME_STATS)


def _baseline_accuracy(family: str, seed: int) -> float:
    key = (family, seed)
    if key not in _BASELINE_CACHE:
        _BASELINE_CACHE[key] = _cv_accuracy(family, dict(BASELINE_PARAMS), seed)
    return _BASELINE_CACHE[key]


def run_attempt(family: str, operator: str, *, seed_base: int,
                trial: int, episode: int, attempt: int,
                threshold: float = DISCOVERY_MARGIN) -> Attempt:
    """Measure one operator application on a real dataset (twice)."""
    del attempt  # replicates are episode-scoped by design (paired baseline)
    import time
    seed_a = _measure_seed(seed_base, trial, episode, 1)
    seed_b = _measure_seed(seed_base, trial, episode, 2)
    base_a = _baseline_accuracy(family, seed_a)
    base_b = _baseline_accuracy(family, seed_b)
    params = {**BASELINE_PARAMS, **OPERATOR_DELTAS[operator]}
    t0 = time.perf_counter()
    acc_a = _cv_accuracy(family, params, seed_a)
    acc_b = _cv_accuracy(family, params, seed_b)
    _TIME_STATS["operator_seconds"] += time.perf_counter() - t0
    _TIME_STATS["attempts"] += 1

    effect_1 = acc_a - base_a
    effect_2 = acc_b - base_b
    discovery = effect_1 >= threshold and effect_2 >= threshold
    return Attempt(
        operator=operator,
        cost_credits=NOMINAL_COSTS[operator],
        valid=True,
        effect_1=round(effect_1, 6),
        effect_2=round(effect_2, 6),
        mean_effect=round((effect_1 + effect_2) / 2.0, 6),
        discovery=bool(discovery),
    )


def environment_metadata() -> dict[str, Any]:
    """Non-oracle environment description for the artifact bundle."""
    import platform
    sizes = {}
    for fam in ALL_FAMILIES:
        X, y = _dataset(fam)
        sizes[fam] = {"n_rows": int(X.shape[0]), "n_features": int(X.shape[1]),
                      "n_classes": int(len(set(y.tolist())))}
    return {
        "environment_version": HPO_WORKLOAD_VERSION,
        "task_suite_version": HPO_TASK_SUITE_VERSION,
        "discovery_gate_version": "1.0.0",
        "families": list(ALL_FAMILIES),
        "held_out_family": HELD_OUT_FAMILY,
        "ground_truth": None,
        "promotion_threshold": DISCOVERY_MARGIN,
        "operators": list(OPERATOR_DELTAS),
        "workload_metadata": {
            "name": WORKLOAD_NAME,
            "base_estimator": "StandardScaler->KNeighborsClassifier",
            "baseline_params": BASELINE_PARAMS,
            "discovery_margin_absolute": DISCOVERY_MARGIN,
            "nominal_costs_flat": True,
            "dataset_shapes": sizes,
            "sklearn_version": sklearn.__version__,
            "numpy_version": np.__version__,
            "python_version": platform.python_version(),
            "measured_operator_seconds": round(
                _TIME_STATS["operator_seconds"], 2),
            "measured_attempts": int(_TIME_STATS["attempts"]),
        },
    }


__all__ = [
    "WORKLOAD_NAME",
    "HPO_WORKLOAD_VERSION",
    "HPO_TASK_SUITE_VERSION",
    "TASK_FAMILIES",
    "HELD_OUT_FAMILY",
    "ALL_FAMILIES",
    "BASELINE_PARAMS",
    "OPERATOR_DELTAS",
    "NOMINAL_COSTS",
    "DISCOVERY_MARGIN",
    "operators",
    "operator_cost",
    "run_attempt",
    "timing_stats",
    "environment_metadata",
]
