"""Structured JSON-line logging for the execution plane (M1).

One JSON object per line: ``{"ts", "level", "event", "producer", ...fields}``.
Machine-readable and greppable; no multi-line records.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JsonLineFormatter(logging.Formatter):
    """Render log records as single JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        return json.dumps(payload, sort_keys=True)


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the module logger with a JSON-line handler on stdout."""
    logger = logging.getLogger("algolab")
    logger.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonLineFormatter())
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: str, level: int = logging.INFO,
              **fields: Any) -> None:
    """Emit one structured event record."""
    logger.log(level, event, extra={"fields": fields})


__all__ = ["configure_logging", "log_event", "JsonLineFormatter"]
