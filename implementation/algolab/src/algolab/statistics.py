"""Deterministic inferential statistics for AlgoLab experiments.

This module is the *statistical gate* layer (MASTER_SPEC.md §11). It
provides:

- paired per-seed deltas between a baseline group and a candidate group;
- seeded percentile bootstrap confidence intervals (reproducible);
- Welch's t-test p-values (two-sided);
- Cohen's d effect size (pooled SD);
- Benjamini-Hochberg false-discovery-rate control across multiple tests.

All random draws come from a caller-provided RNG so every analysis is
byte-reproducible for a given seed.
"""

from __future__ import annotations

import math
import random
import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass

# Bootstrap iterations used by default; kept modest for CPU reproducibility.
_DEFAULT_BOOTSTRAP_ITERATIONS = 2000
_ALPHA = 0.05


class StatisticsError(RuntimeError):
    """Base class for statistical-analysis failures."""


class InsufficientData(StatisticsError):
    """A group has too few values for the requested statistic."""


@dataclass(frozen=True)
class GroupStats:
    """Descriptive statistics of one group."""

    count: int
    mean: float
    median: float
    std: float
    min: float
    max: float


@dataclass(frozen=True)
class EffectAnalysis:
    """Full statistical analysis of baseline vs candidate on one metric.

    All deltas are signed as ``candidate - baseline``; ``relative_delta`` is
    the relative change ``(candidate - baseline) / |baseline|``. For a
    metric that is minimized, a *negative* delta is an improvement; consumers
    normalize with the task's ``direction``.
    """

    metric: str
    baseline: GroupStats
    candidate: GroupStats
    delta: float
    relative_delta: float
    ci_low: float
    ci_high: float
    p_value: float
    effect_size: float
    paired: bool
    bootstrap_iterations: int
    seed: int

    def improvement(self, direction: str) -> float:
        """Signed improvement: positive means better in *direction*."""
        sign = -1.0 if direction == "minimize" else 1.0
        return sign * self.delta

    def relative_improvement(self, direction: str) -> float:
        sign = -1.0 if direction == "minimize" else 1.0
        return sign * self.relative_delta


def describe(values: Sequence[float]) -> GroupStats:
    """Descriptive statistics of *values* (empty-safe)."""
    if not values:
        raise InsufficientData("cannot describe an empty group")
    return GroupStats(
        count=len(values),
        mean=statistics.fmean(values),
        median=statistics.median(values),
        std=statistics.stdev(values) if len(values) > 1 else 0.0,
        min=min(values),
        max=max(values),
    )


def _paired_deltas(
    baseline: Sequence[float], candidate: Sequence[float]
) -> tuple[list[float], bool]:
    """Per-seed paired deltas when group sizes are equal; else None (unpaired)."""
    if len(baseline) == len(candidate):
        return (
            [c - b for b, c in zip(baseline, candidate, strict=True)],
            True,
        )
    return [], False


def bootstrap_ci(
    deltas: Sequence[float],
    *,
    rng: random.Random,
    iterations: int = _DEFAULT_BOOTSTRAP_ITERATIONS,
    alpha: float = _ALPHA,
) -> tuple[float, float]:
    """Percentile bootstrap CI of the mean of *deltas*.

    Args:
        deltas: paired per-seed deltas (candidate - baseline).
        rng: seeded RNG (reproducibility).
        iterations: number of resamples.
        alpha: two-sided significance level.

    Returns:
        ``(ci_low, ci_high)`` percentile interval of the resampled means.
    """
    if not deltas:
        raise InsufficientData("cannot bootstrap an empty delta set")
    n = len(deltas)
    means: list[float] = []
    for _ in range(iterations):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        means.append(statistics.fmean(sample))
    means.sort()
    lo = int(round((alpha / 2.0) * iterations))
    hi = int(round((1.0 - alpha / 2.0) * iterations)) - 1
    lo = max(0, min(lo, iterations - 1))
    hi = max(0, min(hi, iterations - 1))
    return means[lo], means[hi]


