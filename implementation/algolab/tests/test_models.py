"""Entity model validation."""

import pytest
from pydantic import ValidationError

from algolab.core.ids import InvalidID
from algolab.core.models import ReportClaim
from tests.conftest import make_hypothesis, make_run


def test_hypothesis_short_statement_rejected() -> None:
    with pytest.raises(ValidationError):
        make_hypothesis(statement="too short")


def test_hypothesis_bad_effect_direction() -> None:
    with pytest.raises(ValidationError):
        make_hypothesis(
            predicted_effect={"direction": "sideways",
                              "minimum_relative_change": 0.01}
        )


def test_hypothesis_bad_id_prefix() -> None:
    with pytest.raises((ValidationError, InvalidID)):
        make_hypothesis(id="CAND-12345678")


def test_hypothesis_requires_effect_number() -> None:
    with pytest.raises(ValidationError):
        make_hypothesis(predicted_effect={"direction": "increase",
                                          "minimum_relative_change": "big"})


def test_candidate_requires_hypothesis_and_changes() -> None:
    from tests.conftest import make_candidate

    with pytest.raises(ValidationError):
        make_candidate("HYP-12345678", hypothesis_ids=[])
    with pytest.raises(ValidationError):
        make_candidate("HYP-12345678", changes=[])


def test_experiment_seeds_minimum() -> None:
    from tests.conftest import make_experiment

    with pytest.raises(ValidationError):
        make_experiment("HYP-12345678", seeds=[1, 2])


def test_experiment_negative_budget_rejected() -> None:
    from tests.conftest import make_experiment

    with pytest.raises(ValidationError):
        make_experiment(
            "HYP-12345678",
            budget={"max_compute_credits": -1.0, "max_cost": 10.0},
        )


def test_run_negative_credits_rejected() -> None:
    with pytest.raises(ValidationError):
        make_run("EXP-12345678", credits_spent=-0.5)


def test_run_bad_experiment_id() -> None:
    with pytest.raises((ValidationError, InvalidID)):
        make_run("NOTANID")


def test_report_claim_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        ReportClaim(statement="Some claim about a result.",
                    claim_type="discovery",
                    evidence=[])


def test_default_hypothesis_is_valid() -> None:
    h = make_hypothesis()
    assert h.status == "draft"
    assert isinstance(h.id, str)
