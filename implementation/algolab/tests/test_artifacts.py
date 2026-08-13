"""Artifact store: layout, hashing, manifest immutability, verification."""

import hashlib

from algolab.control.config import AlgolabConfig
from algolab.execution.artifacts import (
    MANIFEST_FILES,
    RunArtifacts,
    hash_file,
)


def _artifacts(tmp_path) -> RunArtifacts:
    return RunArtifacts(tmp_path, "RUN-ABCDEF1234")


def test_layout_and_required_files(tmp_path) -> None:
    artifacts = _artifacts(tmp_path)
    artifacts.create()
    for name in MANIFEST_FILES:
        assert not artifacts.file_exists(name)
    artifacts.write_json("resolved_config.json", {"strategy": "momentum"})
    assert (tmp_path / "runs" / "RUN-ABCDEF1234" / "resolved_config.json").is_file()


def test_hash_file_is_sha256(tmp_path) -> None:
    path = tmp_path / "blob.bin"
    path.write_bytes(b"algo lab" * 1000)
    digest = hash_file(path)
    assert len(digest) == 64
    assert digest == hashlib.sha256(b"algo lab" * 1000).hexdigest()


def test_artifact_manifest_lists_hashes(tmp_path) -> None:
    artifacts = _artifacts(tmp_path)
    artifacts.create()
    artifacts.write_json("resolved_config.json", {"dim": 8})
    artifacts.write_json("metrics.json", {"converged": True})
    artifacts.write_artifact_manifest()
    manifest = artifacts.read_json("artifact_manifest.json")
    assert manifest["run_id"] == "RUN-ABCDEF1234"
    paths = {e["path"] for e in manifest["artifacts"]}
    assert paths == {"resolved_config.json", "metrics.json"}
    entry = next(e for e in manifest["artifacts"]
                 if e["path"] == "metrics.json")
    assert entry["sha256"] == hash_file(artifacts.dir / "metrics.json")
    assert entry["size"] > 0


def test_manifest_detects_tampering(tmp_path) -> None:
    artifacts = _artifacts(tmp_path)
    artifacts.create()
    artifacts.write_json("metrics.json", {"converged": True})
    artifacts.write_artifact_manifest()
    assert artifacts.verify_manifest() is True
    artifacts.write_json("metrics.json", {"converged": False})  # tamper
    assert artifacts.verify_manifest() is False


def test_verify_fails_without_manifest(tmp_path) -> None:
    artifacts = _artifacts(tmp_path)
    artifacts.create()
    artifacts.write_json("metrics.json", {"converged": True})
    assert artifacts.verify_manifest() is False


def test_environment_snapshot_is_pinned(tmp_path) -> None:
    artifacts = _artifacts(tmp_path)
    artifacts.create()
    artifacts.write_environment_snapshot(AlgolabConfig(), "1.0.0")
    snapshot = artifacts.read_json("environment.json")
    assert snapshot["workload"]["version"] == "1.0.0"
    assert "python" in snapshot and "platform" in snapshot
    assert "ALGOLAB_RUN_ID" not in snapshot["env_allowlist"]


def test_completion_and_total_size(tmp_path) -> None:
    artifacts = _artifacts(tmp_path)
    artifacts.create()
    artifacts.write_json("resolved_config.json", {"x": 1})
    artifacts.write_completion(
        status="SUCCEEDED", error_code=None, exit_code=0,
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:00:01+00:00",
        credits=1.25, cost=0.0, reservation_id="EVT-RESERV1",
    )
    completion = artifacts.read_json("completion.json")
    assert completion["status"] == "SUCCEEDED"
    assert completion["credits"] == 1.25
    assert artifacts.total_size() > 0
