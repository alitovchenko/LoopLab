"""Wrappers for adapter (ack delay, omit realized), policy (no-op periods), model (low-confidence periods)."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

from looplab.controller.signals import ControlSignal, ModelOutput
from looplab.synthetic.config import (
    AckDelayConfig,
    EventOmissionConfig,
    LowConfidenceConfig,
    PolicyNoopConfig,
)


class SyntheticTaskAdapterWrapper:
    """Wraps a task adapter to add ack delay and/or omit realized events (for synthetic scenarios)."""

    def __init__(
        self,
        inner: Any,
        ack_delay: AckDelayConfig,
        event_omission: EventOmissionConfig,
        seed: int = 42,
    ):
        self._inner = inner
        self._ack_delay = ack_delay
        self._event_omission = event_omission
        self._rng = np.random.default_rng(seed)
        self._logger = None

    def set_logger(self, logger: Any) -> None:
        self._logger = logger
        if hasattr(self._inner, "set_logger"):
            self._inner.set_logger(logger)

    def push(self, signal: ControlSignal) -> None:
        self._inner.push(signal)

    def get_pending(self) -> ControlSignal | None:
        return self._inner.get_pending()

    def pop_pending(self) -> ControlSignal | None:
        return self._inner.pop_pending()

    def report_realized(self, signal: ControlSignal, lsl_time: float) -> None:
        if self._event_omission.enabled and self._event_omission.probability > 0:
            if self._rng.random() < self._event_omission.probability:
                return
        if self._ack_delay.enabled and (self._ack_delay.mean != 0 or self._ack_delay.jitter != 0):
            delay_ms = self._ack_delay.mean + self._ack_delay.jitter * (2 * self._rng.random() - 1)
            lsl_time = lsl_time + delay_ms / 1000.0
        if self._logger is not None:
            self._logger.log_stimulus_realized(lsl_time, signal.action, signal.params)


class NoopPolicyWrapper:
    """Wraps a policy to return a no-op control during configured time windows."""

    def __init__(
        self,
        inner: Any,
        config: PolicyNoopConfig,
        start_time: float,
        lsl_clock_fn: Callable[[], float],
    ):
        self._inner = inner
        self._config = config
        self._start_time = start_time
        self._lsl_clock = lsl_clock_fn

    def __call__(self, model_output: ModelOutput, context: dict[str, Any]) -> ControlSignal:
        now = self._lsl_clock()
        if self._config.enabled and self._config.every_n_seconds > 0:
            elapsed = now - self._start_time
            phase = elapsed % self._config.every_n_seconds
            if phase < self._config.duration_seconds:
                return ControlSignal(
                    action="noop",
                    params={},
                    valid_until_lsl_time=now,
                )
        return self._inner(model_output, context)


class LowConfidenceModelWrapper:
    """Wraps a model to return reduced confidence during configured time windows."""

    def __init__(
        self,
        inner: Any,
        config: LowConfidenceConfig,
        start_time: float,
        lsl_clock_fn: Callable[[], float],
    ):
        self._inner = inner
        self._config = config
        self._start_time = start_time
        self._lsl_clock = lsl_clock_fn

    def run(
        self,
        features: np.ndarray,
        context: dict[str, Any] | None = None,
    ) -> ModelOutput:
        out = self._inner.run(features, context)
        now = self._lsl_clock()
        if self._config.enabled and self._config.every_n_seconds > 0:
            elapsed = now - self._start_time
            phase = elapsed % self._config.every_n_seconds
            if phase < self._config.duration_seconds:
                return ModelOutput(
                    value=out.value,
                    confidence=self._config.confidence,
                    metadata=out.metadata,
                )
        return out
