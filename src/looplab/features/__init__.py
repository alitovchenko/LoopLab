"""Rolling feature extraction from preprocessed windows."""

from looplab.features.base import (
    FeatureExtractor,
    create_feature_extractor,
    get_feature_extractor_registry,
    register_feature_extractor,
)
from looplab.features.simple import SimpleFeatureExtractor

__all__ = [
    "FeatureExtractor",
    "SimpleFeatureExtractor",
    "create_feature_extractor",
    "get_feature_extractor_registry",
    "register_feature_extractor",
]
