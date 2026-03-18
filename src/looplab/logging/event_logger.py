"""Event logger: single interface for all event types, LSL time, optional writer."""

from __future__ import annotations

from typing import Any

from looplab.logging.schema import EventType, LogEvent
from looplab.logging.writers import JSONLWriter
from looplab.streams.clock import lsl_clock


class EventLogger:
    """Log events with event_type, lsl_time, payload. Delegates to a writer (e.g. JSONL)."""

    def __init__(self, writer: JSONLWriter | None = None):
        self._writer = writer

    def set_writer(self, writer: JSONLWriter) -> None:
        self._writer = writer

    def log(self, event_type: EventType | str, lsl_time: float, payload: dict[str, Any] | None = None) -> None:
        if self._writer is None:
            return
        self._writer.write(LogEvent(event_type=event_type, lsl_time=lsl_time, payload=payload or {}))

    def log_stream_chunk(self, t_start: float, t_end: float, n_samples: int) -> None:
        self.log(EventType.STREAM_CHUNK, lsl_clock(), {"t_start": t_start, "t_end": t_end, "n_samples": n_samples})

    def log_features(self, lsl_time: float, feature_shape: list[int] | None = None) -> None:
        self.log(EventType.FEATURES, lsl_time, {"feature_shape": feature_shape or []})

    def log_model_output(self, lsl_time: float, value: Any, confidence: float | None = None) -> None:
        payload: dict[str, Any] = {"value": value}
        if confidence is not None:
            payload["confidence"] = confidence
        self.log(EventType.MODEL_OUTPUT, lsl_time, payload)

    def log_control_signal(self, lsl_time: float, action: str, params: dict[str, Any], valid_until: float) -> None:
        self.log(
            EventType.CONTROL_SIGNAL,
            lsl_time,
            {"action": action, "params": params, "valid_until_lsl_time": valid_until},
        )

    def log_stimulus_intended(self, lsl_time: float, action: str, params: dict[str, Any]) -> None:
        self.log(EventType.STIMULUS_INTENDED, lsl_time, {"action": action, "params": params})

    def log_stimulus_realized(self, lsl_time: float, action: str, params: dict[str, Any]) -> None:
        self.log(EventType.STIMULUS_REALIZED, lsl_time, {"action": action, "params": params})

    def log_benchmark(self, lsl_time: float, label: str, **kwargs: Any) -> None:
        self.log(EventType.BENCHMARK_LATENCY, lsl_time, {"label": label, **kwargs})

    # Task-level / experiment-level events
    def log_trial_start(self, lsl_time: float, trial_context: "TrialContext") -> None:
        from looplab.experiment.state import TrialContext
        if not isinstance(trial_context, TrialContext):
            raise TypeError("trial_context must be TrialContext")
        self.log(EventType.TRIAL_START, lsl_time, trial_context.to_dict())

    def log_trial_end(self, lsl_time: float, trial_index: int, block_index: int) -> None:
        self.log(EventType.TRIAL_END, lsl_time, {"trial_index": trial_index, "block_index": block_index})

    def log_block_start(self, lsl_time: float, block_context: "BlockContext") -> None:
        from looplab.experiment.state import BlockContext
        if not isinstance(block_context, BlockContext):
            raise TypeError("block_context must be BlockContext")
        self.log(EventType.BLOCK_START, lsl_time, block_context.to_dict())

    def log_block_end(self, lsl_time: float, block_index: int) -> None:
        self.log(EventType.BLOCK_END, lsl_time, {"block_index": block_index})

    def log_trial_outcome(self, lsl_time: float, outcome: "TrialOutcome") -> None:
        from looplab.experiment.state import TrialOutcome
        if not isinstance(outcome, TrialOutcome):
            raise TypeError("outcome must be TrialOutcome")
        self.log(EventType.TRIAL_OUTCOME, lsl_time, outcome.to_dict())

    def log_adaptive_params_update(self, lsl_time: float, params: dict[str, Any]) -> None:
        self.log(EventType.ADAPTIVE_PARAMS_UPDATE, lsl_time, params)

    def flush(self) -> None:
        if self._writer is not None and hasattr(self._writer, "close"):
            pass  # writer flushes on each write
