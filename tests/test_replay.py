"""Unit tests for replay (no LSL required)."""

import json
import tempfile
from pathlib import Path

import numpy as np

from looplab.buffer.ring_buffer import RingBuffer
from looplab.controller.policy import IdentityPolicy
from looplab.features.simple import SimpleFeatureExtractor
from looplab.model.example_models import IdentityModel
from looplab.preprocess.pipeline import noop_preprocess
from looplab.replay.engine import ReplayEngine, read_log_events
from looplab.replay.runner import ReplayRunner
from looplab.replay.stream_recorder import StreamRecorder, load_recorded_chunks


def test_stream_recorder_load():
    with tempfile.NamedTemporaryFile(suffix=".stream.jsonl", delete=False) as f:
        path = f.name
    try:
        rec = StreamRecorder(path)
        rec.open()
        samples = np.array([[1.0, 2.0], [3.0, 4.0]])
        ts = [1.0, 2.0]
        rec.record(samples, ts)
        rec.close()
        chunks = load_recorded_chunks(path)
        assert len(chunks) == 1
        np.testing.assert_array_almost_equal(chunks[0][0], samples)
        assert chunks[0][1] == [1.0, 2.0]
    finally:
        Path(path).unlink(missing_ok=True)


def test_replay_engine_load_log_only():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(json.dumps({"event_type": "control_signal", "lsl_time": 1.0, "payload": {"action": "set_value"}}) + "\n")
        path = f.name
    try:
        engine = ReplayEngine(path, stream_path=None)
        engine.load()
        events = engine.get_events()
        assert len(events) == 1
        assert getattr(events[0].event_type, "value", events[0].event_type) == "control_signal"
        seq = engine.get_control_sequence()
        assert len(seq) == 1
        assert seq[0]["action"] == "set_value"
    finally:
        Path(path).unlink(missing_ok=True)


def test_replay_runner_determinism():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as log_f:
        log_f.write(json.dumps({"event_type": "control_signal", "lsl_time": 1.0, "payload": {"action": "set_value", "params": {"value": 0.5}}}) + "\n")
        log_path = log_f.name
    with tempfile.NamedTemporaryFile(suffix=".stream.jsonl", delete=False) as stream_f:
        stream_path = stream_f.name
    try:
        rec = StreamRecorder(stream_path)
        rec.open()
        for i in range(5):
            samples = np.ones((4, 2)) * (i + 1)
            ts = [float(i * 4 + j) for j in range(4)]
            rec.record(samples, ts)
        rec.close()

        engine = ReplayEngine(log_path, stream_path)
        buffer = RingBuffer(max_samples=100, n_channels=2)
        model = IdentityModel()
        policy = IdentityPolicy()
        runner = ReplayRunner(engine, buffer, noop_preprocess, SimpleFeatureExtractor(), model, policy)
        replayed = runner.run(seed=42)
        assert len(replayed) >= 1
    finally:
        Path(log_path).unlink(missing_ok=True)
        Path(stream_path).unlink(missing_ok=True)
