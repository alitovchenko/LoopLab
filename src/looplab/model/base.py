"""Model protocol and registry for plug-in models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Type

import numpy as np

from looplab.controller.signals import ModelOutput
from looplab.exceptions import UnknownComponentError

# Registry: name -> (class or factory, optional config)
_MODEL_REGISTRY: dict[str, tuple[Type["Model"] | Callable[..., "Model"], dict[str, Any]]] = {}


class Model(ABC):
    """Given features (and optional context), produce a raw output. No notion of task/action."""

    @abstractmethod
    def run(
        self,
        features: np.ndarray,
        context: dict[str, Any] | None = None,
    ) -> ModelOutput:
        """Produce model output from feature vector."""
        ...


def get_model_registry() -> dict[str, tuple[Type[Model] | Callable[..., Model], dict[str, Any]]]:
    return _MODEL_REGISTRY.copy()


def register_model(
    name: str,
    model_class: Type[Model] | Callable[..., Model],
    default_config: dict[str, Any] | None = None,
) -> None:
    """Register a model by name for config-based lookup."""
    _MODEL_REGISTRY[name] = (model_class, default_config or {})


def create_model(name: str, config: dict[str, Any] | None = None) -> Model:
    """Instantiate a registered model by name with optional config overrides."""
    if name not in _MODEL_REGISTRY:
        raise UnknownComponentError("model", name, list(_MODEL_REGISTRY))
    model_class, defaults = _MODEL_REGISTRY[name]
    opts = {**defaults, **(config or {})}
    if isinstance(model_class, type):
        return model_class(**opts)
    return model_class(**opts)
