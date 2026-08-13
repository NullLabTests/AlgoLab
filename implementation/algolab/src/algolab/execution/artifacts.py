"""Run artifact store (M1; layout documented in ``docs/ARTIFACT_FORMAT.md``).

Each run owns a directory ``<artifacts_dir>/runs/<RUN_ID>/``. Files written
by the worker before execution are immutable afterwards; ``metrics.json`` is
written by the workload subprocess itself; ``artifact_manifest.json`` is
written last and captures a sha256 per file. Recovery re-verifies hashes
before trusting artifacts.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import platform
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from algolab.control.config import AlgolabConfig

MANIFEST_FILES: tuple[str, ...] = (
    "manifest.json",
    "resolved_config.json",
    "environment.json",
    "stdout.log",
    "stderr.log",
    "metrics.json",
    "resource_usage.json",
    "artifact_manifest.json",
    "completion.json",
)

_ARTIFACT_MANIFEST_VERSION = "1.0.0"
_COMPLETION_VERSION = "1.0.0"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def hash_file(path: Path) -> str:
    """sha256 of a file, streamed."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RunArtifacts:
    """One run's artifact directory and its metadata files."""

    def __init__(self, base_dir: Path, run_id: str) -> None:
        self.base_dir = base_dir
        self.run_id = run_id
        self.dir = base_dir / "runs" / run_id

    def create(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)

    # -- reads / writes ---------------------------------------------------

    def write_json(self, name: str, data: dict[str, Any]) -> Path:
        path = self.dir / name
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
        return path

    def read_json(self, name: str) -> dict[str, Any]:
        with open(self.dir / name, encoding="utf-8") as fh:
            value = json.load(fh)
        assert isinstance(value, dict)
        return value

    def file_exists(self, name: str) -> bool:
        return (self.dir / name).is_file()

    def total_size(self) -> int:
        return sum(
            p.stat().st_size for p in self.dir.rglob("*") if p.is_file()
        )

    # -- snapshots --------------------------------------------------------

    def write_environment_snapshot(self, config: AlgolabConfig,
                                   workload_version: str) -> None:
        """Pin the environment before the workload launches."""
        env: dict[str, str] = {}
        for key in config.execution.env_allowlist:
            value = __import__("os").environ.get(key)
            if value is not None:
                env[key] = value
        snapshot = {
            "schema_version": "1.0.0",
            "captured_at": _utc_now(),
            "python": {
                "executable": sys.executable,
                "version": sys.version,
            },
            "platform": platform.platform(),
            "sqlite_version": sqlite3.sqlite_version,
            "workload": {"name": config.execution.workload,
                         "version": workload_version},
            "env_allowlist": env,
        }
        self.write_json("environment.json", snapshot)

    # -- manifests --------------------------------------------------------

    def write_artifact_manifest(self) -> None:
        """Hash every file in the run directory; written once, last."""
        entries = []
        for path in sorted(self.dir.rglob("*")):
            if not path.is_file() or path.name == "artifact_manifest.json":
                continue
            rel = path.relative_to(self.dir).as_posix()
            media_type = (
                mimetypes.guess_type(path.name)[0]
                or "application/octet-stream"
            )
            entries.append({
                "path": rel,
                "size": path.stat().st_size,
                "sha256": hash_file(path),
                "media_type": media_type,
                "created_at": _utc_now(),
            })
        self.write_json("artifact_manifest.json", {
            "schema_version": _ARTIFACT_MANIFEST_VERSION,
            "run_id": self.run_id,
            "artifacts": entries,
        })

    def write_completion(self, *, status: str, error_code: str | None,
                         exit_code: int | None, started_at: str,
                         finished_at: str, credits: float, cost: float,
                         reservation_id: str | None) -> None:
        """Final run record; written after the artifact manifest."""
        self.write_json("completion.json", {
            "schema_version": _COMPLETION_VERSION,
            "run_id": self.run_id,
            "status": status,
            "error_code": error_code,
            "exit_code": exit_code,
            "started_at": started_at,
            "finished_at": finished_at,
            "credits": credits,
            "cost": cost,
            "reservation_id": reservation_id,
        })

    def verify_manifest(self) -> bool:
        """Re-hash all files listed in ``artifact_manifest.json``."""
        try:
            manifest = self.read_json("artifact_manifest.json")
        except (OSError, json.JSONDecodeError):
            return False
        entries = manifest.get("artifacts")
        if not isinstance(entries, list):
            return False
        for entry in entries:
            path = entry.get("path")
            expected = entry.get("sha256")
            if not isinstance(path, str) or not isinstance(expected, str):
                return False
            file_path = self.dir / path
            if not file_path.is_file() or hash_file(file_path) != expected:
                return False
        return True
