"""Protocol 244 real-workload transfer runner and CLI regression tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from algolab.cli.main import main
from algolab.meta_search import transfer
from algolab.meta_search.protocol_241 import verify_pilot
from algolab.search.toy import Attempt


def _fake_loader(name: str) -> transfer._Workload:  # type: ignore[name-defined]
    """A tiny deterministic stand-in for the real sklearn workloads."""
    assert name in {"fake", "fake-secondary"}

    def attempt(
        family: str,
        operator: str,
        *,
        seed_base: int,
        trial: int,
        episode: int,
        attempt: int,
    ) -> Attempt:
        del family, seed_base, attempt
        useful = operator == "cheap"
        effect = 0.2 if useful else -0.1
        return Attempt(
            operator=operator,
            cost_credits=1.0 if useful else 2.0,
            valid=True,
            effect_1=effect,
            effect_2=effect,
            mean_effect=effect,
            discovery=useful and (trial + episode) % 2 == 0,
        )

    return transfer._Workload(  # type: ignore[attr-defined]
        name=name,
        version="test/1.0",
        families=("alpha", "beta"),
        held_out="gamma",
        operators=("cheap", "expensive", "third"),
        costs={"cheap": 1.0, "expensive": 2.0, "third": 2.0},
        attempt=attempt,
        environment={"name": name, "ground_truth": None},
    )


@pytest.fixture()
def fake_workload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(transfer, "_load_workload", _fake_loader)


class TestTransferBundle:
    def test_bundle_is_sealed_and_verifiable(
        self, fake_workload: None, tmp_path: Path
    ) -> None:
        bundle = tmp_path / "protocol-244-test"
        result = transfer.run_transfer(
            bundle,
            workloads=("fake",),
            trials=2,
            episodes=3,
            budget=40,
            bootstrap_iterations=200,
        )
        verdict = verify_pilot(bundle)
        assert verdict["verified"] is True
        assert verdict["trace_integrity"] is True
        assert verdict["replay_only_promotion_detected"] is False
        assert verdict["n_files_verified"] == len(result["checksums"])

        manifest = json.loads((bundle / "manifest.json").read_text())
        assert manifest["schema_version"] == transfer.TRANSFER_SCHEMA_VERSION
        assert manifest["trace_is_prospective_evidence"] is False
        assert manifest["multiple_comparison_correction"] == "benjamini-hochberg"
        assert manifest["workloads"] == [
            {"name": "fake", "version": "test/1.0", "held_out": "gamma"}
        ]

        replay = json.loads(
            (bundle / "replay" / "fake-fixed-baseline.json").read_text()
        )
        assert replay["is_prospective_evidence"] is False
        evaluation = json.loads(
            (bundle / "evaluations" / "fake-evolved.json").read_text()
        )
        assert evaluation["stage_a"]["is_prospective_evidence"] is False
        assert evaluation["stage_b"]["is_prospective_evidence"] is True
        assert evaluation["stage_c"]["is_prospective_evidence"] is True
        assert "p_adjusted" in evaluation["stage_b"]["primary"]
        assert len(result["summaries"]) == 1

    def test_bundle_is_deterministic(
        self, fake_workload: None, tmp_path: Path
    ) -> None:
        first = tmp_path / "first"
        second = tmp_path / "second"
        kwargs = {
            "workloads": ("fake",),
            "trials": 2,
            "episodes": 3,
            "budget": 40,
            "bootstrap_iterations": 200,
        }
        transfer.run_transfer(first, **kwargs)  # type: ignore[arg-type]
        transfer.run_transfer(second, **kwargs)  # type: ignore[arg-type]
        assert (first / "checksums.json").read_bytes() == (
            second / "checksums.json"
        ).read_bytes()
        for path in first.rglob("*"):
            if not path.is_file() or path.name == "checksums.json":
                continue
            assert path.read_bytes() == (second / path.relative_to(first)).read_bytes()

    def test_tampering_detected(self, fake_workload: None, tmp_path: Path) -> None:
        bundle = tmp_path / "tampered"
        transfer.run_transfer(
            bundle,
            workloads=("fake",),
            trials=2,
            episodes=3,
            budget=40,
            bootstrap_iterations=200,
        )
        target = bundle / "report.md"
        target.write_text(target.read_text() + "\nTAMPERED\n")
        verdict = verify_pilot(bundle)
        assert verdict["verified"] is False
        assert "report.md" in verdict["mismatches"]

    def test_unknown_workload_fails_closed(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="unsupported transfer workload"):
            transfer.run_transfer(
                tmp_path / "unknown",
                workloads=("not-a-workload",),
                trials=1,
                episodes=1,
                bootstrap_iterations=100,
            )


class TestTransferCLI:
    def test_cli_writes_bundle(
        self, fake_workload: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bundle = tmp_path / "cli-bundle"
        code = main(
            [
                "meta-transfer-run",
                "--dir",
                str(bundle),
                "--workloads",
                "fake",
                "--trials",
                "2",
                "--episodes",
                "3",
                "--budget",
                "40",
                "--bootstrap-iterations",
                "200",
                "--apply-bh",
                "--force",
                "--json",
            ]
        )
        assert code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["summaries"][0]["workload"] == "fake"
        assert output["summaries"][0]["promotion"] in {
            "PROMOTED",
            "REJECTED_HISTORICAL_ONLY",
            "REJECTED_PROSPECTIVE",
            "REJECTED_INDEPENDENT",
            "REJECTED_INCOMPLETE",
        }
        assert verify_pilot(bundle)["verified"] is True

    def test_cli_refuses_existing_bundle(
        self, fake_workload: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bundle = tmp_path / "sealed"
        base = [
            "meta-transfer-run",
            "--dir",
            str(bundle),
            "--workloads",
            "fake",
            "--trials",
            "2",
            "--episodes",
            "1",
            "--bootstrap-iterations",
            "100",
        ]
        assert main(base) == 0
        capsys.readouterr()
        assert main(base) == 2
        assert "refusing to overwrite sealed bundle" in capsys.readouterr().err

    def test_meta_verify_command(self, fake_workload: None, tmp_path: Path) -> None:
        bundle = tmp_path / "verify-cli"
        main(
            [
                "meta-transfer-run",
                "--dir",
                str(bundle),
                "--workloads",
                "fake",
                "--trials",
                "2",
                "--episodes",
                "1",
                "--bootstrap-iterations",
                "100",
            ]
        )
        assert main(["meta-verify", "--dir", str(bundle), "--json"]) == 0
