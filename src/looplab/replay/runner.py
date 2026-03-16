"""Replay runner: drive pipeline from recorded data, optionally verify determinism."""

from __future__ import annotations

from typing import Any

import numpy as np

from looplab.buffer.ring_buffer import RingBuffer
from looplab.replay.engine import ReplayEngine
from looplab.replay.stream_recorder import load_recorded_chunks


class ReplayRunner:
    """
    Replay session: feed recorded chunks into buffer, run same pipeline (preprocess,
    features, model, policy), compare control outputs to logged control_signal events.
    """

    def __init__(
        self,
        replay_engine: ReplayEngine,
        buffer: RingBuffer,
        preprocess: Any,
        feature_extractor: Any,
        model: Any,
        policy: Any,
    ):
        self._engine = replay_engine
        self._buffer = buffer
        self._preprocess = preprocess
        self._feature_extractor = feature_extractor
        self._model = model
        self._policy = policy

    def run(self, seed: int | None = 42) -> list[dict[str, Any]]:
        """
        Replay: load chunks, replay into buffer in order, tick pipeline at same points
        as log (e.g. after each chunk). Collect control signals and return comparison
        with logged control_signal payloads.
        """
        if seed is not None:
            np.random.seed(seed)
        self._engine.load()
        chunks = self._engine.get_chunks()
        logged_controls = self._engine.get_control_sequence()

        # Replay chunks into buffer and run pipeline at each chunk
        replayed_controls: list[dict[str, Any]] = []
        for samples, timestamps in chunks:
            self._buffer.append(samples, timestamps)
            data, times = self._buffer.get_window()
            if data.shape[0] < 1:
                continue
            t_start = float(times[0])
            t_end = float(times[-1])
            preprocessed = self._preprocess(data)
            if preprocessed.ndim == 2 and preprocessed.shape[0] > preprocessed.shape[1]:
                preprocessed = preprocessed.T
            ctx = {"t_start": t_start, "t_end": t_end}
            features = self._feature_extractor.extract(preprocessed, t_start, t_end, ctx)
            if isinstance(features, dict):
                features = list(features.values())[0] if features else np.array([])
            features_arr = np.asarray(features).ravel()
            model_output = self._model.run(features_arr, ctx)
            control = self._policy(model_output, ctx)
            replayed_controls.append({
                "action": control.action,
                "params": control.params,
                "valid_until_lsl_time": control.valid_until_lsl_time,
            })
        return replayed_controls
