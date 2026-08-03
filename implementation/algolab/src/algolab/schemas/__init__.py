"""Canonical JSON Schema registry.

The *.schema.json files in this package are byte-identical copies of the
canonical schemas in ``schemas/`` at the repository root (asserted by
``tests/test_schemas_match_canonical.py``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

_SCHEMA_DIR: Final[Path] = Path(__file__).parent

_SCHEMA_FILES: Final[dict[str, str]] = {
    "hypothesis": "hypothesis.schema.json",
    "candidate": "candidate.schema.json",
    "experiment": "experiment.schema.json",
}


class SchemaNotFound(KeyError):
    """Raised when a requested schema type is not in the registry."""


def available_types() -> tuple[str, ...]:
    return tuple(_SCHEMA_FILES)


def load_schema(schema_type: str) -> dict[str, Any]:
    """Load a canonical JSON Schema as a dict.

    Raises:
        SchemaNotFound: if *schema_type* is not registered.
    """
    filename = _SCHEMA_FILES.get(schema_type)
    if filename is None:
        raise SchemaNotFound(
            f"unknown schema type {schema_type!r}; available: {sorted(_SCHEMA_FILES)}"
        )
    with open(_SCHEMA_DIR / filename, encoding="utf-8") as fh:
        data = json.load(fh)
    assert isinstance(data, dict)
    return data


__all__ = ["load_schema", "SchemaNotFound"]
