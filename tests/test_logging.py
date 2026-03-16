"""Unit tests for event logging."""

import json
import tempfile
from pathlib import Path

from looplab.logging.schema import EventType, LogEvent
from looplab.logging.writers import JSONLWriter
from looplab.logging.event_logger import EventLogger


def test_log_event_to_dict():
    ev = LogEvent(event_type=EventType.CONTROL_SIGNAL, lsl_time=123.45, payload={"action": "set"})
    d = ev.to_dict()
    assert d["event_type"] == "control_signal"
    assert d["lsl_time"] == 123.45
    assert d["payload"]["action"] == "set"


def test_log_event_from_dict():
    d = {"event_type": "control_signal", "lsl_time": 1.0, "payload": {}}
    ev = LogEvent.from_dict(d)
    assert ev.event_type == EventType.CONTROL_SIGNAL
    assert ev.lsl_time == 1.0


def test_jsonl_writer():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        path = f.name
    try:
        w = JSONLWriter(path)
        w.open()
        w.write(LogEvent(event_type=EventType.STREAM_CHUNK, lsl_time=1.0, payload={"n": 1}))
        w.write(LogEvent(event_type=EventType.FEATURES, lsl_time=2.0, payload={}))
        w.close()
        lines = Path(path).read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["event_type"] == "stream_chunk"
    finally:
        Path(path).unlink(missing_ok=True)


def test_event_logger_log_control():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        path = f.name
    try:
        w = JSONLWriter(path)
        logger = EventLogger(w)
        w.open()
        logger.log_control_signal(1.0, "set_value", {"value": 0.5}, 2.0)
        w.close()
        lines = Path(path).read_text().strip().split("\n")
        d = json.loads(lines[0])
        assert d["event_type"] == "control_signal"
        assert d["payload"]["action"] == "set_value"
    finally:
        Path(path).unlink(missing_ok=True)
