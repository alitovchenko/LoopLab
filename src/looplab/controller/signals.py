"""Structured control signal and model output types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelOutput:
    """Raw output from a model: value, optional confidence, optional metadata."""

    value: float | list[float] | dict[str, Any]
    confidence: float | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class ControlSignal:
    """Structured control for the task: action type, params, validity window (LSL time)."""

    action: str
    params: dict[str, Any]
    valid_until_lsl_time: float
    metadata: dict[str, Any] | None = None
