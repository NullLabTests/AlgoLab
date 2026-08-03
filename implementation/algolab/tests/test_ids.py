"""Typed ID helpers."""

import pytest

from algolab.core.ids import InvalidID, is_valid, kind_of, new_id, require


@pytest.mark.parametrize(
    "prefix",
    ["HYP", "CAND", "EXP", "RUN", "RES", "DISC", "REP", "EVT"],
)
def test_new_id_prefix(prefix: str) -> None:
    value = new_id(prefix)
    assert value.startswith(f"{prefix}-")
    assert is_valid(value)
    assert kind_of(value) == prefix


def test_new_id_randomness() -> None:
    assert new_id("HYP") != new_id("HYP")


def test_new_id_unknown_prefix() -> None:
    with pytest.raises(InvalidID):
        new_id("FOO")


def test_is_valid_rejects_junk() -> None:
    assert not is_valid(None)
    assert not is_valid("")
    assert not is_valid("HYP-123")
    assert not is_valid("HYP-1234567")  # too short
    assert not is_valid("xyz-12345678")
    # 16 hex chars is a valid ID body.
    assert is_valid("EXP-1234567890ABCDEF")


def test_require_wrong_prefix() -> None:
    with pytest.raises(InvalidID):
        require("CAND-12345678", "HYP")


def test_require_accepts_any_prefix() -> None:
    assert require("CAND-12345678") == "CAND-12345678"


def test_require_rejects_malformed() -> None:
    with pytest.raises(InvalidID):
        require(12345)
