"""Validation of interchange manifests against the canonical JSON Schemas.

Manifests entering the system (hypothesis/candidate/experiment) MUST validate
against the canonical schemas before persistence; this is the authoritative
contract boundary (MASTER_SPEC.md §12, §16 acceptance 4).
"""

from __future__ import annotations

from typing import Any, Final

from jsonschema import Draft202012Validator, ValidationError

from algolab.schemas import SchemaNotFound, load_schema

# Draft 2020-12 already enforces additionalProperties:false.
_VALIDATORS: Final[dict[str, Draft202012Validator]] = {}


def _get_validators() -> dict[str, Draft202012Validator]:
    if not _VALIDATORS:
        for schema_type in ("hypothesis", "candidate", "experiment"):
            _VALIDATORS[schema_type] = Draft202012Validator(load_schema(schema_type))
    return _VALIDATORS


class ManifestValidationError(ValueError):
    """Raised when a manifest fails validation against its canonical schema."""

    def __init__(self, schema_type: str, errors: list[str]) -> None:
        self.schema_type = schema_type
        self.errors = errors
        super().__init__(f"manifest failed {schema_type} schema validation: {errors}")


def validate_manifest(manifest: dict[str, Any], schema_type: str) -> None:
    """Validate *manifest* against the canonical *schema_type* schema.

    Raises:
        SchemaNotFound: unknown schema type.
        ManifestValidationError: if the manifest is invalid (fail closed).
    """
    validators = _get_validators()
    if schema_type not in validators:
        raise SchemaNotFound(
            f"unknown schema type {schema_type!r}; available: {sorted(validators)}"
        )
    errors = sorted(
        (e for e in validators[schema_type].iter_errors(manifest)),
        key=lambda e: ".".join(str(p) for p in e.absolute_path),
    )
    if errors:
        raise ManifestValidationError(schema_type, [_format_error(e) for e in errors])


def _format_error(err: ValidationError) -> str:
    location = ".".join(str(part) for part in err.absolute_path) or "<root>"
    return f"at {location}: {err.message}"
