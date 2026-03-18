"""Synthetic scenario configuration: signal generator, dropouts, noise, ack delay, etc."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DropoutConfig:
    """Missing chunks: probability per chunk (0-1)."""

    enabled: bool = False
    probability: float = 0.0


@dataclass
class NoiseBurstConfig:
    """Noisy bursts: add Gaussian noise in windows every N seconds."""

    enabled: bool = False
    every_n_seconds: float = 8.0
    scale: float = 1.0


@dataclass
class AckDelayConfig:
    """Delayed task acknowledgments: delay (ms) for report_realized time."""

    enabled: bool = False
    mean: float = 0.0
    jitter: float = 0.0


@dataclass
class EventOmissionConfig:
    """Missing realized events: probability of omitting report_realized."""

    enabled: bool = False
    probability: float = 0.0


@dataclass
class PolicyNoopConfig:
    """Policy no-op periods: during these, policy returns a no-op control (e.g. skip push)."""

    enabled: bool = False
    every_n_seconds: float = 10.0
    duration_seconds: float = 0.5


@dataclass
class LowConfidenceConfig:
    """Low-confidence model output periods: model returns reduced confidence."""

    enabled: bool = False
    every_n_seconds: float = 12.0
    duration_seconds: float = 0.5
    confidence: float = 0.2


@dataclass
class IrregularTimingConfig:
    """Irregular chunk timing: jitter on chunk delivery interval."""

    enabled: bool = False
    jitter_seconds: float = 0.005


@dataclass
class InvalidWindowsConfig:
    """Invalid windows: sometimes emit NaN or empty chunk (controller may skip tick)."""

    enabled: bool = False
    probability: float = 0.0


@dataclass
class SyntheticConfig:
    """Full synthetic scenario: scenario name, seed, and optional degradation schedules."""

    scenario: str = "stationary_clean"
    seed: int = 42
    dropouts: DropoutConfig = field(default_factory=DropoutConfig)
    noise_bursts: NoiseBurstConfig = field(default_factory=NoiseBurstConfig)
    ack_delay_ms: AckDelayConfig = field(default_factory=AckDelayConfig)
    event_omission: EventOmissionConfig = field(default_factory=EventOmissionConfig)
    policy_noop: PolicyNoopConfig = field(default_factory=PolicyNoopConfig)
    low_confidence: LowConfidenceConfig = field(default_factory=LowConfidenceConfig)
    irregular_timing: IrregularTimingConfig = field(default_factory=IrregularTimingConfig)
    invalid_windows: InvalidWindowsConfig = field(default_factory=InvalidWindowsConfig)
    # Optional drift/regime params for scenario
    drift_per_channel: list[float] | None = None
    regime_shift_times: list[float] | None = None
    regime_scale: float = 1.0
    regime_offset: float = 0.0


def _parse_dropouts(d: dict[str, Any] | None) -> DropoutConfig:
    if not d:
        return DropoutConfig()
    return DropoutConfig(
        enabled=d.get("enabled", False),
        probability=float(d.get("probability", 0)),
    )


def _parse_noise_bursts(d: dict[str, Any] | None) -> NoiseBurstConfig:
    if not d:
        return NoiseBurstConfig()
    return NoiseBurstConfig(
        enabled=d.get("enabled", False),
        every_n_seconds=float(d.get("every_n_seconds", 8)),
        scale=float(d.get("scale", 1.0)),
    )


def _parse_ack_delay(d: dict[str, Any] | None) -> AckDelayConfig:
    if not d:
        return AckDelayConfig()
    mean = float(d.get("mean", 0))
    jitter = float(d.get("jitter", 0))
    return AckDelayConfig(
        enabled=d.get("enabled", mean != 0 or jitter != 0),
        mean=mean,
        jitter=jitter,
    )


def _parse_event_omission(d: dict[str, Any] | None) -> EventOmissionConfig:
    if not d:
        return EventOmissionConfig()
    return EventOmissionConfig(
        enabled=d.get("enabled", False),
        probability=float(d.get("probability", 0)),
    )


def _parse_policy_noop(d: dict[str, Any] | None) -> PolicyNoopConfig:
    if not d:
        return PolicyNoopConfig()
    return PolicyNoopConfig(
        enabled=d.get("enabled", False),
        every_n_seconds=float(d.get("every_n_seconds", 10)),
        duration_seconds=float(d.get("duration_seconds", 0.5)),
    )


def _parse_low_confidence(d: dict[str, Any] | None) -> LowConfidenceConfig:
    if not d:
        return LowConfidenceConfig()
    return LowConfidenceConfig(
        enabled=d.get("enabled", False),
        every_n_seconds=float(d.get("every_n_seconds", 12)),
        duration_seconds=float(d.get("duration_seconds", 0.5)),
        confidence=float(d.get("confidence", 0.2)),
    )


def _parse_irregular_timing(d: dict[str, Any] | None) -> IrregularTimingConfig:
    if not d:
        return IrregularTimingConfig()
    return IrregularTimingConfig(
        enabled=d.get("enabled", False),
        jitter_seconds=float(d.get("jitter_seconds", 0.005)),
    )


def _parse_invalid_windows(d: dict[str, Any] | None) -> InvalidWindowsConfig:
    if not d:
        return InvalidWindowsConfig()
    return InvalidWindowsConfig(
        enabled=d.get("enabled", False),
        probability=float(d.get("probability", 0)),
    )


def parse_synthetic_config(d: dict[str, Any] | None) -> SyntheticConfig | None:
    """Parse a raw synthetic config dict (from YAML/JSON) into SyntheticConfig. Returns None if d is None or empty."""
    if not d:
        return None
    return SyntheticConfig(
        scenario=str(d.get("scenario", "stationary_clean")),
        seed=int(d.get("seed", 42)),
        dropouts=_parse_dropouts(d.get("dropouts")),
        noise_bursts=_parse_noise_bursts(d.get("noise_bursts")),
        ack_delay_ms=_parse_ack_delay(d.get("ack_delay_ms")),
        event_omission=_parse_event_omission(d.get("event_omission")),
        policy_noop=_parse_policy_noop(d.get("policy_noop")),
        low_confidence=_parse_low_confidence(d.get("low_confidence")),
        irregular_timing=_parse_irregular_timing(d.get("irregular_timing")),
        invalid_windows=_parse_invalid_windows(d.get("invalid_windows")),
        drift_per_channel=d.get("drift_per_channel"),
        regime_shift_times=d.get("regime_shift_times"),
        regime_scale=float(d.get("regime_scale", 1.0)),
        regime_offset=float(d.get("regime_offset", 0.0)),
    )
