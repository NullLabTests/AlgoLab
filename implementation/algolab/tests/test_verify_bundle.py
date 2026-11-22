"""Tests for the independent bundle-reproduction verifier.

``scripts/verify_bundle.py`` is the artifact that lets a reviewer re-run a
sealed experiment from a clean process. Its correctness claims need their own
tests, because a verifier that quietly accepts anything is worse than no
verifier:

- a bundle whose bytes were altered must fail the integrity check;
- workload recovery for pre-``workload`` manifests must be evidence-based, and
  must refuse to guess when the evidence is ambiguous;
- the numeric comparison must catch value changes while tolerating documented
  additive metadata and wall-clock fields;
- the additivity allow-list must apply only to the exact registered path, never
  to a subtree or to a value change.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "verify_bundle.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_bundle_under_test",
                                                  SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify = _load()


class TestChecksumIntegrity:
    def test_untouched_bundle_passes(self, tmp_path) -> None:
        bundle = tmp_path / "b"
        bundle.mkdir()
        (bundle / "statistics.json").write_text("{}\n")
        digest = hashlib.sha256((bundle / "statistics.json").read_bytes()
                                ).hexdigest()
        (bundle / "checksums.json").write_text(
            json.dumps({"statistics.json": digest}))
        result = verify.verify_checksums(bundle)
        assert result["pass"] is True
        assert result["files"] == 1

    def test_modified_artifact_fails(self, tmp_path) -> None:
        bundle = tmp_path / "b"
        bundle.mkdir()
        (bundle / "statistics.json").write_text("{}\n")
        digest = hashlib.sha256((bundle / "statistics.json").read_bytes()
                                ).hexdigest()
        (bundle / "checksums.json").write_text(
            json.dumps({"statistics.json": digest}))
        (bundle / "statistics.json").write_text('{"tampered": true}\n')
        result = verify.verify_checksums(bundle)
        assert result["pass"] is False
        assert any("MISMATCH" in p for p in result["problems"])

    def test_missing_artifact_fails(self, tmp_path) -> None:
        bundle = tmp_path / "b"
        bundle.mkdir()
        (bundle / "checksums.json").write_text(
            json.dumps({"gone.json": "0" * 64}))
        result = verify.verify_checksums(bundle)
        assert result["pass"] is False
        assert any("MISSING" in p for p in result["problems"])

    def test_bundle_without_checksums_is_a_verification_error(
            self, tmp_path) -> None:
        with pytest.raises(verify.VerificationError):
            verify.verify_checksums(tmp_path)


class TestWorkloadRecovery:
    def test_explicit_workload_wins(self) -> None:
        assert verify.infer_workload({"workload": "compose"}) == "compose"

    def test_historical_toy_manifest_is_recovered(self) -> None:
        manifest = json.loads(
            (REPO_ROOT / "experiments" / "protocol-230-v1" /
             "manifest.json").read_text())
        assert "workload" not in manifest
        assert verify.infer_workload(manifest) == "toy"

    def test_ambiguous_identity_refuses_to_guess(self) -> None:
        with pytest.raises(verify.VerificationError):
            verify.infer_workload({
                "environment_version": "9.9.9",
                "task_suite_version": "9.9.9",
                "held_out_family": "nope",
                "operators": [],
            })


class TestNumericComparison:
    def test_float_tolerance_is_1e_9(self) -> None:
        assert verify.compare_values({"x": 1.0}, {"x": 1.0 + 1e-12}) == []
        problems = verify.compare_values({"x": 1.0}, {"x": 1.0 + 1e-6})
        assert problems

    def test_missing_committed_field_is_always_a_failure(self) -> None:
        problems = verify.compare_values({"a": 1, "b": 2}, {"a": 1})
        assert problems and "missing" in problems[0]

    def test_additive_field_allowlisted_by_exact_path(self) -> None:
        additions: list[str] = []
        problems = verify.compare_values(
            {"experiment_id": "x"}, {"experiment_id": "x", "workload": "toy"},
            "manifest.json", allowed_additions=additions)
        assert problems == []
        assert additions == ["manifest.json.workload"]

    def test_unregistered_additive_field_is_a_failure(self) -> None:
        problems = verify.compare_values(
            {"a": 1}, {"a": 1, "surprise": 2}, "manifest.json")
        assert problems and "unexpected" in problems[0]

    def test_allow_list_does_not_hide_a_changed_shared_value(self) -> None:
        problems = verify.compare_values(
            {"workload": "toy"}, {"workload": "compose"}, "manifest.json")
        assert problems

    def test_volatile_fields_are_stripped_and_reported(self) -> None:
        payload = {"created_at": "2026-01-01", "x": 1,
                   "compute": {"evaluation_seconds": 12.5,
                               "evaluations": 7},
                   "nested": {"measured_operator_seconds": 3.5}}
        excluded: list[str] = []
        stripped = verify._strip_volatile(payload, excluded)
        assert stripped == {"x": 1, "compute": {"evaluations": 7},
                            "nested": {}}
        assert "created_at" in excluded
        assert "compute.evaluation_seconds" in excluded
        assert "nested.measured_operator_seconds" in excluded

    def test_interpreter_version_is_volatile_but_library_versions_are_not(
            self) -> None:
        payload = {
            "workload_metadata": {
                "python_version": "3.14.4",
                "numpy_version": "2.5.2",
                "sklearn_version": "1.9.0",
            }
        }
        excluded: list[str] = []
        stripped = verify._strip_volatile(payload, excluded)
        assert stripped == {
            "workload_metadata": {
                "numpy_version": "2.5.2",
                "sklearn_version": "1.9.0",
            }
        }
        assert excluded == ["workload_metadata.python_version"]
        assert verify.compare_values(
            {"workload_metadata": {"numpy_version": "2.5.2"}},
            {"workload_metadata": {"numpy_version": "2.4.6"}},
        ) != []

    def test_bool_is_not_compared_as_a_number(self) -> None:
        assert verify.compare_values(True, True) == []
        assert verify.compare_values(True, 1)
