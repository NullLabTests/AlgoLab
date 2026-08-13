"""Tests for the knowledge layer: evidence, operator catalog, registry,
and the v2 -> v3 schema migration."""

from __future__ import annotations

import os

import pytest

from algolab.knowledge.evidence import (
    Evidence,
    EvidenceIntegrityError,
    EvidenceRepo,
    PROMOTE,
    REJECT,
)
from algolab.knowledge.operators import (
    M4_OPERATOR_ROLES,
    OPERATOR_CATALOG,
    budget_for_operator,
    is_operator,
    required_roles,
)
from algolab.knowledge.registry import (
    CooperativeRegistry,
    Registry,
    RegistryEntry,
    RegistryError,
    validate_skill_toml,
)
from algolab.storage.db import (
    SCHEMA_VERSION,
    apply_schema,
    check_append_only,
    connect,
)


# -- evidence -------------------------------------------------------------

def register_task(conn, task_id: str = "task-1") -> None:
    """Insert a task row so evidence FKs resolve (M1 registers tasks first)."""
    conn.execute(
        "INSERT INTO tasks (task_id, name, family, workload, description,"
        " baseline_config, search_space, seeds, primary_metric, direction,"
        " promotion_threshold, ground_truth, credit_estimate, created_at,"
        " producer) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (task_id, task_id, "family-a", "workload-a", "desc",
         "{}", "{}", "[11, 23, 37]", "qps", "maximize", 0.15, None,
         100.0, "2026-08-13T00:00:00Z", "test"),
    )


def make_record(repo: EvidenceRepo, **overrides) -> Evidence:
    params = {
        "task_id": "task-1",
        "experiment_id": "exp-1",
        "operator_name": "tune",
        "policy": "policy-a",
        "primary_metric": "qps",
        "direction": "maximize",
        "outcome": PROMOTE,
        "promotion_threshold": 0.15,
        "credits_charged": 10.0,
        "novel": True,
        "relative_delta": 0.21,
    }
    params.update(overrides)
    return repo.insert(**params)


def test_evidence_roundtrip(conn):
    register_task(conn)
    repo = EvidenceRepo(conn)
    rec = make_record(repo)
    assert rec.evidence_id.startswith("ev-")
    assert rec.created_at
    back = repo.by_id(rec.evidence_id)
    assert back == rec
    assert back.is_promotion


def test_evidence_history_and_latest(conn):
    register_task(conn)
    repo = EvidenceRepo(conn)
    first = make_record(repo, novel=True)
    second = make_record(repo, novel=False, replication_status=first.evidence_id)
    hist = repo.history("task-1")
    assert len(hist) == 2
    assert repo.latest("task-1") == second
    assert repo.latest() == second


def test_evidence_payload_roundtrip(conn):
    register_task(conn)
    repo = EvidenceRepo(conn)
    rec = make_record(repo, payload={"seeds": [11, 23], "ci": [0.1, 0.3]})
    assert repo.by_id(rec.evidence_id).payload == {"seeds": [11, 23], "ci": [0.1, 0.3]}


def test_evidence_bad_outcome_rejected(conn):
    with pytest.raises(EvidenceIntegrityError):
        make_record(EvidenceRepo(conn), outcome="meh")


def test_evidence_novel_replication_mismatch(conn):
    register_task(conn)
    repo = EvidenceRepo(conn)
    with pytest.raises(EvidenceIntegrityError):
        make_record(repo, novel=True, replication_status="ev-x")
    with pytest.raises(EvidenceIntegrityError):
        make_record(repo, novel=False, replication_status="")


def test_evidence_append_only_triggers(conn):
    register_task(conn)
    rec = make_record(EvidenceRepo(conn))
    with pytest.raises(Exception):
        conn.execute(
            "UPDATE evidence SET outcome = ? WHERE evidence_id = ?",
            (REJECT, rec.evidence_id))
    with pytest.raises(Exception):
        conn.execute("DELETE FROM evidence WHERE evidence_id = ?",
                     (rec.evidence_id,))


def test_evidence_sign(conn):
    register_task(conn)
    repo = EvidenceRepo(conn)
    up = make_record(repo, direction="maximize", outcome=PROMOTE,
                     relative_delta=0.2)
    down = make_record(repo, direction="minimize", outcome=PROMOTE,
                       relative_delta=-0.1)
    rejected = make_record(repo, direction="maximize", outcome=REJECT,
                           relative_delta=0.2)
    assert up.sign() == 1.0
    assert down.sign() == 1.0
    assert rejected.sign() == -1.0


# -- operator catalog -----------------------------------------------------

def test_catalog_complete():
    expected = {
        "tune", "reparameterize", "decompose", "polyglot",
        "synthesize", "validate", "refresh", "rollback",
    }
    assert set(OPERATOR_CATALOG) == expected
    for name in expected:
        assert is_operator(name)
        assert budget_for_operator(name) > 0
        assert required_roles(name)


