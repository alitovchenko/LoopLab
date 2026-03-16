"""Rolling feature extraction from preprocessed windows."""

from looplab.features.base import FeatureExtractor
from looplab.features.simple import SimpleFeatureExtractor

__all__ = [
    "FeatureExtractor",
    "SimpleFeatureExtractor",
]
