"""One test per ontology invariant in spec/foundation/001_CORE_ONTOLOGY.md.

Invariants:
1. No result exists without a run.
2. No run exists without an approved experiment.
3. No experiment exists without a falsifiable hypothesis or baseline-validation
   purpose.
4. No discovery exists without replication evidence.
5. No report claim exists without evidence links.
6. No entity may overwrite its provenance.
"""

import sqlite3

import pytest

from algolab.core.models import ReportClaim
from algolab.storage.event_store import EventStore
from algolab.storage.repositories import InvariantViolation
from algolab.validation.schema_validator import (
    ManifestValidationError,
    validate_manifest,
)
from tests.conftest import (
    approve_experiment,
    expand,
    make_approved_experiment,
    make_candidate,
    make_discovery,
    make_experiment,
    make_hypothesis,
    make_report,
    make_result,
    run_through_success,
)


def _completed_run(conn, run_repo, exp_id: str, seed: int) -> str:
    run = next(r for r in run_repo.list_runs(experiment_id=exp_id)
               if r.seed == seed)
    run_through_success(conn, run.run_id)
    return run.run_id


def test_invariant_1_result_requires_run(conn, res_repo) -> None:
    """No result exists without a run."""
    with conn:
        with pytest.raises(InvariantViolation):
            res_repo.create(make_result("RUN-00000000"))


def test_invariant_2_run_requires_approved_experiment(conn) -> None:
    """No run exists without an approved experiment: expansion is refused
    for non-approved experiments and nothing is persisted."""
    from algolab.control.config import AlgolabConfig
    from algolab.execution.expansion import (
        ExperimentExpansion,
        ExperimentNotApproved,
    )
    from algolab.storage.repositories import (
        CandidateRepository,
        ExperimentRepository,
        HypothesisRepository,
    )
    from algolab.storage.run_repository import RunRepository

    with conn:
        h = make_hypothesis()
        hid = HypothesisRepository(conn, producer="test").create(h)
        c = make_candidate(hid)
        cid = CandidateRepository(conn, producer="test").create(c)
        exp = make_experiment(hid, cid, seeds=[11, 23, 37], status="draft")
        exp_id = ExperimentRepository(conn, producer="test").create(exp)

    with pytest.raises(ExperimentNotApproved):
        ExperimentExpansion(
            conn, AlgolabConfig(producer="test")).expand(exp_id, "k")
    # No runs were persisted (all-or-nothing).
    assert RunRepository(conn, producer="test").list_runs() == []


def test_invariant_3a_experiment_requires_hypothesis_schema() -> None:
    """No experiment exists without a falsifiable hypothesis (schema level)."""
    manifest = make_experiment("HYP-00000000").model_dump(mode="json")
    manifest.pop("hypothesis_ids")
    with pytest.raises(ManifestValidationError):
        validate_manifest(manifest, "experiment")


def test_invariant_3b_experiment_hypothesis_must_exist(conn, exp_repo) -> None:
    """The referenced hypothesis must actually exist (integrity level)."""
    with conn:
        with pytest.raises(InvariantViolation):
            exp_repo.create(make_experiment("HYP-00000000"))


def test_invariant_4_discovery_requires_replication_evidence(
    conn, run_repo, res_repo, disc_repo
) -> None:
    """No discovery exists without replication evidence: >= 2 results from
    >= 2 distinct runs."""
    exp_id = make_approved_experiment(conn, candidate_count=1)
    expand(conn, exp_id)
    runs = run_repo.list_runs(experiment_id=exp_id)
    cand_id = next(r.candidate_id for r in runs if not r.is_baseline)
    run_a = _completed_run(conn, run_repo, exp_id, seed=11)
    run_b = _completed_run(conn, run_repo, exp_id, seed=23)

    with conn:
        # Two results from the SAME run -> not replication evidence.
        r1 = res_repo.create(make_result(run_a))
        r2 = res_repo.create(make_result(run_a))
        with pytest.raises(InvariantViolation):
            disc_repo.create(make_discovery([r1, r2], candidate_id=cand_id))

        # One result from each of two runs -> replication evidence.
        r3 = res_repo.create(make_result(run_b))
        disc_repo.create(make_discovery([r1, r3], candidate_id=cand_id))


def test_invariant_4b_discovery_results_must_exist(conn, disc_repo,
                                                   hyp_repo, cand_repo) -> None:
    with conn:
        h = make_hypothesis()
        hyp_repo.create(h)
        c = make_candidate(h.id)
        cand_repo.create(c)
        with pytest.raises(InvariantViolation):
            disc_repo.create(
                make_discovery(["RES-00000001", "RES-00000002"],
                               candidate_id=c.id)
            )


def test_invariant_5a_report_claim_requires_evidence_link() -> None:
    """No report claim exists without evidence links (model level)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ReportClaim(statement="Claim with no evidence.",
                    claim_type="discovery",
                    evidence=[])


def test_invariant_5b_report_evidence_must_exist(conn, rep_repo) -> None:
    """Evidence links must resolve to stored results."""
    with conn:
        with pytest.raises(InvariantViolation):
            rep_repo.create(make_report(["RES-00000001"]))


def test_invariant_6a_provenance_columns_frozen(conn, hyp_repo) -> None:
    """No entity may overwrite its provenance: direct SQL is blocked by
    trigger for payload/creator/created_at."""
    h = make_hypothesis()
    with conn:
        hyp_repo.create(h)
    with pytest.raises(Exception) as excinfo:
        with conn:
            conn.execute(
                "UPDATE entities SET payload = '{}' WHERE entity_id = ?",
                (h.id,),
            )
    assert "immutable" in str(excinfo.value)
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute(
                "UPDATE entities SET created_at = 'epoch' WHERE entity_id = ?",
                (h.id,),
            )


def test_invariant_6b_provenance_survives_lifecycle(conn, hyp_repo, cand_repo,
                                                    exp_repo) -> None:
    """The manifest is immutable across the lifecycle; the event log records
    every change, so nothing is ever overwritten."""
    h = make_hypothesis()
    with conn:
        hyp_repo.create(h)
        c = make_candidate(h.id)
        cand_repo.create(c)
        exp_id = exp_repo.create(make_experiment(h.id, c.id))
        approve_experiment(exp_repo, exp_id)

    stored = hyp_repo.get(h.id)
    assert stored.statement == h.statement
    assert stored.mechanism == h.mechanism
    assert stored.status == "draft"  # hypothesis manifest untouched

    mutations = [e.mutation for e in EventStore(conn).list_for_entity(exp_id)]
    assert mutations == ["created", "status_changed", "status_changed"]


def test_every_mutation_appends_event(conn, hyp_repo) -> None:
    """Kickoff constraint: every state mutation appends an audit event."""
    h = make_hypothesis()
    with conn:
        hyp_repo.create(h)
    assert EventStore(conn).count() == 1
