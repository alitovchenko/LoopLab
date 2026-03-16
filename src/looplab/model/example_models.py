"""Example / trivial models for testing and default pipeline."""

from __future__ import annotations

import numpy as np

from looplab.controller.signals import ModelOutput
from looplab.model.base import Model, register_model


class IdentityModel(Model):
    """Output = mean of features as scalar; confidence = 1.0."""

    def run(
        self,
        features: np.ndarray,
        context: dict | None = None,
    ) -> ModelOutput:
        f = np.asarray(features).ravel()
        return ModelOutput(value=float(np.mean(f)), confidence=1.0)


register_model("identity", IdentityModel, {})
