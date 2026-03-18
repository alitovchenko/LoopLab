"""Adaptive difficulty / vigilance demo: policy that bins model output and emits multi-parameter adaptation."""

from __future__ import annotations

from looplab.controller.policy import Policy, register_policy
from looplab.controller.signals import ControlSignal, ModelOutput
from looplab.streams.clock import lsl_clock

# State-dependent mapping: tier 0 = easy, 1 = medium, 2 = hard (vigilance / attention load)
_VIGILANCE_PARAMS = (
    {"target_frequency_hz": 1.0, "stimulus_duration_sec": 0.3, "iti_sec": 0.5, "distractor_load": 0},
    {"target_frequency_hz": 1.5, "stimulus_duration_sec": 0.25, "iti_sec": 0.4, "distractor_load": 1},
    {"target_frequency_hz": 2.0, "stimulus_duration_sec": 0.2, "iti_sec": 0.3, "distractor_load": 2},
)


class AdaptiveDifficultyPolicy(Policy):
    """
    Bin model output (scalar) into 3 difficulty levels and emit set_difficulty with multi-parameter
    adaptation (difficulty_tier, target_frequency_hz, stimulus_duration_sec, iti_sec, distractor_load).
    level 0 = easy, 1 = medium, 2 = hard.
    """

    def __init__(
        self,
        validity_seconds: float = 1.0,
        threshold_low: float = -0.3,
        threshold_high: float = 0.3,
    ):
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
        params = {"level": level, "difficulty_tier": level, **_VIGILANCE_PARAMS[level]}
        return ControlSignal(
            action="set_difficulty",
            params=params,
            valid_until_lsl_time=now + self._validity_seconds,
        )


register_policy("adaptive_difficulty", AdaptiveDifficultyPolicy, {
    "validity_seconds": 1.0,
    "threshold_low": -0.3,
    "threshold_high": 0.3,
})
