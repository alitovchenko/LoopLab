"""Adaptive difficulty demo: policy that bins model output into difficulty levels."""

from __future__ import annotations

from looplab.controller.policy import Policy, register_policy
from looplab.controller.signals import ControlSignal, ModelOutput
from looplab.streams.clock import lsl_clock


class AdaptiveDifficultyPolicy(Policy):
    """
    Bin model output (scalar) into 3 difficulty levels and emit set_difficulty.
    level 0 = easy, 1 = medium, 2 = hard.
    """

    def __init__(self, validity_seconds: float = 1.0, threshold_low: float = -0.3, threshold_high: float = 0.3):
        self._validity_seconds = validity_seconds
        self._threshold_low = threshold_low
        self._threshold_high = threshold_high

    def __call__(
        self,
        model_output: ModelOutput,
        context: dict,
    ) -> ControlSignal:
        val = model_output.value
        if isinstance(val, (list, tuple)):
            val = float(val[0]) if val else 0.0
        else:
            val = float(val)
        if val <= self._threshold_low:
            level = 0
        elif val >= self._threshold_high:
            level = 2
        else:
            level = 1
        now = lsl_clock()
        return ControlSignal(
            action="set_difficulty",
            params={"level": level},
            valid_until_lsl_time=now + self._validity_seconds,
        )


register_policy("adaptive_difficulty", AdaptiveDifficultyPolicy, {
    "validity_seconds": 1.0,
    "threshold_low": -0.3,
    "threshold_high": 0.3,
})
