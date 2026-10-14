"""Committed experiment bundles: at-rest integrity and presence.

Every sealed bundle under ``experiments/`` ships a ``checksums.json`` mapping
each deterministic artifact file to its SHA-256. This test re-hashes the actual
bytes and asserts equality, so any accidental edit, truncation, or corruption of
a committed artifact (including the sealed raw per-attempt streams) fails CI.

It also asserts that the known sealed bundles are still present: deleting a
bundle to make a red test green is exactly the failure mode this guards against.

Scope note: this verifies artifact *integrity at rest*, not scientific
reproducibility. Byte-reproduction of a bundle by re-execution is covered
separately (``test_protocol_230_golden.py`` for protocol-230-v1).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

EXPERIMENTS = Path(__file__).resolve().parents[1] / "experiments"

# Bundles expected to be committed with a checksums.json. Update deliberately
# when a new bundle is sealed; never remove an entry to silence a failure.
EXPECTED_SEALED_BUNDLES = (
    "protocol-230-v1",
    "protocol-230-v2",
    "protocol-232-v1",
    "protocol-233-p30",
    "protocol-233-p60",
    "protocol-233-p120",
    "protocol-233-p240",
    "protocol-234-p30",
    "protocol-234-p60",
    "protocol-234-p120",
    "protocol-234-p240",
    "protocol-235-v1",
)


def _bundles_with_checksums() -> list[Path]:
    return sorted(EXPERIMENTS.glob("*/checksums.json"))


def test_expected_sealed_bundles_present() -> None:
    present = {p.parent.name for p in _bundles_with_checksums()}
    missing = [b for b in EXPECTED_SEALED_BUNDLES if b not in present]
    assert not missing, f"sealed bundles missing checksums.json: {missing}"


def test_checksums_json_is_well_formed() -> None:
    for cs in _bundles_with_checksums():
        data = json.loads(cs.read_text())
        assert isinstance(data, dict) and data, cs
        assert all(
            isinstance(k, str) and isinstance(v, str) and len(v) == 64
            for k, v in data.items()
        ), cs


def test_every_recorded_digest_matches_the_artifact_bytes() -> None:
    checked = 0
    problems: list[str] = []
    for cs in _bundles_with_checksums():
        bundle = cs.parent
        for rel, digest in json.loads(cs.read_text()).items():
            p = bundle / rel
            if not p.is_file():
                problems.append(f"{bundle.name}:{rel} MISSING")
                continue
            actual = hashlib.sha256(p.read_bytes()).hexdigest()
            if actual != digest:
                problems.append(f"{bundle.name}:{rel} MISMATCH")
            checked += 1
    assert checked > 0, "no artifact files were checked"
    assert not problems, "artifact integrity failures:\n" + "\n".join(problems)


@pytest.mark.parametrize("bundle", EXPECTED_SEALED_BUNDLES)
def test_bundle_has_a_report_and_statistics(bundle: str) -> None:
    d = EXPERIMENTS / bundle
    assert (d / "manifest.json").is_file(), bundle
    assert (d / "statistics.json").is_file(), bundle
    assert (d / "report.md").is_file(), bundle
