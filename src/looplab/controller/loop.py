"""Controller loop: buffer -> preprocess -> features -> model -> policy -> adapter + logging."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from looplab.controller.signals import ControlSignal
from looplab.streams.clock import lsl_clock

if TYPE_CHECKING:
    from looplab.buffer.ring_buffer import RingBuffer
    from looplab.features.base import FeatureExtractor
    from looplab.logging.event_logger import EventLogger
    from looplab.model.base import Model
    from looplab.controller.policy import Policy
    from looplab.preprocess.pipeline import PreprocessPipeline


class ControllerLoop:
    """
    One iteration: get window from buffer -> preprocess -> features -> model -> policy
    -> push ControlSignal to task adapter and log intended event.
    Does not block on the task.
    """

    def __init__(
        self,
        buffer: "RingBuffer",
        preprocess: Callable[[Any], Any],
        feature_extractor: "FeatureExtractor",
        model: "Model",
        policy: "Policy",
        adapter: Any,
        logger: "EventLogger | None" = None,
        min_samples: int = 1,
    ):
        self._buffer = buffer
        self._preprocess = preprocess
        self._feature_extractor = feature_extractor
        self._model = model
        self._policy = policy
        self._adapter = adapter
        self._logger = logger
        self._min_samples = min_samples

    def set_logger(self, logger: "EventLogger") -> None:
        self._logger = logger

    def tick(self, context: dict[str, Any] | None = None) -> ControlSignal | None:
        """
        Run one iteration. Returns ControlSignal if produced, else None (e.g. insufficient data).
        """
        data, times = self._buffer.get_window()
        if data.shape[0] < self._min_samples:
            return None

        t_start = float(times[0]) if len(times) else 0.0
        t_end = float(times[-1]) if len(times) else 0.0

        # Preprocess: (n_samples, n_channels) -> same shape expected by feature extractor
        preprocessed = self._preprocess(data)
        if preprocessed.ndim == 2 and preprocessed.shape[0] > preprocessed.shape[1]:
            # Feature extractor expects (n_channels, n_times)
            preprocessed = preprocessed.T

        ctx = context or {}
        ctx["t_start"] = t_start
        ctx["t_end"] = t_end

        features = self._feature_extractor.extract(preprocessed, t_start, t_end, ctx)
        if isinstance(features, dict):
            features = features.get("features", list(features.values())[0] if features else None)
        if features is None:
            return None
        import numpy as np
        features_arr = np.asarray(features).ravel()

        now = lsl_clock()
        model_output = self._model.run(features_arr, ctx)
        control = self._policy(model_output, ctx)

        if self._logger:
            self._logger.log_features(now, list(features_arr.shape))
            self._logger.log_model_output(now, model_output.value, model_output.confidence)
            self._logger.log_control_signal(
                now,
                control.action,
                control.params,
                control.valid_until_lsl_time,
            )
            self._logger.log_stimulus_intended(now, control.action, control.params)

        if hasattr(self._adapter, "push"):
            self._adapter.push(control)
        elif callable(getattr(self._adapter, "receive", None)):
            self._adapter.receive(control)

        return control
