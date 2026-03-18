"""Simple feature extractor: per-channel mean and variance (or band power proxy)."""

from __future__ import annotations

import numpy as np

from looplab.features.base import FeatureExtractor, register_feature_extractor


class SimpleFeatureExtractor(FeatureExtractor):
    """
    Stateless extractor: data (n_channels, n_times) -> concat(mean per channel, var per channel).
    If data is (n_times, n_channels), treat columns as channels.
    """

    def __init__(self, use_variance: bool = True):
        self._use_variance = use_variance

    def extract(
        self,
        data: np.ndarray,
        t_start: float,
        t_end: float,
        context: dict | None = None,
    ) -> np.ndarray:
        data = np.asarray(data, dtype=np.float64)
        if data.ndim == 1:
            data = data.reshape(1, -1)
        if data.shape[0] > data.shape[1]:
            data = data.T
        # now (n_channels, n_times)
        n_channels = data.shape[0]
        mean = data.mean(axis=1)
        if self._use_variance:
            var = data.var(axis=1)
            return np.concatenate([mean, var])
        return mean


register_feature_extractor("simple", SimpleFeatureExtractor, {"use_variance": True}, component_version="1.0.0")
