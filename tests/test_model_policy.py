"""Unit tests for model and policy."""

import numpy as np
import pytest

from looplab.controller.signals import ModelOutput, ControlSignal
from looplab.model.base import Model, get_model_registry, register_model, create_model
from looplab.model.example_models import IdentityModel
from looplab.controller.policy import IdentityPolicy


def test_identity_model():
    model = IdentityModel()
    out = model.run(np.array([1.0, 2.0, 3.0]), None)
    assert out.value == 2.0
    assert out.confidence == 1.0


def test_identity_model_registered():
    model = create_model("identity", {})
    assert isinstance(model, IdentityModel)


def test_identity_policy():
    policy = IdentityPolicy(validity_seconds=2.0)
    out = ModelOutput(value=0.5, confidence=0.9)
    ctx = {}
    sig = policy(out, ctx)
    assert sig.action == "set_value"
    assert sig.params["value"] == 0.5
    assert sig.valid_until_lsl_time > sig.params["value"]
