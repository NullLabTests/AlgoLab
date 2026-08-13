"""Typed identifier helpers.

Canonical ID prefixes (MASTER_SPEC.md §12, extended for the evidence
archive):

    HYP-  hypothesis
    CAND- candidate
    EXP-  experiment
    RUN-  run
    RES-  result
    DISC- discovery
    REP-  report
    TASK- benchmark task
    EVID- evidence record
    EPIS- search episode
    EVT-  event

Format: ``<PREFIX>-<8+ hex chars>`` (e.g. ``HYP-3F2A9C01``).
"""

from __future__ import annotations

import re
import secrets
from typing import Final

PREFIXES: Final[frozenset[str]] = frozenset(
    {"HYP", "CAND", "EXP", "RUN", "RES", "DISC", "REP",
     "TASK", "EVID", "EPIS", "EVT"}
)

_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(HYP|CAND|EXP|RUN|RES|DISC|REP|TASK|EVID|EPIS|EVT)-([0-9A-Fa-f]{8,})$"
)

_HEX_DIGITS: Final[int] = 8


class InvalidID(ValueError):
    """Raised when an identifier is malformed or has the wrong prefix."""


def new_id(kind: str) -> str:
    """Create a new identifier of the given kind.

    Raises:
        InvalidID: if *kind* is not a canonical prefix.
    """
    if kind not in PREFIXES:
        raise InvalidID(
            f"unknown ID prefix {kind!r}; expected one of "
            f"{sorted(PREFIXES)}"
        )
    return f"{kind}-{secrets.token_hex(_HEX_DIGITS // 2).upper()}"


def is_valid(value: object) -> bool:
    """Return True if *value* matches the canonical ID format."""
    return isinstance(value, str) and _PATTERN.fullmatch(value) is not None


def kind_of(value: str) -> str:
    """Return the prefix (kind) of a valid ID.

    Raises:
        InvalidID: if *value* is malformed.
    """
    m = _PATTERN.fullmatch(value)
    if m is None:
        raise InvalidID(f"malformed ID {value!r}")
    return m.group(1)


def require(value: object, expected_prefix: str | None = None) -> str:
    """Validate *value* as a canonical ID, optionally enforcing a prefix.

    Raises:
        InvalidID: on malformed ID or prefix mismatch.
    """
    if not is_valid(value):
        raise InvalidID(f"malformed ID {value!r}")
    assert isinstance(value, str)
    if expected_prefix is not None and kind_of(value) != expected_prefix:
        raise InvalidID(
            f"expected prefix {expected_prefix}- but got {value!r}"
        )
    return value
