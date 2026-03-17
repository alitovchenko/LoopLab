"""Timing hooks at key pipeline points: record LSL time and label."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from looplab.streams.clock import lsl_clock


@dataclass
class BenchmarkHooks:
    """
    Instrument pipeline: after pull_chunk, preprocess, features, model, policy, intended, realized.
    Records (label, lsl_time) for each. Optional callback to logger.
    """

    _points: list[tuple[str, float]] = field(default_factory=list)
    _enabled: bool = True
    _logger: Any = None

    def set_logger(self, logger: Any) -> None:
        self._logger = logger

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def record(self, label: str, lsl_time: float | None = None) -> None:
        if not self._enabled:
            return
        t = lsl_time if lsl_time is not None else lsl_clock()
        self._points.append((label, t))
        if self._logger is not None:
            self._logger.log_benchmark(t, label=label)

    def record_pull_chunk(self, lsl_time: float | None = None) -> None:
        self.record("pull_chunk", lsl_time)

    def record_window_ready(self, lsl_time: float | None = None) -> None:
        self.record("window_ready", lsl_time)

    def record_acquisition(self, lsl_time: float) -> None:
        """Record acquisition time (e.g. window t_end) for acquisition-to-window latency."""
        self.record("acquisition", lsl_time)

    def record_preprocess_done(self, lsl_time: float | None = None) -> None:
        self.record("preprocess_done", lsl_time)

    def record_features_done(self, lsl_time: float | None = None) -> None:
        self.record("features_done", lsl_time)

    def record_model_done(self, lsl_time: float | None = None) -> None:
        self.record("model_done", lsl_time)

    def record_policy_done(self, lsl_time: float | None = None) -> None:
        self.record("policy_done", lsl_time)

    def record_task_dispatch(self, lsl_time: float | None = None) -> None:
        self.record("task_dispatch", lsl_time)

    def record_intended(self, lsl_time: float | None = None) -> None:
        self.record("stimulus_intended", lsl_time)

    def record_realized(self, lsl_time: float | None = None) -> None:
        self.record("stimulus_realized", lsl_time)

    def get_points(self) -> list[tuple[str, float]]:
        return list(self._points)

    def clear(self) -> None:
        self._points.clear()
