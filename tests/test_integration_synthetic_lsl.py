"""Integration test: synthetic LSL stream -> pipeline -> control signals and log.

This test requires native LSL discovery and is skipped by default. Run it explicitly with:
  RUN_LSL_TESTS=1 python -m pytest tests/test_integration_synthetic_lsl.py
CI runs it only in a dedicated integration job (RUN_LSL_TESTS=1).
"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

if os.environ.get("RUN_LSL_TESTS") != "1":
    pytest.skip(
        "LSL integration tests disabled (set RUN_LSL_TESTS=1 to run)",
        allow_module_level=True,
    )

from looplab.buffer.ring_buffer import RingBuffer
from looplab.controller.loop import ControllerLoop
from looplab.controller.policy import IdentityPolicy
from looplab.features.simple import SimpleFeatureExtractor
from looplab.logging.event_logger import EventLogger
from looplab.logging.writers import JSONLWriter
from looplab.model.example_models import IdentityModel
from looplab.preprocess.pipeline import noop_preprocess
from looplab.streams.synthetic import start_synthetic_outlet_thread


def test_synthetic_lsl_to_control_and_log():
    """Start fake LSL outlet, connect inlet, fill buffer, run loop tick, check log."""
    log_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    log_path = log_file.name
    log_file.close()

    # Start fake outlet in background
    duration = 2.0
    thread = start_synthetic_outlet_thread(duration, n_channels=2, srate=50.0, stream_name="FakeEEG")
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