def test_rollback_no_novelty_budget():
    assert budget_for_operator("rollback") < budget_for_operator("synthesize")
    assert required_roles("rollback") == {"tuner", "critic", "researcher"}
    for role in required_roles("rollback"):
        assert role in M4_OPERATOR_ROLES  # every eligible role is valid


def test_roles_subset_of_researcher():
    for roles in M4_OPERATOR_ROLES.values():
        assert roles <= M4_OPERATOR_ROLES["researcher"]


# -- registry -------------------------------------------------------------

def test_registry_roundtrip(tmp_path):
    reg = Registry(str(tmp_path))
    reg.register(RegistryEntry(
        agent="alice", role="tuner", status="active",
        record_target="artifacts/evidence/alice",
        updated_at="2026-08-13T00:00:00Z"))
    reg.register(RegistryEntry(
        agent="bob", role="coder", status="active",
        updated_at="2026-08-13T00:00:00Z"))
    assert [e.agent for e in reg.list()] == ["alice", "bob"]
    assert reg.get("alice").role == "tuner"
    assert reg.get("nobody") is None


def test_registry_latest_wins(tmp_path):
    reg = Registry(str(tmp_path))
    for role in ("tuner", "researcher"):
        reg.register(RegistryEntry(agent="alice", role=role, status="active"))
    assert reg.get("alice").role == "researcher"


def test_registry_may_invoke(tmp_path):
    reg = Registry(str(tmp_path))
    reg.register(RegistryEntry(agent="alice", role="tuner", status="active"))
    assert reg.may_invoke("alice", "tune")
    assert not reg.may_invoke("alice", "synthesize")
    assert not reg.may_invoke("nobody", "tune")


def test_registry_suspended(tmp_path):
    reg = Registry(str(tmp_path))
    reg.register(RegistryEntry(agent="alice", role="tuner",
                               status="suspended"))
    assert not reg.may_invoke("alice", "tune")


def test_registry_invalid_role_rejected(tmp_path):
    with pytest.raises(RegistryError):
        RegistryEntry(agent="alice", role="wizard", status="active")


def test_registry_malformed_line(tmp_path):
    path = os.path.join(str(tmp_path), "registry", "registry.tsv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("not-enough-fields\n")
    with pytest.raises(RegistryError):
        Registry(str(tmp_path)).list()


def test_cooperative_operators_for(tmp_path):
    reg = CooperativeRegistry(str(tmp_path))
    reg.register(RegistryEntry(agent="alice", role="critic", status="active"))
    assert reg.operators_for("alice") == ["validate", "rollback"]


def test_validate_skill_toml(tmp_path):
    good = tmp_path / "skill.toml"
    good.write_text(
        '[skill]\nname = "tuner-a"\nrole = "tuner"\ndescription = "tunes"\n'
    )
    assert validate_skill_toml(str(good))["role"] == "tuner"
    bad = tmp_path / "bad.toml"
    bad.write_text('[skill]\nname = "x"\nrole = "wizard"\n')
    with pytest.raises(RegistryError):
        validate_skill_toml(str(bad))


# -- migration v2 -> v3 ---------------------------------------------------

def test_migration_v2_to_v3(tmp_path):
    db = tmp_path / "db.sqlite3"
    c = connect(str(db), initialize=False)
    apply_schema(c, 2)
    assert c.execute("PRAGMA user_version").fetchone()[0] == 2
    c.close()

    c = connect(str(db), initialize=False)
    with pytest.raises(Exception):
        c.execute("SELECT * FROM evidence")  # table does not exist yet
    apply_schema(c, SCHEMA_VERSION)
    assert c.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION

    tables = {r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"tasks", "evidence", "operator_uses", "operator_stats",
            "search_episodes"} <= tables
    # New tables are writable and append-only-protected.
    register_task(c)
    repo = EvidenceRepo(c)
    rec = make_record(repo)
    assert repo.by_id(rec.evidence_id) == rec
    with pytest.raises(Exception):
        c.execute("DELETE FROM evidence WHERE evidence_id = ?",
                  (rec.evidence_id,))
    check_append_only(c)
    c.close()


def test_append_only_also_protects_new_tables(conn):
    register_task(conn)
    with pytest.raises(Exception):
        conn.execute("UPDATE tasks SET name = 'task-1-renamed'")
    with pytest.raises(Exception):
        conn.execute("DELETE FROM tasks")
    conn.execute(
        "INSERT INTO operator_uses (use_id, operator_name, task_id,"
        " experiment_id, outcome, relative_delta, credits_charged, novel,"
        " created_at, producer) VALUES ('use-1', 'tune', 'task-1', 'exp-1',"
        " 'promote', 0.2, 10.0, 1, '2026-08-13T00:00:00Z', 'test')")
    with pytest.raises(Exception):
        conn.execute("DELETE FROM operator_uses")
