"""Configurable synthetic scenarios for stress-testing and development."""

from looplab.synthetic.config import (
    AckDelayConfig,
    DropoutConfig,
    EventOmissionConfig,
    InvalidWindowsConfig,
    LowConfidenceConfig,
    NoiseBurstConfig,
    PolicyNoopConfig,
    SyntheticConfig,
    parse_synthetic_config,
)
from looplab.synthetic.generator import generate_chunks

__all__ = [
    "SyntheticConfig",
    "DropoutConfig",
    "NoiseBurstConfig",
    "AckDelayConfig",
    "EventOmissionConfig",
    "PolicyNoopConfig",
    "LowConfidenceConfig",
    "InvalidWindowsConfig",
    "parse_synthetic_config",
    "generate_chunks",
]
