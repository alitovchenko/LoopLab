"""Model and control policy API."""

from looplab.model.base import Model, ModelOutput, get_model_registry, register_model
from looplab.model.example_models import IdentityModel

__all__ = [
    "Model",
    "ModelOutput",
    "get_model_registry",
    "register_model",
    "IdentityModel",
]
