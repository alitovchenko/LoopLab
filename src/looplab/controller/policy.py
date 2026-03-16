"""Policy: model output -> control signal."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from looplab.controller.signals import ControlSignal, ModelOutput
from looplab.streams.clock import lsl_clock


class Policy(ABC):
    """Given model output and context, produce a control signal."""

    @abstractmethod
    def __call__(
        self,
        model_output: ModelOutput,
        context: dict[str, Any],
    ) -> ControlSignal:
        ...


class IdentityPolicy(Policy):
    """Map model output value 1:1 to control: action='set_value', params={'value': output.value}."""

    def __init__(self, validity_seconds: float = 1.0):
        self._validity_seconds = validity_seconds

    def __call__(
        self,
        model_output: ModelOutput,
        context: dict[str, Any],
    ) -> ControlSignal:
        now = lsl_clock()
        return ControlSignal(
            action="set_value",
            params={"value": model_output.value},
            valid_until_lsl_time=now + self._validity_seconds,
        )
