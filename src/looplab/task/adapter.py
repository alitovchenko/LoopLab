"""Abstract task adapter: receives control signals, translates to task commands."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from looplab.controller.signals import ControlSignal


class TaskAdapter(ABC):
    """Receives control signals (queue or callback). Logs realized events when change applied."""

    @abstractmethod
    def push(self, signal: ControlSignal) -> None:
        """Accept a control signal; apply when task is ready (e.g. next frame or trial)."""
        ...

    @abstractmethod
    def get_pending(self) -> ControlSignal | None:
        """Return next pending signal if any, without removing. For polling from task."""
        ...

    @abstractmethod
    def pop_pending(self) -> ControlSignal | None:
        """Remove and return next pending signal. Task calls this when applying."""
        ...

    def report_realized(self, signal: ControlSignal, lsl_time: float) -> None:
        """Override to log stimulus_realized (e.g. after win.flip()). Default no-op."""
        pass
