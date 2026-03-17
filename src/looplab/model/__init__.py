"""Model and control policy API."""

from looplab.model.base import Model, ModelOutput, get_model_registry, register_model
from looplab.model.example_models import IdentityModel
from looplab.model import stress_models  # noqa: F401 - registers "faulty"

__all__ = [
    "Model",
    "ModelOutput",
    "get_model_registry",
    "register_model",
    "IdentityModel",
]
