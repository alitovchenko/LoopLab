"""Stress/fault models for testing (Workstream F): invalid model outputs."""

from __future__ import annotations

from typing import Any

import numpy as np

from looplab.controller.signals import ModelOutput
from looplab.model.base import Model, register_model


class FaultyModel(Model):
    """
    With configurable probability returns invalid output (NaN, Inf, or extreme value)
    so pipeline and policy behavior can be tested. Invalid model output is not
    sanitized by the controller; policies may need to handle NaN/Inf.
    """

    def __init__(
        self,
        fail_probability: float = 0.2,
        fail_mode: str = "nan",
        seed: int | None = None,
    ):
        self._fail_probability = fail_probability
        self._fail_mode = fail_mode
        self._rng = np.random.default_rng(seed)
        self._call_count = 0

    def run(
        self,
        features: np.ndarray,
        context: dict[str, Any] | None = None,
    ) -> ModelOutput:
        self._call_count += 1
        if self._rng.random() < self._fail_probability:
            if self._fail_mode == "nan":
                return ModelOutput(value=float("nan"), confidence=0.0)
            if self._fail_mode == "inf":
                return ModelOutput(value=float("inf"), confidence=0.0)
            if self._fail_mode == "neg_inf":
                return ModelOutput(value=float("-inf"), confidence=0.0)
            if self._fail_mode == "extreme":
                return ModelOutput(value=1e10, confidence=0.0)
        f = np.asarray(features).ravel()
        return ModelOutput(value=float(np.mean(f)) if f.size else 0.0, confidence=1.0)


register_model("faulty", FaultyModel, {"fail_probability": 0.2, "fail_mode": "nan"})
