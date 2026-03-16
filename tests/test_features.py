"""Unit tests for feature extractor."""

import numpy as np
import pytest

from looplab.features.simple import SimpleFeatureExtractor


def test_simple_feature_extractor_mean_var():
    ext = SimpleFeatureExtractor(use_variance=True)
    # (2 channels, 4 times)
    data = np.array([[1.0, 2.0, 3.0, 4.0], [0.0, 0.0, 0.0, 0.0]])
    out = ext.extract(data, 0.0, 1.0, None)
    assert out.ndim == 1
    assert len(out) == 4  # 2 means + 2 vars
    np.testing.assert_array_almost_equal(out[:2], [2.5, 0.0])
    np.testing.assert_array_almost_equal(out[2], 1.25)
    np.testing.assert_array_almost_equal(out[3], 0.0)


def test_simple_feature_extractor_mean_only():
    ext = SimpleFeatureExtractor(use_variance=False)
    data = np.array([[1.0, 2.0], [3.0, 4.0]])
    out = ext.extract(data, 0.0, 1.0, None)
    assert len(out) == 2
    np.testing.assert_array_almost_equal(out, [1.5, 3.5])
