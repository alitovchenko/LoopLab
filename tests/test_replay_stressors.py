"""Tests for stream and event stressors (Workstream F)."""

import json
import tempfile
from pathlib import Path

import numpy as np

from looplab.benchmark.report import latency_report
from looplab.buffer.ring_buffer import RingBuffer
from looplab.controller.policy import create_policy
from looplab.features.base import create_feature_extractor
from looplab.logging.schema import EventType, LogEvent
from looplab.model.base import create_model
from looplab.preprocess.pipeline import noop_preprocess
from looplab.replay.engine import ReplayEngine
from looplab.replay.runner import ReplayRunner
from looplab.replay.stressors import (
    add_abrupt_change,
    add_drift,
    add_noise,
    delay_realized_events,
    drop_chunks,
    drop_chunks_by_index,
    drop_chunks_in_interval,
    drop_realized_events,
    drop_realized_in_interval,
)


def _make_chunks(n: int, n_channels: int = 2, chunk_size: int = 8, srate: float = 50.0, t0: float = 1000.0):
    rng = np.random.default_rng(42)
    chunks = []
    for i in range(n):
        samples = rng.standard_normal((chunk_size, n_channels)).astype(np.float64)
        ts = [t0 + (i * chunk_size + j) / srate for j in range(chunk_size)]
        chunks.append((samples, ts))
    return chunks


def test_drop_chunks():
    chunks = _make_chunks(20)
    out = drop_chunks(chunks, 0.5, rng=np.random.default_rng(123))
    assert len(out) < 20
    out2 = drop_chunks(chunks, 0.0)
    assert len(out2) == 20
    out3 = drop_chunks(chunks, 1.0)
    assert len(out3) == 0


def test_drop_chunks_by_index():
    chunks = _make_chunks(10)
    out = drop_chunks_by_index(chunks, {1, 3, 5})
    assert len(out) == 7
    out2 = drop_chunks_by_index(chunks, set())
    assert len(out2) == 10


def test_drop_chunks_in_interval():
    chunks = _make_chunks(10, chunk_size=8, t0=1000.0)
    t_start = 1000.0 + 2 * 8 / 50.0
    t_end = 1000.0 + 5 * 8 / 50.0
    out = drop_chunks_in_interval(chunks, t_start, t_end)
    assert len(out) <= 10


def test_add_noise():
    chunks = _make_chunks(5)
    t0 = 1000.0
    t1 = 1002.0
    out = add_noise(chunks, 1.0, t0, t1, rng=np.random.default_rng(1))
    assert len(out) == 5
    for (s, ts), (s2, ts2) in zip(chunks, out):
        assert ts == ts2
        assert s.shape == s2.shape
    assert not np.allclose(np.concatenate([c[0] for c in chunks]), np.concatenate([c[0] for c in out]))


def test_add_drift():
    chunks = _make_chunks(5, chunk_size=4)
    out = add_drift(chunks, 0.01)
    assert len(out) == 5
    out2 = add_drift(chunks, [0.01, -0.01])
    assert len(out2) == 5


def test_add_abrupt_change():
    chunks = _make_chunks(5, chunk_size=4, t0=1000.0)
    out = add_abrupt_change(chunks, at_time=1000.1, scale=2.0, offset=1.0)
    assert len(out) == 5
    for (s, ts), (s2, ts2) in zip(chunks, out):
        assert ts == ts2
        if ts and ts[-1] >= 1000.1:
            np.testing.assert_allclose(s2, s * 2.0 + 1.0)


def test_delay_realized_events():
    events = [
        LogEvent(EventType.STIMULUS_INTENDED, 1000.0, {}),
        LogEvent(EventType.STIMULUS_REALIZED, 1000.05, {}),
        LogEvent(EventType.STIMULUS_INTENDED, 1001.0, {}),
        LogEvent(EventType.STIMULUS_REALIZED, 1001.02, {}),
    ]
    out = delay_realized_events(events, 0.5)
    assert len(out) == 4
    assert out[0].lsl_time == 1000.0
    assert out[1].lsl_time == 1000.55
    assert out[2].lsl_time == 1001.0
    assert out[3].lsl_time == 1001.52


def test_drop_realized_events():
    events = [
        LogEvent(EventType.STIMULUS_REALIZED, 1000.0, {}),
        LogEvent(EventType.STIMULUS_REALIZED, 1001.0, {}),
        LogEvent(EventType.STIMULUS_REALIZED, 1002.0, {}),
    ]
    out = drop_realized_events(events, {0, 2})
    assert len(out) == 1
    assert out[0].lsl_time == 1001.0


