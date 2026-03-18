"""Model-based feedback demo: model outputs 0/1 with optional confidence; policy maps to feedback A/B or suppresses when low confidence."""

from __future__ import annotations

import numpy as np

from looplab.controller.policy import Policy, register_policy
from looplab.controller.signals import ControlSignal, ModelOutput
from looplab.model.base import Model, register_model
from looplab.streams.clock import lsl_clock


class BinaryFeedbackModel(Model):
    """
    Threshold on feature mean: output 0 or 1 for feedback condition.
    When |mean - threshold| < confidence_epsilon, returns confidence = confidence_low (otherwise 1.0).
    """

    def __init__(
        self,
        threshold: float = 0.0,
        confidence_epsilon: float = 0.2,
        confidence_low: float = 0.3,
    ):
        self._threshold = threshold
        self._confidence_epsilon = confidence_epsilon
        self._confidence_low = confidence_low

    def run(
        self,
        features: np.ndarray,
        context: dict | None = None,
    ) -> ModelOutput:
        f = np.asarray(features).ravel()
        mean_val = float(np.mean(f))
        out = 1 if mean_val >= self._threshold else 0
        if abs(mean_val - self._threshold) < self._confidence_epsilon:
            confidence = self._confidence_low
        else:
            confidence = 1.0
        return ModelOutput(value=out, confidence=confidence)


class FeedbackPolicy(Policy):
    """
    Map model value 0/1 to show_feedback with type "A" or "B".
    When model_output.confidence < confidence_threshold, emits show_feedback with type "none" (suppress feedback).
    """

    def __init__(self, validity_seconds: float = 1.0, confidence_threshold: float = 0.5):
        self._validity_seconds = validity_seconds
        self._confidence_threshold = confidence_threshold

    def __call__(
        self,
        model_output: ModelOutput,
        context: dict,
    ) -> ControlSignal:
        conf = model_output.confidence if model_output.confidence is not None else 1.0
        if conf < self._confidence_threshold:
            now = lsl_clock()
            return ControlSignal(
                action="show_feedback",
                params={"type": "none"},
                valid_until_lsl_time=now + self._validity_seconds,
            )
        val = model_output.value
        if isinstance(val, (list, tuple)):
            val = int(val[0]) if val else 0
        else:
            val = int(val)
        feedback_type = "B" if val else "A"
        now = lsl_clock()
        return ControlSignal(
            action="show_feedback",
            params={"type": feedback_type},
            valid_until_lsl_time=now + self._validity_seconds,
        )


register_model("binary_feedback", BinaryFeedbackModel, {
    "threshold": 0.0,
    "confidence_epsilon": 0.2,
    "confidence_low": 0.3,
})
register_policy("feedback", FeedbackPolicy, {"validity_seconds": 1.0, "confidence_threshold": 0.5})
