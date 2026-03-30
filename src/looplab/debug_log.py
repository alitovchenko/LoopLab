"""Stderr logging for LoopLab: -v (INFO), -vv (DEBUG with optional LOOPLAB JSON lines)."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any


class _LooplabFormatter(logging.Formatter):
    """INFO/WARNING: short line; DEBUG: one JSON object per line prefixed with LOOPLAB."""

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno == logging.DEBUG:
            payload: dict[str, Any] = {
                "ts": record.created,
                "phase": getattr(record, "phase", "looplab"),
                "msg": record.getMessage(),
            }
            payload_data = getattr(record, "payload", None)
            if payload_data is not None:
                payload["data"] = payload_data
            return "LOOPLAB " + json.dumps(payload, default=str)
        return f"looplab: {record.levelname} {record.name}: {record.getMessage()}"


def setup_looplab_logging(verbosity: int) -> None:
    """
    verbosity: 0 = WARNING (quiet), 1 = INFO, 2+ = DEBUG (structured LOOPLAB lines on stderr).
    """
    log = logging.getLogger("looplab")
    log.handlers.clear()
    log.propagate = False
    if verbosity <= 0:
        log.setLevel(logging.WARNING)
    elif verbosity == 1:
        log.setLevel(logging.INFO)
    else:
        log.setLevel(logging.DEBUG)

    h = logging.StreamHandler(sys.stderr)
    h.setLevel(logging.DEBUG)
    h.setFormatter(_LooplabFormatter())
    log.addHandler(h)


def log_debug_event(logger: logging.Logger, phase: str, msg: str, data: dict[str, Any] | None = None) -> None:
    """Emit a DEBUG record with optional structured data (rendered as LOOPLAB JSON at -vv)."""
    extra: dict[str, Any] = {"phase": phase}
    if data is not None:
        extra["payload"] = data
    logger.debug(msg, extra=extra)


def proof_phase_logger() -> logging.Logger:
    return logging.getLogger("looplab.proof_run")
