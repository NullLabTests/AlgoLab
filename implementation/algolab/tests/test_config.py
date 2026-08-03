"""Configuration loading (strict YAML -> Pydantic)."""

import pytest

from algolab.control.config import default_config, load_config


def test_defaults() -> None:
    cfg = default_config()
    assert cfg.budget.weekly_credits == 100.0
    assert cfg.budget.lifetime_cap_credits == 5000.0
    assert cfg.budget.currency == "USD"
    assert str(cfg.storage.path) == "data/algolab.sqlite3"


def test_load_from_file(tmp_path) -> None:
    p = tmp_path / "algolab.yaml"
    p.write_text(
        "storage:\n  path: /tmp/x.db\n"
        "budget:\n  weekly_credits: 3.0\n  lifetime_cap_credits: 50.0\n"
        "  max_run_credits: 4.0\n  max_cost: 500.0\n  currency: USD\n"
    )
    cfg = load_config(p)
    assert str(cfg.storage.path) == "/tmp/x.db"
    assert cfg.budget.weekly_credits == 3.0


def test_unknown_key_rejected(tmp_path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("storage:\n  path: x.db\nunknown_option: 1\n")
    with pytest.raises(ValueError):
        load_config(p)


def test_max_run_cannot_exceed_lifetime(tmp_path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        "budget:\n  weekly_credits: 1.0\n  lifetime_cap_credits: 5.0\n"
        "  max_run_credits: 50.0\n"
    )
    with pytest.raises(ValueError):
        load_config(p)


def test_lifetime_must_cover_weekly(tmp_path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("budget:\n  weekly_credits: 100.0\n  lifetime_cap_credits: 50.0\n")
    with pytest.raises(ValueError):
        load_config(p)


def test_negative_budget_rejected(tmp_path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("budget:\n  weekly_credits: -5.0\n")
    with pytest.raises(ValueError):
        load_config(p)


def test_invalid_yaml(tmp_path) -> None:
    p = tmp_path / "broken.yaml"
    p.write_text("storage: [unclosed\n")
    with pytest.raises(ValueError):
        load_config(p)
