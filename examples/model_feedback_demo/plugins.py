"""Model-based feedback demo: model outputs 0/1, policy maps to feedback type A/B."""

from __future__ import annotations

import numpy as np

from looplab.controller.policy import Policy, register_policy
from looplab.controller.signals import ControlSignal, ModelOutput
from looplab.model.base import Model, register_model
from looplab.streams.clock import lsl_clock


class BinaryFeedbackModel(Model):
    """
    Threshold on feature mean: output 0 or 1 for feedback condition.
    """

    def __init__(self, threshold: float = 0.0):
        self._threshold = threshold

    def run(
        self,
        features: np.ndarray,
        context: dict | None = None,
    ) -> ModelOutput:
        f = np.asarray(features).ravel()
        mean_val = float(np.mean(f))
        out = 1 if mean_val >= self._threshold else 0
        return ModelOutput(value=out, confidence=1.0)


class FeedbackPolicy(Policy):
    """
    Map model value 0/1 to show_feedback with type "A" or "B".
    """

    def __init__(self, validity_seconds: float = 1.0):
        self._validity_seconds = validity_seconds

    def __call__(
        self,
        model_output: ModelOutput,
        context: dict,
    ) -> ControlSignal:
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


register_model("binary_feedback", BinaryFeedbackModel, {"threshold": 0.0})
register_policy("feedback", FeedbackPolicy, {"validity_seconds": 1.0})
