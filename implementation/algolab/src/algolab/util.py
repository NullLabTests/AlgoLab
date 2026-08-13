"""Shared micro-utilities for AlgoLab."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> str:
    """Current UTC timestamp as ISO-8601 with seconds precision."""
    return datetime.now(UTC).isoformat(timespec="seconds")


__all__ = ["utc_now"]
