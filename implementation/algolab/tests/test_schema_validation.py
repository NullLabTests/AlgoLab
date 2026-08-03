"""Canonical schema byte-identity + manifest validation."""


import pytest

from algolab.schemas import SchemaNotFound, load_schema
from algolab.validation.schema_validator import (
    ManifestValidationError,
    validate_manifest,
)
from tests.conftest import (
    CANONICAL_SCHEMAS_DIR,
    PACKAGE_SCHEMAS_DIR,
    make_candidate,
    make_experiment,
    make_hypothesis,
)

canonical_present = CANONICAL_SCHEMAS_DIR.exists()


@pytest.mark.skipif(
    not canonical_present,
    reason="canonical schemas/ dir absent (standalone checkout)",
)
@pytest.mark.parametrize("name", ["hypothesis", "candidate", "experiment"])
def test_packaged_schema_matches_canonical(name: str) -> None:
    canonical = (CANONICAL_SCHEMAS_DIR / f"{name}.schema.json").read_bytes()
    packaged = (PACKAGE_SCHEMAS_DIR / f"{name}.schema.json").read_bytes()
    assert packaged == canonical, (
        f"src/algolab/schemas/{name}.schema.json drifted from the canonical "
        f"schemas/{name}.schema.json — copy it verbatim"
    )


@pytest.mark.parametrize("schema_type", ["hypothesis", "candidate", "experiment"])
def test_load_schema_roundtrip(schema_type: str) -> None:
    schema = load_schema(schema_type)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_unknown_schema_type() -> None:
    with pytest.raises(SchemaNotFound):
        load_schema("paper")


def test_valid_manifests_pass() -> None:
    validate_manifest(make_hypothesis().model_dump(mode="json"), "hypothesis")
    validate_manifest(make_candidate("HYP-12345678").model_dump(mode="json"),
                      "candidate")
    validate_manifest(
        make_experiment("HYP-12345678").model_dump(mode="json"), "experiment"
    )


def test_additional_property_rejected() -> None:
    manifest = make_hypothesis().model_dump(mode="json")
    manifest["sneaky_extra"] = True
    with pytest.raises(ManifestValidationError):
        validate_manifest(manifest, "hypothesis")


def test_missing_required_field_rejected() -> None:
    manifest = make_candidate("HYP-12345678").model_dump(mode="json")
    del manifest["validators"]
    with pytest.raises(ManifestValidationError):
        validate_manifest(manifest, "candidate")


def test_bad_status_enum_rejected() -> None:
    manifest = make_experiment("HYP-12345678").model_dump(mode="json")
    manifest["status"] = "launched"
    with pytest.raises(ManifestValidationError):
        validate_manifest(manifest, "experiment")


def test_too_few_seeds_rejected() -> None:
    manifest = make_experiment("HYP-12345678").model_dump(mode="json")
    manifest["seeds"] = [1, 2]
    with pytest.raises(ManifestValidationError):
        validate_manifest(manifest, "experiment")


def test_error_messages_are_structured() -> None:
    manifest = make_hypothesis().model_dump(mode="json")
    manifest["predicted_effect"] = {"direction": "weird", "minimum_relative_change": 1}
    with pytest.raises(ManifestValidationError) as excinfo:
        validate_manifest(manifest, "hypothesis")
    assert any("predicted_effect" in e for e in excinfo.value.errors)
