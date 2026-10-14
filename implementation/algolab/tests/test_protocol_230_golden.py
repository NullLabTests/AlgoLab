"""Golden regression guard: the generalized harness must reproduce the
committed protocol-230-v1 artifact bundle.

This enforces the protocol 231 guarantee that adding the cost-aware arms did
not alter any pre-registered v1 behavior (spec/research/
231_COST_AWARE_SELECTION.md §7).

Reproducibility contract (honest version):

- The raw per-attempt condition streams are exact integers/clipped values and
  are compared **byte-for-byte**.
- ``report.md`` formats numbers to a fixed number of digits and is compared
  **byte-for-byte**.
- JSON artifacts (``statistics.json``, ``held-out-statistics.json``, and the
  recorded ``environment.json`` / ``protocol.json`` / ``knowledge-snapshot.json``)
  are compared **numerically** with a tight tolerance. The derived statistics
  are full-precision floats produced by bootstrap/permutation routines; their
  last significant digit depends on the BLAS/libm/Python build, so byte
  equality is only guaranteed on the environment that sealed the bundle. A
  changed arm, count, structure, or an effect outside 1e-9 relative is still
  caught. (Recorded as defect D-10 in docs/audits/initial-audit.md.)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from algolab.search import ExperimentConfig, PolicyComparison
from algolab.storage.db import connect

ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "experiments" / "protocol-230-v1"

# Deterministic given the manifest integers, but formatted by hand -> byte-exact.
BYTE_EXACT_FILES = ("report.md",)

# Fully deterministic given the manifest integers, but carrying full-precision
# derived floats -> compared numerically (see module docstring).
NUMERIC_JSON_FILES = (
    "statistics.json",
    "held-out-statistics.json",
    "knowledge-snapshot.json",
    "environment.json",
    "protocol.json",
)

_REL_TOL = 1e-9
_ABS_TOL = 1e-9


def _regenerate_v1(tmp: Path) -> Path:
    cfg = ExperimentConfig(experiment_id="protocol-230-v1")
    conn = connect(":memory:", initialize=True)
    comp = PolicyComparison(cfg, conn, tmp / "art")
    results = comp.run()
    stats = comp.analyze(results)
    held_out = comp.analyze_held_out(comp.run_held_out())
    held_out["claim_readiness"] = PolicyComparison.evaluate_claim(
        stats.get("per_family", {}), held_out)
    comp.write_report(results, stats, held_out)
    comp.write_artifact_bundle(stats, held_out)
    return tmp / "art"


def _assert_numerically_equal(a: Any, b: Any, path: str) -> None:
    if isinstance(a, bool) or isinstance(b, bool):
        assert a == b, f"{path}: {a!r} != {b!r}"
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        assert math.isclose(a, b, rel_tol=_REL_TOL, abs_tol=_ABS_TOL), \
            f"{path}: {a!r} != {b!r}"
    elif isinstance(a, dict) and isinstance(b, dict):
        assert set(a) == set(b), f"{path}: keys {set(a)} != {set(b)}"
        for k in a:
            _assert_numerically_equal(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list):
        assert len(a) == len(b), f"{path}: len {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            _assert_numerically_equal(x, y, f"{path}[{i}]")
    else:
        assert a == b, f"{path}: {a!r} != {b!r}"


class TestV1GoldenBundle:
    def test_byte_exact_artifacts_match_committed_bytes(
            self, tmp_path) -> None:
        art = _regenerate_v1(tmp_path)
        for name in BYTE_EXACT_FILES:
            assert (art / name).read_bytes() == \
                (ARTIFACT_DIR / name).read_bytes(), name

    def test_json_artifacts_match_committed_values(
            self, tmp_path) -> None:
        art = _regenerate_v1(tmp_path)
        for name in NUMERIC_JSON_FILES:
            regenerated = json.loads((art / name).read_text())
            committed = json.loads((ARTIFACT_DIR / name).read_text())
            _assert_numerically_equal(regenerated, committed, name)

    def test_all_condition_streams_match_committed_bytes(
            self, tmp_path) -> None:
        art = _regenerate_v1(tmp_path)
        committed_streams = sorted(ARTIFACT_DIR.glob("conditions/*/*.jsonl"))
        assert committed_streams
        for p in committed_streams:
            rel = p.relative_to(ARTIFACT_DIR)
            assert (art / rel).read_bytes() == p.read_bytes(), str(rel)
