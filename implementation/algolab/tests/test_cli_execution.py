"""CLI end-to-end: init -> create -> approve -> expand -> worker -> aggregate."""

import json
import subprocess
import sys
from pathlib import Path

from tests.conftest import make_candidate, make_experiment, make_hypothesis

CLI = [sys.executable, "-m", "algolab.cli"]


def run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*CLI, "--config", "config.yaml", *args], cwd=cwd,
        capture_output=True, text=True, check=False, timeout=300,
    )


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, default=str))


def _seed_project(tmp_path: Path) -> dict:
    (tmp_path / "config.yaml").write_text(
        "storage:\n  path: db.sqlite3\n  artifacts_dir: artifacts\n"
        "producer: test\n")
    r = run_cli(tmp_path, "init-db")
    assert r.returncode == 0, r.stderr

    hyp = make_hypothesis()
    cand = make_candidate(hyp.id)
    exp = make_experiment(
        hyp.id, cand.id, seeds=[11, 23, 37], status="planned",
        budget={"max_compute_credits": 10000.0, "max_cost": 1000.0,
                "currency": "USD"})
    write_json(tmp_path / "h.json", hyp.model_dump(mode="json"))
    write_json(tmp_path / "c.json", cand.model_dump(mode="json"))
    write_json(tmp_path / "e.json", exp.model_dump(mode="json"))

    r = run_cli(tmp_path, "create-hypothesis", "--file", "h.json")
    assert r.returncode == 0, r.stderr
    r = run_cli(tmp_path, "create-candidate", "--file", "c.json")
    assert r.returncode == 0, r.stderr
    r = run_cli(tmp_path, "create-experiment", "--file", "e.json")
    assert r.returncode == 0, r.stderr
    return {"hyp": hyp.id, "cand": cand.id, "exp": exp.id}


def test_full_cli_workflow(tmp_path) -> None:
    ids = _seed_project(tmp_path)
    r = run_cli(tmp_path, "approve-experiment", ids["exp"])
    assert r.returncode == 0, r.stderr
    r = run_cli(tmp_path, "budget-grant", "--credits", "5000")
    assert r.returncode == 0, r.stderr
    r = run_cli(tmp_path, "expand-experiment", ids["exp"], "--key", "k1")
    assert r.returncode == 0, r.stderr
    assert "6" in r.stdout  # 1 baseline + 1 candidate x 3 seeds

    r = run_cli(tmp_path, "list-runs", "--json")
    assert r.returncode == 0
    runs = json.loads(r.stdout)
    assert len(runs) == 6
    assert all(run["status"] == "QUEUED" for run in runs)

    r = run_cli(tmp_path, "worker", "--poll-interval", "0.1")
    assert r.returncode == 0, r.stderr
    r = run_cli(tmp_path, "list-runs", "--status", "SUCCEEDED", "--json")
    assert len(json.loads(r.stdout)) == 6

    r = run_cli(tmp_path, "aggregate-experiment", ids["exp"], "--json")
    assert r.returncode == 0, r.stderr
    report = json.loads(r.stdout)
    assert report["run_counts"]["SUCCEEDED"] == 6
    assert "final_objective" in report["metrics"]

    r = run_cli(tmp_path, "budget-state")
    assert r.returncode == 0
    assert "charged_credits" in r.stdout
    r = run_cli(tmp_path, "audit-log", "--json")
    assert r.returncode == 0
    events = json.loads(r.stdout)
    mutations = {e["mutation"] for e in events}
    assert {"expanded", "claimed", "status_changed"} <= mutations


def test_cli_cancel_and_recovery(tmp_path) -> None:
    ids = _seed_project(tmp_path)
    run_cli(tmp_path, "approve-experiment", ids["exp"])
    run_cli(tmp_path, "budget-grant", "--credits", "5000")
    run_cli(tmp_path, "expand-experiment", ids["exp"], "--key", "k1")
    r = run_cli(tmp_path, "list-runs", "--json")
    runs = json.loads(r.stdout)
    target = runs[0]["run_id"]

    r = run_cli(tmp_path, "cancel-run", target)
    assert r.returncode == 0, r.stderr
    r = run_cli(tmp_path, "show-run", target, "--json")
    assert json.loads(r.stdout)["status"] == "CANCELLED"

    r = run_cli(tmp_path, "recover-runs", "--json")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["orphaned"] == 0


def test_cli_error_handling(tmp_path) -> None:
    (tmp_path / "config.yaml").write_text(
        "storage:\n  path: db.sqlite3\n  artifacts_dir: artifacts\n")
    run_cli(tmp_path, "init-db")
    r = run_cli(tmp_path, "approve-experiment", "EXP-NONEXISTENT")
    assert r.returncode == 1
    assert "error" in r.stdout.lower() or "error" in r.stderr.lower()

    bad = make_hypothesis()
    bad = bad.model_copy(update={"statement": 42})
    write_json(tmp_path / "bad.json", bad.model_dump())
    r = run_cli(tmp_path, "create-hypothesis", "--file", "bad.json")
    assert r.returncode == 1

    r = run_cli(tmp_path, "validate-manifest", "--type", "hypothesis",
                "--file", "bad.json")
    assert r.returncode == 1


def test_worker_is_deterministic_across_cli_invocations(tmp_path) -> None:
    ids = _seed_project(tmp_path)
    run_cli(tmp_path, "approve-experiment", ids["exp"])
    run_cli(tmp_path, "budget-grant", "--credits", "5000")
    run_cli(tmp_path, "expand-experiment", ids["exp"], "--key", "k1")
    run_cli(tmp_path, "worker", "--poll-interval", "0.1")
    r = run_cli(tmp_path, "aggregate-experiment", ids["exp"], "--json")
    first = json.loads(r.stdout)

    ids2 = _seed_project(tmp_path)
    run_cli(tmp_path, "approve-experiment", ids2["exp"])
    run_cli(tmp_path, "budget-grant", "--credits", "5000")
    run_cli(tmp_path, "expand-experiment", ids2["exp"], "--key", "k1")
    run_cli(tmp_path, "worker", "--poll-interval", "0.1")
    r = run_cli(tmp_path, "aggregate-experiment", ids2["exp"], "--json")
    second = json.loads(r.stdout)

    assert (first["metrics"]["final_objective"]["baseline"]
            == second["metrics"]["final_objective"]["baseline"])
    cand = next(iter(first["metrics"]["final_objective"]["candidates"]))
    cand2 = next(iter(second["metrics"]["final_objective"]["candidates"]))
    assert (first["metrics"]["final_objective"]["candidates"][cand]["mean"]
            == second["metrics"]["final_objective"]["candidates"][cand2]["mean"])
