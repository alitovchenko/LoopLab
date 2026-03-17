"""Feature extractor protocol and registry for plug-in extractors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Type

import numpy as np

from looplab.exceptions import UnknownComponentError

# Registry: name -> (class or factory, optional default config)
_FEATURE_EXTRACTOR_REGISTRY: dict[str, tuple[Type["FeatureExtractor"] | Callable[..., "FeatureExtractor"], dict[str, Any]]] = {}


class FeatureExtractor(ABC):
    """Input: preprocessed window (channels x time). Output: feature vector or dict."""

    @abstractmethod
    def extract(
        self,
        data: np.ndarray,
        t_start: float,
        t_end: float,
        context: dict[str, Any] | None = None,
    ) -> np.ndarray | dict[str, np.ndarray]:
        """
        Extract features from window. data shape (n_channels, n_times) or (n_times, n_channels).
        t_start, t_end are LSL-time interval for the window.
        Returns 1D array or dict of named arrays.
        """
        ...


def get_feature_extractor_registry() -> dict[str, tuple[Type[FeatureExtractor] | Callable[..., FeatureExtractor], dict[str, Any]]]:
    return _FEATURE_EXTRACTOR_REGISTRY.copy()


def register_feature_extractor(
    name: str,
    extractor_class: Type[FeatureExtractor] | Callable[..., FeatureExtractor],
    default_config: dict[str, Any] | None = None,
) -> None:
    """Register a feature extractor by name for config-based lookup."""
    _FEATURE_EXTRACTOR_REGISTRY[name] = (extractor_class, default_config or {})


def create_feature_extractor(name: str, config: dict[str, Any] | None = None) -> FeatureExtractor:
    """Instantiate a registered feature extractor by name with optional config overrides."""
    if name not in _FEATURE_EXTRACTOR_REGISTRY:
        raise UnknownComponentError("feature_extractor", name, list(_FEATURE_EXTRACTOR_REGISTRY))
    extractor_class, defaults = _FEATURE_EXTRACTOR_REGISTRY[name]
    opts = {**defaults, **(config or {})}
    if isinstance(extractor_class, type):
        return extractor_class(**opts)
    return extractor_class(**opts)