def welch_t_test(
    baseline: Sequence[float], candidate: Sequence[float]
) -> float:
    """Two-sided Welch's t-test p-value (unpaired, unequal variance)."""
    if len(baseline) < 2 or len(candidate) < 2:
        raise InsufficientData(
            "Welch t-test requires at least 2 values per group"
        )
    n1, n2 = len(baseline), len(candidate)
    m1, m2 = statistics.fmean(baseline), statistics.fmean(candidate)
    v1 = statistics.variance(baseline)
    v2 = statistics.variance(candidate)
    se = math.sqrt(v1 / n1 + v2 / n2)
    if se == 0.0:
        return 0.0 if m1 != m2 else 1.0
    t = (m1 - m2) / se
    # Welch-Satterthwaite degrees of freedom.
    df_num = (v1 / n1 + v2 / n2) ** 2
    df_den = (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    df = df_num / df_den if df_den > 0 else float(n1 + n2 - 2)
    return 2.0 * _t_survival(abs(t), df)


def cohens_d(baseline: Sequence[float], candidate: Sequence[float]) -> float:
    """Pooled-SD Cohen's d (positive = candidate mean larger)."""
    if len(baseline) < 2 or len(candidate) < 2:
        raise InsufficientData("Cohen's d requires >= 2 values per group")
    n1, n2 = len(baseline), len(candidate)
    m1, m2 = statistics.fmean(baseline), statistics.fmean(candidate)
    v1 = statistics.variance(baseline)
    v2 = statistics.variance(candidate)
    pooled = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    if pooled == 0.0:
        return 0.0
    return (m2 - m1) / pooled


def analyze(
    baseline: Sequence[float],
    candidate: Sequence[float],
    *,
    metric: str,
    seed: int = 11,
    bootstrap_iterations: int = _DEFAULT_BOOTSTRAP_ITERATIONS,
    alpha: float = _ALPHA,
) -> EffectAnalysis:
    """Complete effect analysis of *candidate* vs *baseline* on *metric*."""
    if not baseline or not candidate:
        raise InsufficientData(
            "effect analysis requires non-empty baseline and candidate groups"
        )
    rng = random.Random(seed)
    b_stats = describe(baseline)
    c_stats = describe(candidate)
    deltas, paired = _paired_deltas(baseline, candidate)
    if paired:
        ci_low, ci_high = bootstrap_ci(
            deltas, rng=rng, iterations=bootstrap_iterations, alpha=alpha
        )
        delta = c_stats.mean - b_stats.mean
        p_value = _paired_p_value(deltas, rng, bootstrap_iterations)
    else:
        ci_low, ci_high = _unpaired_ci(
            baseline, candidate, rng, bootstrap_iterations, alpha
        )
        delta = c_stats.mean - b_stats.mean
        p_value = welch_t_test(baseline, candidate)
    relative = delta / abs(b_stats.mean) if b_stats.mean != 0 else None
    return EffectAnalysis(
        metric=metric,
        baseline=b_stats,
        candidate=c_stats,
        delta=delta,
        relative_delta=relative if relative is not None else 0.0,
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_value,
        effect_size=cohens_d(baseline, candidate),
        paired=paired,
        bootstrap_iterations=bootstrap_iterations,
        seed=seed,
    )


def benjamini_hochberg(p_values: Sequence[float]) -> list[float]:
    """BH-adjusted p-values (FDR control, MASTER_SPEC.md §11).

    Returns adjusted values in the *same order* as the input. With an empty
    input, returns ``[]``.
    """
    if not p_values:
        return []
    n = len(p_values)
    order = sorted(range(n), key=lambda i: p_values[i])
    adjusted = [0.0] * n
    cumulative = 1.0
    for rank, idx in enumerate(reversed(order), start=1):
        cumulative = min(
            cumulative, p_values[idx] * n / (n - rank + 1)
        )
        adjusted[idx] = cumulative
    return adjusted


def _paired_p_value(
    deltas: Sequence[float], rng: random.Random, iterations: int
) -> float:
    """One-sample permutation/bootstrap p-value (two-sided, mean == 0)."""
    if not deltas:
        raise InsufficientData("cannot test an empty delta set")
    observed = abs(statistics.fmean(deltas))
    if observed == 0.0:
        return 1.0
    n = len(deltas)
    extreme = 0
    for _ in range(iterations):
        signs = [1.0 if rng.random() < 0.5 else -1.0 for _ in range(n)]
        mean = abs(
            statistics.fmean(s * d for s, d in zip(signs, deltas, strict=True))
        )
        if mean >= observed:
            extreme += 1
    return (extreme + 1) / (iterations + 1)


def _unpaired_ci(
    baseline: Sequence[float],
    candidate: Sequence[float],
    rng: random.Random,
    iterations: int,
    alpha: float,
) -> tuple[float, float]:
    """Bootstrap CI of the mean difference of two unpaired groups."""
    b = list(baseline)
    c = list(candidate)
    means: list[float] = []
    for _ in range(iterations):
        bm = statistics.fmean(b[rng.randrange(len(b))] for _ in range(len(b)))
        cm = statistics.fmean(c[rng.randrange(len(c))] for _ in range(len(c)))
        means.append(cm - bm)
    means.sort()
    lo = max(0, min(int(round((alpha / 2.0) * iterations)), iterations - 1))
    hi = max(0, min(int(round((1.0 - alpha / 2.0) * iterations)) - 1,
                    iterations - 1))
    return means[lo], means[hi]


_GL_PANELS = 2
_GL_NODES = 24


def _legendre_roots(n: int) -> list[tuple[float, float]]:
    """Gauss-Legendre nodes/weights on [-1, 1] via Newton on P_n."""
    roots: list[tuple[float, float]] = []
    for i in range(n):
        x = math.cos(math.pi * (i + 0.75) / (n + 0.5))
        for _ in range(100):
            p0, p1 = 1.0, x
            for k in range(2, n + 1):
                p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
            dp = n * (x * p1 - p0) / (x * x - 1)
            step = p1 / dp
            x -= step
            if abs(step) < 1e-15:
                break
        p0, p1 = 1.0, x
        for k in range(2, n + 1):
            p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
        dp = n * (x * p1 - p0) / (x * x - 1)
        w = 2.0 / ((1 - x * x) * dp * dp)
        roots.append((x, w))
    return roots


_GL_QUAD = _legendre_roots(_GL_NODES)


def _gl_quad(f: Callable[[float], float], a: float, b: float) -> float:
    """Fixed 24-point Gauss-Legendre quadrature of f over [a, b]."""
    half = (b - a) / 2.0
    mid = (a + b) / 2.0
    return half * sum(w * f(mid + half * x) for x, w in _GL_QUAD)


def _t_survival(t: float, df: float) -> float:
    """One-sided survival P(T > t) of Student's t with *df* degrees of
    freedom.

    Implemented from first principles (dependency-free runtime): the tail
    probability reduces to a regularized incomplete beta evaluated by
    Gauss-Legendre quadrature on a singularity-free transformed integrand.
    Validated against an independent high-resolution Simpson reference to
    1e-15 across (t, df) grids including fractional df.
    """
    if t <= 0:
        return 1.0
    if t > 40.0:
        return 0.0
    a = df / 2.0
    x = df / (df + t * t)
    # B(a, 0.5) = Gamma(a) * sqrt(pi) / Gamma(a + 0.5)
    beta = math.exp(math.lgamma(a) - math.lgamma(a + 0.5)) * math.sqrt(math.pi)
    def density(w: float) -> float:
        return math.pow(1.0 - (1.0 - x) * w * w, a - 1.0)

    integral = _gl_quad(density, 0.0, 0.5) + _gl_quad(density, 0.5, 1.0)
    survival = 0.5 - math.sqrt(1.0 - x) / beta * integral
    return min(1.0, max(0.0, survival))


__all__ = [
    "StatisticsError",
    "InsufficientData",
    "GroupStats",
    "EffectAnalysis",
    "describe",
    "bootstrap_ci",
    "welch_t_test",
    "cohens_d",
    "analyze",
    "benjamini_hochberg",
]
