"""Event log schema: event_type, lsl_time, payload."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    STREAM_CHUNK = "stream_chunk"
    FEATURES = "features"
    MODEL_OUTPUT = "model_output"
    CONTROL_SIGNAL = "control_signal"
    STIMULUS_INTENDED = "stimulus_intended"
    STIMULUS_REALIZED = "stimulus_realized"
    BENCHMARK_LATENCY = "benchmark_latency"


@dataclass
class LogEvent:
    """Single log entry: type, LSL time, payload dict."""

    event_type: EventType | str
    lsl_time: float
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value if hasattr(self.event_type, "value") else self.event_type,
            "lsl_time": self.lsl_time,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LogEvent":
        et = d.get("event_type", "")
        try:
            et = EventType(et)
        except ValueError:
            pass
        return cls(event_type=et, lsl_time=float(d["lsl_time"]), payload=d.get("payload", {}))
