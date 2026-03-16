"""PsychoPy task adapter: queue of control signals; task polls at frame/trial boundaries."""

from __future__ import annotations

import threading
from typing import Any

from looplab.controller.signals import ControlSignal
from looplab.task.adapter import TaskAdapter


class PsychoPyTaskAdapter(TaskAdapter):
    """
    Thread-safe queue. LoopLab pushes signals; PsychoPy script calls get_pending/pop_pending
    each frame or at trial boundaries, then report_realized(signal, lsl_time) after flip.
    """

    def __init__(self, logger: Any = None):
        self._list: list[ControlSignal] = []
        self._lock = threading.Lock()
        self._logger = logger

    def set_logger(self, logger: Any) -> None:
        self._logger = logger

    def push(self, signal: ControlSignal) -> None:
        with self._lock:
            self._list.append(signal)

    def get_pending(self) -> ControlSignal | None:
        with self._lock:
            return self._list[0] if self._list else None

    def pop_pending(self) -> ControlSignal | None:
        with self._lock:
            return self._list.pop(0) if self._list else None

    def report_realized(self, signal: ControlSignal, lsl_time: float) -> None:
        if self._logger is not None:
            self._logger.log_stimulus_realized(lsl_time, signal.action, signal.params)
