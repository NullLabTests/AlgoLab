"""Generative composition substrate (protocol 240).

Every attempt in this workload is a *generated program*: an ordered sequence of
1-3 typed feature transforms (see :mod:`algolab.search.candidates`) executed as
a real scikit-learn pipeline in front of a fixed estimator::

    Program(transform_1, ..., transform_k) -> StandardScaler
        -> LogisticRegression(max_iter=1000)

The objective is real classification accuracy on real (sklearn built-in) data,
measured by 5-fold stratified cross-validation, twice (two replicate split
seeds). The effect of a program is its CV accuracy minus the CV accuracy of the
**identity program** (``StandardScaler -> LogisticRegression``) evaluated on the
*same split seed*, so the comparison is paired at the fold level.

Determinism contract
--------------------
Outcomes depend only on (family, program, seed_base, trial, episode, replicate).
``attempt`` is deliberately **not** part of the seed: evaluating the same
program twice in the same episode yields the identical measurement. This is a
scientific choice, not a convenience — it makes "discovery farming" (re-running
a lucky program to accumulate discovery counts) impossible, because the
protocol-240 primary metric counts *distinct* validated programs. Wall-clock
time is recorded for budget accounting but never influences a decision.

Leakage contract
----------------
Every transformer is fitted inside the CV fold on training rows only
(``Pipeline`` + ``cross_val_score``); nothing is fitted on validation rows and
the held-out family is never read by any search path.

The atom transformers are the protocol-239 implementations imported as-is, so
an atom means exactly the same thing in both protocols and a length-1 program
is directly comparable to a protocol-239 operator.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import numpy as np
import sklearn
from sklearn.base import TransformerMixin, clone
from sklearn.datasets import load_breast_cancer, load_digits, load_wine
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler, StandardScaler

from algolab.search import candidates
from algolab.search.toy import Attempt
from algolab.search.workload_transform import (
    # Reused verbatim from protocol 239 (same atom semantics across protocols).
    _ClipTransformer,
    _Composite,
    _FunctionTransformer,
    _InteractionTopK,
    _Poly2,
    _QuantileBinner,
)

WORKLOAD_NAME = "compose"
WORKLOAD_VERSION = "1.0.0"
TASK_SUITE_VERSION = "1.0.0"
DISCOVERY_GATE_VERSION = "1.0.0"

TASK_FAMILIES: tuple[str, ...] = ("alpha", "beta")
HELD_OUT_FAMILY: str = "gamma"
ALL_FAMILIES: tuple[str, ...] = TASK_FAMILIES + (HELD_OUT_FAMILY,)

BASELINE_PARAMS: dict[str, Any] = {"max_iter": 1000}
DISCOVERY_MARGIN = 0.005

#: gamma is subsampled so the pre-registered CPU budget holds; the subsample
#: seed is part of the frozen task suite (never re-drawn).
GAMMA_ROWS = 600
GAMMA_SUBSAMPLE_SEED = 0

_SPLIT_SEED_OFFSET = 777_001
_CV_FOLDS = 5


# ---------------------------------------------------------------------------
# Atom factories (fresh instance per attempt and per fold -> no leakage)
# ---------------------------------------------------------------------------


def _log1p() -> Any:
    return _FunctionTransformer(lambda X: np.log1p(np.clip(X, 0, None)))


def _sqrt() -> Any:
    return _FunctionTransformer(lambda X: np.sqrt(np.clip(X, 0, None)))


ATOM_FACTORIES: dict[str, Callable[[], Any]] = {
    "log1p": _log1p,
    "sqrt": _sqrt,
    "clip-1_99": lambda: _ClipTransformer(1.0, 99.0),
    "robust-scale": RobustScaler,
    "standard-scale": StandardScaler,
    "quantile-bin-3": lambda: _QuantileBinner(3),
    "interaction-top2": lambda: _InteractionTopK(2),
    "pca-10": lambda: PCA(n_components=10, random_state=0),
    "poly2-top5": lambda: _Poly2(5),
}

# The grammar and the evaluator must agree on the atom set, or a program could
# parse but not execute. Asserted at import so the failure is loud and early.
assert set(ATOM_FACTORIES) == set(candidates.ATOMS), (
    "grammar/evaluator atom mismatch: "
    f"{sorted(set(ATOM_FACTORIES) ^ set(candidates.ATOMS))}")


def _identity() -> Any:
    return _FunctionTransformer(lambda X: np.asarray(X, dtype=float))


def program_transformer(program: str) -> Any:
    """Build a fresh, unfitted transformer for *program* (validated)."""
    atoms = candidates.parse(program)
    if len(atoms) == 1:
        return ATOM_FACTORIES[atoms[0]]()
    return _Composite(tuple(ATOM_FACTORIES[a] for a in atoms))


def operators() -> tuple[str, ...]:
    """Atom operators (the prior/policy-facing "operator" list).

    The generative arms are not restricted to this list: they propose and
    execute arbitrary programs from the grammar. The atoms are what the frozen
    K0 prior is built over, because prior evidence about single transforms is
    the only knowledge available before any composition has been tried.
    """
    return candidates.ATOMS


def operator_cost(operator: str) -> float:
    """Registered credit cost of one attempt at a program (or bare atom)."""
    return candidates.program_cost(operator)


# ---------------------------------------------------------------------------
# Datasets (sklearn built-ins; CPU-only; no downloads)
# ---------------------------------------------------------------------------


_DATASET_CACHE: dict[str, tuple[np.ndarray, np.ndarray]] = {}


def _dataset(family: str) -> tuple[np.ndarray, np.ndarray]:
    if family not in _DATASET_CACHE:
        if family == "alpha":
            X, y = load_breast_cancer(return_X_y=True)
        elif family == "beta":
            X, y = load_wine(return_X_y=True)
        elif family == HELD_OUT_FAMILY:
            X, y = load_digits(return_X_y=True)
            rng = np.random.RandomState(GAMMA_SUBSAMPLE_SEED)
            idx = rng.choice(len(X), GAMMA_ROWS, replace=False)
            idx.sort()
            X, y = X[idx], y[idx]
        else:
            raise KeyError(f"unknown compose family {family!r}")
        _DATASET_CACHE[family] = (np.asarray(X, dtype=float), np.asarray(y))
    return _DATASET_CACHE[family]


def _measure_seed(seed_base: int, trial: int, episode: int,
                  replicate: int) -> int:
    """Deterministic split seed for one replicate measurement.

    ``attempt`` is intentionally excluded (see the module docstring).
    """
    return (trial * 100_000_000 + episode * 1_000_000
            + replicate * 1000 + seed_base)


def _cv_accuracy(family: str, transformer: Any, seed: int) -> float:
    X, y = _dataset(family)
    pipe = make_pipeline(
        clone(transformer),
        StandardScaler(),
        LogisticRegression(**BASELINE_PARAMS, random_state=seed % (2 ** 31)),
    )
    cv = StratifiedKFold(
        _CV_FOLDS, shuffle=True, random_state=(seed + _SPLIT_SEED_OFFSET) % 2 ** 31)
    scores = cross_val_score(pipe, X, y, cv=cv, scoring="accuracy", n_jobs=1)
    return float(np.mean(scores))


_BASELINE_CACHE: dict[tuple[str, int], float] = {}
#: Memoisation of the pure evaluation function keyed by
#: (family, program, seed_a, seed_b). Different arms frequently propose the
#: same program (the space is closed and small); the evaluation is a pure
#: function of these four values, so a cache hit is *identical* to a recompute.
#: This saves wall clock only: credits are still charged per attempt by every
#: arm, so the registered cost model is untouched. Every call (cached or not)
#: is counted in ``_TIME_STATS["attempts"]``; ``evaluations`` counts real
#: computations and ``cache_hits`` the saved ones.
_EVAL_CACHE: dict[tuple[str, str, int, int], tuple[float, float]] = {}
_TIME_STATS: dict[str, float] = {
    "operator_seconds": 0.0, "attempts": 0, "evaluations": 0, "cache_hits": 0}


def timing_stats() -> dict[str, float]:
    return dict(_TIME_STATS)


def reset_timing_stats() -> None:
    _TIME_STATS["operator_seconds"] = 0.0
    _TIME_STATS["attempts"] = 0
    _TIME_STATS["evaluations"] = 0
    _TIME_STATS["cache_hits"] = 0


def clear_caches() -> None:
    """Drop the memoised evaluation/baseline caches (test isolation)."""
    _EVAL_CACHE.clear()
    _BASELINE_CACHE.clear()


def _baseline_accuracy(family: str, seed: int) -> float:
    key = (family, seed)
    if key not in _BASELINE_CACHE:
        _BASELINE_CACHE[key] = _cv_accuracy(family, _identity(), seed)
    return _BASELINE_CACHE[key]


def run_attempt(family: str, program: str, *, seed_base: int,
                trial: int, episode: int, attempt: int,
                threshold: float = DISCOVERY_MARGIN) -> Attempt:
    """Evaluate one generated program on *family* with 2 replicate splits.

    Returns an :class:`~algolab.search.toy.Attempt`. ``valid`` is False when the
    program could not be executed (e.g. a transform raised); an invalid attempt
    is recorded and charged, never silently dropped. A *validated discovery*
    requires both replicate effects to clear ``threshold``.
    """
    del attempt  # deterministic per (trial, episode) by design
    atoms = candidates.parse(program)
    cost = candidates.program_cost(program)
    seed_a = _measure_seed(seed_base, trial, episode, 1)
    seed_b = _measure_seed(seed_base, trial, episode, 2)
    t0 = time.perf_counter()
    canonical = "+".join(atoms)
    key = (family, canonical, seed_a, seed_b)
    cached = _EVAL_CACHE.get(key)
    if cached is not None:
        _TIME_STATS["operator_seconds"] += time.perf_counter() - t0
        _TIME_STATS["attempts"] += 1
        _TIME_STATS["cache_hits"] += 1
        effect_1, effect_2 = cached
        return Attempt(
            operator=canonical, cost_credits=cost, valid=True,
            effect_1=effect_1, effect_2=effect_2,
            mean_effect=round((effect_1 + effect_2) / 2.0, 6),
            discovery=bool(effect_1 >= threshold and effect_2 >= threshold))
    try:
        transformer = program_transformer(program)
        base_a = _baseline_accuracy(family, seed_a)
        base_b = _baseline_accuracy(family, seed_b)
        acc_a = _cv_accuracy(family, transformer, seed_a)
        acc_b = _cv_accuracy(family, clone(transformer), seed_b)
    except Exception:  # noqa: BLE001 - a broken program is an invalid attempt
        _TIME_STATS["operator_seconds"] += time.perf_counter() - t0
        _TIME_STATS["attempts"] += 1
        _TIME_STATS["evaluations"] += 1
        return Attempt(
            operator=program, cost_credits=cost, valid=False,
            effect_1=0.0, effect_2=0.0, mean_effect=0.0, discovery=False)
    _TIME_STATS["operator_seconds"] += time.perf_counter() - t0
    _TIME_STATS["attempts"] += 1
    _TIME_STATS["evaluations"] += 1

    effect_1 = round(acc_a - base_a, 6)
    effect_2 = round(acc_b - base_b, 6)
    _EVAL_CACHE[key] = (effect_1, effect_2)
    discovery = effect_1 >= threshold and effect_2 >= threshold
    return Attempt(
        operator=canonical,
        cost_credits=cost,
        valid=True,
        effect_1=effect_1,
        effect_2=effect_2,
        mean_effect=round((effect_1 + effect_2) / 2.0, 6),
        discovery=bool(discovery),
    )


def environment_metadata() -> dict[str, Any]:
    import platform

    shapes = {}
    for fam in ALL_FAMILIES:
        X, y = _dataset(fam)
        shapes[fam] = {
            "n_rows": int(X.shape[0]),
            "n_features": int(X.shape[1]),
            "n_classes": int(len(set(y.tolist()))),
        }
    return {
        "environment_version": WORKLOAD_VERSION,
        "task_suite_version": TASK_SUITE_VERSION,
        "discovery_gate_version": DISCOVERY_GATE_VERSION,
        "families": list(ALL_FAMILIES),
        "held_out_family": HELD_OUT_FAMILY,
        "ground_truth": None,
        "promotion_threshold": DISCOVERY_MARGIN,
        "operators": list(candidates.ATOMS),
        "operator_costs": {a: candidates.program_cost(a) for a in candidates.ATOMS},
        "workload_metadata": {
            "name": WORKLOAD_NAME,
            "base_estimator": "StandardScaler->LogisticRegression",
            "baseline_params": BASELINE_PARAMS,
            "discovery_margin_absolute": DISCOVERY_MARGIN,
            "nominal_costs_flat": False,
            "grammar_version": candidates.GRAMMAR_VERSION,
            "max_program_length": candidates.MAX_PROGRAM_LENGTH,
            "search_space_size": candidates.space_size(),
            "search_space_is_closed": True,
            "cv_folds": _CV_FOLDS,
            "replicates": 2,
            "gamma_rows": GAMMA_ROWS,
            "gamma_subsample_seed": GAMMA_SUBSAMPLE_SEED,
            "repeated_attempts_identical": True,
            "dataset_shapes": shapes,
            "sklearn_version": sklearn.__version__,
            "numpy_version": np.__version__,
            "python_version": platform.python_version(),
            "measured_operator_seconds": round(_TIME_STATS["operator_seconds"], 2),
            "measured_attempts": int(_TIME_STATS["attempts"]),
        },
    }


__all__ = [
    "WORKLOAD_NAME",
    "WORKLOAD_VERSION",
    "TASK_SUITE_VERSION",
    "DISCOVERY_GATE_VERSION",
    "TASK_FAMILIES",
    "HELD_OUT_FAMILY",
    "ALL_FAMILIES",
    "BASELINE_PARAMS",
    "DISCOVERY_MARGIN",
    "GAMMA_ROWS",
    "GAMMA_SUBSAMPLE_SEED",
    "ATOM_FACTORIES",
    "operators",
    "operator_cost",
    "program_transformer",
    "run_attempt",
    "timing_stats",
    "reset_timing_stats",
    "environment_metadata",
    "TransformerMixin",
]
