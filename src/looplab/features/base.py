"""Feature extractor protocol: window -> feature vector."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np


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
