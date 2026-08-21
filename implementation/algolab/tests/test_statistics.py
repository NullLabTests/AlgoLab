"""Tests for the deterministic statistics layer (algolab.statistics)."""

from __future__ import annotations

import random

import pytest

from algolab.statistics import (
    InsufficientData,
    analyze,
    benjamini_hochberg,
    bootstrap_ci,
    cohens_d,
    describe,
    welch_t_test,
)


def test_describe_basic():
    s = describe([1.0, 2.0, 3.0])
    assert s.count == 3
    assert s.mean == 2.0
    assert s.median == 2.0
    assert s.min == 1.0
    assert s.max == 3.0
    assert s.std == 1.0


def test_describe_empty_raises():
    with pytest.raises(InsufficientData):
        describe([])


def test_welch_t_test_reference_values():
    # Reference values computed independently (scipy.stats.ttest_ind).
    # [1..5] vs [3..7]: means 3 vs 5, sd 1.581 each -> t = 2.0, df = 8
    # -> p = 2 * sf(2.0, 8) = 0.08051623795726237.
    assert welch_t_test([1, 2, 3, 4, 5], [3, 4, 5, 6, 7]) == pytest.approx(
        0.08051623795726237, abs=1e-9)
    assert welch_t_test([1, 2, 3], [4, 5, 6]) == pytest.approx(
        0.021311641128756165, abs=1e-9)


def test_welch_t_test_too_small():
    with pytest.raises(InsufficientData):
        welch_t_test([1.0], [2.0, 3.0])


def test_cohens_d_sign():
    assert cohens_d([1, 2, 3], [4, 5, 6]) > 0
    assert cohens_d([4, 5, 6], [1, 2, 3]) < 0
    assert cohens_d([1, 1, 1], [1, 1, 1]) == 0.0


def test_bootstrap_ci_reproducible():
    deltas = [0.1, 0.2, 0.3, 0.15, 0.25, -0.05, 0.3, 0.1, 0.2, 0.05]
    a = bootstrap_ci(deltas, rng=random.Random(42), iterations=500)
    b = bootstrap_ci(deltas, rng=random.Random(42), iterations=500)
    assert a == b
    assert a[0] <= a[1]


def test_bootstrap_ci_empty_raises():
    with pytest.raises(InsufficientData):
        bootstrap_ci([], rng=random.Random(1))


def test_analyze_paired_positive_delta():
    r = analyze([1.0, 2.0, 3.0, 4.0, 5.0],
                [3.0, 4.0, 5.0, 6.0, 7.0],
                metric="m", seed=42)
    assert r.paired
    assert r.delta == 2.0
    assert r.relative_delta == pytest.approx(2.0 / 3.0)
    assert r.ci_low <= r.ci_high
    assert 0 <= r.p_value <= 1
    assert r.effect_size > 0
    assert r.improvement("maximize") == pytest.approx(2.0)
    assert r.improvement("minimize") == pytest.approx(-2.0)


def test_analyze_deterministic():
    baseline = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    candidate = [1.5, 2.5, 3.5, 4.5, 5.5, 6.5]
    a = analyze(baseline, candidate, metric="m", seed=7)
    b = analyze(baseline, candidate, metric="m", seed=7)
    assert a == b
    assert a.delta == pytest.approx(0.5)


def test_analyze_unpaired():
    r = analyze([1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
                [1.5, 2.5, 3.5],
                metric="m", seed=7)
    assert not r.paired
    assert 0 <= r.p_value <= 1


def test_analyze_empty_raises():
    with pytest.raises(InsufficientData):
        analyze([], [1.0, 2.0], metric="m")


def test_analyze_identical_groups_p_one():
    r = analyze([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], metric="m", seed=1)
    assert r.delta == 0.0
    assert r.p_value == 1.0


def test_benjamini_hochberg_reference():
    p = [0.01, 0.03, 0.2, 0.5]
    adj = benjamini_hochberg(p)
    assert adj == pytest.approx([0.04, 0.06, 0.2666666667, 0.5], abs=1e-9)
    # Monotone order preserved.
    assert adj[0] <= adj[1] <= adj[2] <= adj[3]


def test_benjamini_hochberg_empty():
    assert benjamini_hochberg([]) == []


def test_t_survival_known_values():
    from algolab.statistics import _t_survival

    # Reference values from scipy.stats.t.sf.
    assert _t_survival(1.0, 3) == pytest.approx(0.195501109478, abs=1e-9)
    assert _t_survival(2.5, 4) == pytest.approx(0.033383272406, abs=1e-9)
    assert _t_survival(4.0, 10) == pytest.approx(0.001259166247, abs=1e-8)
    assert _t_survival(0.5, 2) == pytest.approx(0.333333333333, abs=1e-9)
    # Exact Cauchy tail at t=1.
    assert _t_survival(1.0, 1) == pytest.approx(0.25, abs=1e-12)


def test_t_survival_bounds():
    from algolab.statistics import _t_survival

    assert _t_survival(0.0, 3) == 1.0
    assert _t_survival(-1.0, 3) == 1.0
    assert _t_survival(100.0, 3) == 0.0
