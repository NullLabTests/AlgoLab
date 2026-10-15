"""Typed feature-transform substrate (protocol 239).

A CPU-feasible search problem whose candidates are small, composable,
deterministic transformations of tabular features:

- base estimator: ``LogisticRegression`` (fixed max_iter, seeded);
- baseline (no transform): ``StandardScaler -> LogisticRegression``;
- operators: a closed catalog of 14 typed transforms applied before the
  baseline, each a deterministic sklearn-compatible transformer cloned per
  CV fold (fit on train only; no leakage);
- an attempt scores ``Transform -> StandardScaler -> LogisticRegression``
  with 5-fold stratified CV, twice (two replicate seeds), and is a validated
  discovery iff BOTH replicate CV accuracies beat the cached split-matched
  baseline by >= 0.005 absolute;
- costs vary by operator (5.0-18.0 credits) so the cost dimension stays live.

Determinism: outcomes depend only on dataset, operator, and integers derived
from (seed_base, trial, episode, replicate). Timing never affects decisions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import sklearn
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.datasets import load_breast_cancer, load_digits, load_wine
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import (
    PolynomialFeatures,
    PowerTransformer,
    RobustScaler,
    StandardScaler,
)

from algolab.search.toy import Attempt

WORKLOAD_VERSION = "1.0.0"
TASK_SUITE_VERSION = "1.0.0"
WORKLOAD_NAME = "transform"
TASK_FAMILIES: tuple[str, ...] = ("alpha", "beta")
HELD_OUT_FAMILY: str = "gamma"
ALL_FAMILIES: tuple[str, ...] = TASK_FAMILIES + (HELD_OUT_FAMILY,)

BASELINE_PARAMS: dict[str, Any] = {"max_iter": 1000}
DISCOVERY_MARGIN = 0.005
_SPLIT_SEED_OFFSET = 777_001


# ---------------------------------------------------------------------------
# Typed transformers (sklearn-compatible: fresh instance per attempt/fold)
# ---------------------------------------------------------------------------


class _FunctionTransformer(BaseEstimator, TransformerMixin):
    """Wrap a pure row-preserving function as a stateless transformer."""

    def __init__(self, func: Callable[[np.ndarray], np.ndarray]):
        self.func = func

    def fit(self, X: np.ndarray, y: Any = None) -> _FunctionTransformer:
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        out = np.asarray(self.func(np.asarray(X)), dtype=float)
        return out.reshape(out.shape[0], -1) if out.ndim == 1 else out


class _ClipTransformer(BaseEstimator, TransformerMixin):
    """Clip at fitted percentiles (fit per fold; no leakage)."""

    def __init__(self, lower: float = 1.0, upper: float = 99.0):
        self.lower = lower
        self.upper = upper

    def fit(self, X: np.ndarray, y: Any = None) -> _ClipTransformer:
        self.lo_ = np.percentile(np.asarray(X), self.lower, axis=0)
        self.hi_ = np.percentile(np.asarray(X), self.upper, axis=0)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return np.clip(np.asarray(X), self.lo_, self.hi_)


class _QuantileBinner(BaseEstimator, TransformerMixin):
    """Bin each feature into ``n_bins`` quantile bins (fit per fold)."""

    def __init__(self, n_bins: int = 3):
        self.n_bins = n_bins

    def fit(self, X: np.ndarray, y: Any = None) -> _QuantileBinner:
        X = np.asarray(X)
        qs = np.linspace(0, 100, self.n_bins + 1)[1:-1]
        self.edges_ = np.percentile(X, qs, axis=0)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X)
        out = np.zeros(X.shape, dtype=float)
        for j in range(X.shape[1]):
            out[:, j] = np.digitize(X[:, j], self.edges_[:, j])
        return out


class _VarianceSelector(BaseEstimator, TransformerMixin):
    """Select the ``k`` highest-variance features (fit per fold)."""

    def __init__(self, k: int = 5):
        self.k = k

    def fit(self, X: np.ndarray, y: Any = None) -> _VarianceSelector:
        var = np.var(np.asarray(X), axis=0)
        self.idx_ = np.argsort(var)[::-1][: self.k]
        self.idx_ = np.sort(self.idx_)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(X)[:, self.idx_]


class _Poly2(BaseEstimator, TransformerMixin):
    """PolynomialFeatures(degree=2) on the selected (top-variance) columns."""

    def __init__(self, k: int | None = None):
        self.k = k

    def fit(self, X: np.ndarray, y: Any = None) -> _Poly2:
        X = np.asarray(X)
        if self.k is None:
            self.sel_ = np.arange(X.shape[1])
        else:
            var = np.var(X, axis=0)
            top = np.argsort(var)[::-1][: self.k]
            self.sel_ = np.sort(top)
        self.poly_ = PolynomialFeatures(degree=2, include_bias=False)
        self.poly_.fit(X[:, self.sel_])
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        Xt = np.asarray(self.poly_.transform(np.asarray(X)[:, self.sel_]))
        if self.k is None:
            return Xt
        return np.column_stack([np.asarray(X), Xt])


class _InteractionTopK(BaseEstimator, TransformerMixin):
    """Pairwise products of the top-k variance features (fit per fold)."""

    def __init__(self, k: int = 2):
        self.k = k

    def fit(self, X: np.ndarray, y: Any = None) -> _InteractionTopK:
        X = np.asarray(X)
        var = np.var(X, axis=0)
        self.pairs_ = []
        top = np.argsort(var)[::-1][: self.k]
        for i in range(len(top)):
            for j in range(i + 1, len(top)):
                self.pairs_.append((int(top[i]), int(top[j])))
        if not self.pairs_:  # single-feature fallback: square it
            self.pairs_ = [(int(top[0]), int(top[0]))] if len(top) else []
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X)
        cols = [X[:, i] * X[:, j] for i, j in self.pairs_]
        if cols:
            return np.column_stack([X] + cols)
        return X.copy()


class _Composite(BaseEstimator, TransformerMixin):
    """Chain of transformers applied in order (fresh instances per fit)."""

    def __init__(self, factories: tuple[Callable[[], Any], ...]):
        self.factories = factories

    def fit(self, X: np.ndarray, y: Any = None) -> _Composite:
        self.steps_ = []
        Xt = np.asarray(X)
        for f in self.factories:
            step = f()
            Xt = np.asarray(step.fit_transform(Xt))
            self.steps_.append(step)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        Xt = np.asarray(X)
        for step in self.steps_:
            Xt = np.asarray(step.transform(Xt))
        return Xt


# ---------------------------------------------------------------------------
# Operator catalog (frozen): name -> factory returning a fresh transformer
# ---------------------------------------------------------------------------


def _log1p() -> Any:
    return _FunctionTransformer(lambda X: np.log1p(np.clip(X, 0, None)))


def _sqrt() -> Any:
    return _FunctionTransformer(lambda X: np.sqrt(np.clip(X, 0, None)))


def _identity() -> Any:
    return _FunctionTransformer(lambda X: np.asarray(X, dtype=float))


OPERATOR_FACTORIES: dict[str, Callable[[], Any]] = {
    "log1p": _log1p,
    "sqrt": _sqrt,
    "clip-1_99": lambda: _ClipTransformer(1.0, 99.0),
    "robust-scale": RobustScaler,
    "standard-scale": StandardScaler,
    "quantile-bin-3": lambda: _QuantileBinner(3),
    "interaction-top2": lambda: _InteractionTopK(2),
    "quantile-bin-5": lambda: _QuantileBinner(5),
    "poly2-top5": lambda: _Poly2(5),
    "power-yeo-johnson": lambda: PowerTransformer(method="yeo-johnson"),
    "pca-10": lambda: PCA(n_components=10, random_state=0),
    "poly2-all": lambda: _Poly2(None),
    "interaction+robust": lambda: _Composite(
        (lambda: _InteractionTopK(2), RobustScaler),
    ),
    "poly2+log1p": lambda: _Composite(
        (lambda: _Poly2(None), _log1p),
    ),
}

# Costs vary by operator complexity (5.0-18.0 credits).
OPERATOR_COSTS: dict[str, float] = {
    "log1p": 5.0,
    "sqrt": 5.0,
    "clip-1_99": 6.0,
    "robust-scale": 8.0,
    "standard-scale": 8.0,
    "quantile-bin-3": 8.0,
    "interaction-top2": 10.0,
    "quantile-bin-5": 10.0,
    "poly2-top5": 12.0,
    "power-yeo-johnson": 12.0,
    "pca-10": 14.0,
    "poly2-all": 15.0,
    "interaction+robust": 15.0,
    "poly2+log1p": 18.0,
}


def operators() -> tuple[str, ...]:
    return tuple(OPERATOR_FACTORIES)


def operator_cost(operator: str) -> float:
    return OPERATOR_COSTS[operator]


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
            raise KeyError(f"unknown transform family {family!r}")
    return _DATASET_CACHE[family]


def _measure_seed(seed_base: int, trial: int, episode: int,
                  replicate: int) -> int:
    return (trial * 100_000_000 + episode * 1_000_000
            + replicate * 1000 + seed_base)


def _cv_accuracy(family: str, factory: Callable[[], Any], seed: int) -> float:
    X, y = _dataset(family)
    pipe = make_pipeline(
        clone(factory()),
        StandardScaler(),
        LogisticRegression(**BASELINE_PARAMS, random_state=seed % (2 ** 31)),
    )
    cv = StratifiedKFold(
        5, shuffle=True, random_state=(seed + _SPLIT_SEED_OFFSET) % 2 ** 31)
    return float(cross_val_score(pipe, X, y, cv=cv, scoring="accuracy",
                                n_jobs=-1).mean())


_BASELINE_CACHE: dict[tuple[str, int], float] = {}
_TIME_STATS: dict[str, float] = {"operator_seconds": 0.0, "attempts": 0}


def timing_stats() -> dict[str, float]:
    return dict(_TIME_STATS)


def _baseline_accuracy(family: str, seed: int) -> float:
    key = (family, seed)
    if key not in _BASELINE_CACHE:
        _BASELINE_CACHE[key] = _cv_accuracy(
            family, _identity, seed)
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
    factory = OPERATOR_FACTORIES[operator]
    t0 = time.perf_counter()
    acc_a = _cv_accuracy(family, factory, seed_a)
    acc_b = _cv_accuracy(family, factory, seed_b)
    _TIME_STATS["operator_seconds"] += time.perf_counter() - t0
    _TIME_STATS["attempts"] += 1

    effect_1 = acc_a - base_a
    effect_2 = acc_b - base_b
    discovery = effect_1 >= threshold and effect_2 >= threshold
    return Attempt(
        operator=operator,
        cost_credits=OPERATOR_COSTS[operator],
        valid=True,
        effect_1=round(effect_1, 6),
        effect_2=round(effect_2, 6),
        mean_effect=round((effect_1 + effect_2) / 2.0, 6),
        discovery=bool(discovery),
    )


def environment_metadata() -> dict[str, Any]:
    import platform
    sizes = {}
    for fam in ALL_FAMILIES:
        X, y = _dataset(fam)
        sizes[fam] = {"n_rows": int(X.shape[0]), "n_features": int(X.shape[1]),
                      "n_classes": int(len(set(y.tolist())))}
    return {
        "environment_version": WORKLOAD_VERSION,
        "task_suite_version": TASK_SUITE_VERSION,
        "discovery_gate_version": "1.0.0",
        "families": list(ALL_FAMILIES),
        "held_out_family": HELD_OUT_FAMILY,
        "ground_truth": None,
        "promotion_threshold": DISCOVERY_MARGIN,
        "operators": list(OPERATOR_FACTORIES),
        "operator_costs": dict(OPERATOR_COSTS),
        "workload_metadata": {
            "name": WORKLOAD_NAME,
            "base_estimator": "StandardScaler->LogisticRegression",
            "baseline_params": BASELINE_PARAMS,
            "discovery_margin_absolute": DISCOVERY_MARGIN,
            "nominal_costs_flat": False,
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
    "WORKLOAD_VERSION",
    "TASK_SUITE_VERSION",
    "TASK_FAMILIES",
    "HELD_OUT_FAMILY",
    "ALL_FAMILIES",
    "BASELINE_PARAMS",
    "OPERATOR_FACTORIES",
    "OPERATOR_COSTS",
    "DISCOVERY_MARGIN",
    "operators",
    "operator_cost",
    "run_attempt",
    "timing_stats",
    "environment_metadata",
]
