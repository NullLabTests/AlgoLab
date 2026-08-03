"""CLI entry point: init-db, validate-manifest, budget-state."""

import json
import os
import subprocess
import sys
from pathlib import Path

from algolab.cli.main import main
from tests.conftest import make_hypothesis


def _run(
    args: list[str], cwd: Path, env: dict[str, str]
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "algolab.cli", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_init_db_creates_database(tmp_path) -> None:
    db = tmp_path / "algolab.sqlite3"
    code = main(["init-db", "--path", str(db)])
    assert code == 0
    assert db.exists()

    import sqlite3

    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert {"events", "entities", "ledger_entries", "reservations"} <= tables


def test_validate_manifest_valid_file(tmp_path) -> None:
    manifest = tmp_path / "hyp.json"
    manifest.write_text(
        json.dumps(make_hypothesis().model_dump(mode="json"))
    )
    code = main(["validate-manifest", "--type", "hypothesis",
                 "--file", str(manifest)])
    assert code == 0


def test_validate_manifest_invalid_file(tmp_path, capsys) -> None:
    manifest = tmp_path / "hyp.json"
    manifest.write_text(json.dumps({"id": "HYP-12345678"}))
    code = main(["validate-manifest", "--type", "hypothesis",
                 "--file", str(manifest)])
    assert code == 1
    assert "invalid hypothesis manifest" in capsys.readouterr().err


def test_validate_manifest_missing_file(tmp_path, capsys) -> None:
    code = main(["validate-manifest", "--type", "hypothesis",
                 "--file", str(tmp_path / "nope.json")])
    assert code == 2


def test_budget_state_empty_ledger(tmp_path, capsys) -> None:
    db = tmp_path / "algolab.sqlite3"
    main(["init-db", "--path", str(db)])
    code = main(["budget-state", "--path", str(db)])
    assert code == 0
    out = capsys.readouterr().out
    assert "available_credits: 0.0" in out
    assert "audit events: 0" in out


def test_entry_point_via_subprocess(tmp_path) -> None:
    """The installed entry point works end-to-end (reproducible commands)."""
    src = Path(__file__).resolve().parents[1] / "src"
    env = {**os.environ, "PYTHONPATH": str(src)}
    db = tmp_path / "algolab.sqlite3"
    result = _run(["init-db", "--path", str(db)], cwd=tmp_path, env=env)
    assert result.returncode == 0, result.stderr
    assert db.exists()
    result2 = _run(["budget-state", "--path", str(db)], cwd=tmp_path, env=env)
    assert result2.returncode == 0
    assert "available_credits" in result2.stdout