def test_drop_realized_in_interval():
    events = [
        LogEvent(EventType.STIMULUS_REALIZED, 1000.0, {}),
        LogEvent(EventType.STIMULUS_REALIZED, 1000.5, {}),
        LogEvent(EventType.STIMULUS_REALIZED, 1001.5, {}),
    ]
    out = drop_realized_in_interval(events, 1000.2, 1001.0)
    assert len(out) == 2
    assert out[0].lsl_time == 1000.0
    assert out[1].lsl_time == 1001.5


def test_stress_replay_missing_chunks_diverges():
    """Replay with dropped chunks yields fewer replayed controls than logged."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as log_f:
        for i in range(10):
            log_f.write(json.dumps({
                "event_type": "control_signal",
                "lsl_time": 1000.0 + i * 0.1,
                "payload": {"action": "set_value", "params": {"value": 0.5}},
            }) + "\n")
        log_path = log_f.name
    with tempfile.NamedTemporaryFile(suffix=".stream.jsonl", delete=False) as stream_f:
        stream_path = stream_f.name
    with tempfile.NamedTemporaryFile(suffix=".stress.jsonl", delete=False) as stress_f:
        stress_stream_path = stress_f.name
    try:
        chunks = _make_chunks(10)
        from looplab.replay.stream_recorder import StreamRecorder
        rec = StreamRecorder(stream_path)
        rec.open()
        for s, ts in chunks:
            rec.record(s, ts)
        rec.close()
        engine = ReplayEngine(log_path, stream_path)
        engine.load()
        logged = engine.get_control_sequence()
        stressed = drop_chunks_by_index(chunks, {2, 5, 7})
        assert len(stressed) < len(logged)
        rec2 = StreamRecorder(stress_stream_path)
        rec2.open()
        for s, ts in stressed:
            rec2.record(s, ts)
        rec2.close()
        engine2 = ReplayEngine(log_path, stress_stream_path)
        buffer = RingBuffer(500, 2)
        runner = ReplayRunner(
            engine2, buffer, noop_preprocess,
            create_feature_extractor("simple", {}), create_model("identity", {}), create_policy("identity", {}),
        )
        replayed = runner.run(seed=42)
        assert len(replayed) < len(logged)
        assert len(replayed) == len(stressed)
    finally:
        Path(log_path).unlink(missing_ok=True)
        Path(stream_path).unlink(missing_ok=True)
        Path(stress_stream_path).unlink(missing_ok=True)


def test_event_stressor_benchmark_absent_realized():
    """Latency report with fewer realized than intended: pairs by min(len)."""
    events = [
        LogEvent(EventType.STIMULUS_INTENDED, 1000.0, {}),
        LogEvent(EventType.STIMULUS_REALIZED, 1000.05, {}),
        LogEvent(EventType.STIMULUS_INTENDED, 1001.0, {}),
        LogEvent(EventType.STIMULUS_REALIZED, 1001.02, {}),
        LogEvent(EventType.STIMULUS_INTENDED, 1002.0, {}),
    ]
    out = drop_realized_events(events, {1, 2})
    points = []
    for e in out:
        et = getattr(e.event_type, "value", e.event_type)
        if et in ("stimulus_intended", "stimulus_realized"):
            points.append((et, e.lsl_time))
    report = latency_report(points)
    by = report.get("by_label", {})
    assert len(by.get("stimulus_intended", [])) == 3
    assert len(by.get("stimulus_realized", [])) == 1
    assert len(by["stimulus_intended"]) > len(by["stimulus_realized"])


def test_faulty_model_pipeline_completes():
    """Pipeline with faulty model (invalid output) completes; policy receives value."""
    from looplab.model.base import create_model
    model = create_model("faulty", {"fail_probability": 1.0, "fail_mode": "nan", "seed": 99})
    from looplab.controller.policy import create_policy
    from looplab.controller.signals import ModelOutput
    policy = create_policy("identity", {})
    out = model.run(np.array([1.0, 2.0]), None)
    assert isinstance(out, ModelOutput)
    import math
    assert math.isnan(out.value)
    control = policy(out, {"t_start": 0, "t_end": 1})
    assert control.action == "set_value"
    assert math.isnan(control.params["value"])
