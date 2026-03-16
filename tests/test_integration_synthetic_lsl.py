"""Integration test: synthetic LSL stream -> pipeline -> control signals and log."""

import json
import tempfile
import threading
import time
from pathlib import Path

import numpy as np
import pytest
import pylsl

from looplab.buffer.ring_buffer import RingBuffer
from looplab.controller.loop import ControllerLoop
from looplab.controller.policy import IdentityPolicy
from looplab.features.simple import SimpleFeatureExtractor
from looplab.logging.event_logger import EventLogger
from looplab.logging.writers import JSONLWriter
from looplab.model.example_models import IdentityModel
from looplab.preprocess.pipeline import noop_preprocess


def _run_fake_lsl_outlet(duration: float, n_channels: int = 2, srate: float = 100.0):
    """Push fake EEG chunks for duration seconds."""
    cf = getattr(pylsl, "cf_float32", getattr(pylsl, "ChannelFormat", None))
    if cf is None:
        cf = 1
    info = pylsl.StreamInfo(
        "FakeEEG",
        "EEG",
        n_channels,
        srate,
        cf,
        "fake_source_123",
    )
    outlet = pylsl.StreamOutlet(info, chunk_size=16)
    start = pylsl.local_clock()
    sample = np.zeros(n_channels, dtype=np.float32)
    while pylsl.local_clock() - start < duration:
        sample[:] = np.random.randn(n_channels).astype(np.float32)
        outlet.push_sample(sample.tolist())
        time.sleep(0.02)
    outlet.__del__()


def test_synthetic_lsl_to_control_and_log():
    """Start fake LSL outlet, connect inlet, fill buffer, run loop tick, check log."""
    log_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    log_path = log_file.name
    log_file.close()

    # Start fake outlet in background
    duration = 2.0
    thread = threading.Thread(target=_run_fake_lsl_outlet, args=(duration, 2, 50.0))
    thread.start()
    time.sleep(0.8)

    try:
        from looplab.streams.lsl_client import LSLInletClient

        client = LSLInletClient(name="FakeEEG", timeout=5.0, chunk_size=8)
        try:
            client.connect()
        except RuntimeError as e:
            if "No LSL stream" in str(e):
                pytest.skip("LSL stream discovery failed (network/sandbox); skip integration test")
            raise

        buffer = RingBuffer(max_samples=500, n_channels=2)
        writer = JSONLWriter(log_path)
        writer.open()
        logger = EventLogger(writer)
        class DummyAdapter:
            def push(self, signal):
                pass

        adapter = DummyAdapter()

        loop = ControllerLoop(
            buffer=buffer,
            preprocess=noop_preprocess,
            feature_extractor=SimpleFeatureExtractor(),
            model=IdentityModel(),
            policy=IdentityPolicy(validity_seconds=1.0),
            adapter=adapter,
            logger=logger,
            min_samples=10,
        )

        # Pull a few chunks and tick
        for _ in range(20):
            data, ts = client.pull_chunk(timeout=0.2, max_samples=32)
            if data.size > 0:
                buffer.append(data, ts)
            if buffer.size >= 10:
                c = loop.tick()
                if c is not None:
                    break
            time.sleep(0.05)

        client.close()
        writer.close()
    finally:
        thread.join(timeout=5)

    # Check log has at least one control_signal
    events = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    Path(log_path).unlink(missing_ok=True)

    control_events = [e for e in events if e.get("event_type") == "control_signal"]
    assert len(control_events) >= 1
    assert control_events[0]["payload"].get("action") == "set_value"
