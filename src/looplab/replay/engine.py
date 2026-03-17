"""Replay engine: read event log + recorded stream, re-run pipeline, verify determinism."""

from __future__ import annotations

from typing import Any, Iterator

from looplab.logging.schema import LogEvent
from looplab.replay.stream_recorder import load_recorded_chunks


def read_log_events(path: str) -> Iterator[LogEvent]:
    """Read JSONL log file and yield LogEvents."""
    import json
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield LogEvent.from_dict(json.loads(line))


class ReplayEngine:
    """
    Replay from event log and (optionally) recorded stream. Can re-run model/pipeline
    and compare outputs to logged control_signal events.
    """

    def __init__(
        self,
        log_path: str,
        stream_path: str | None = None,
    ):
        self._log_path = log_path
        self._stream_path = stream_path
        self._events: list[LogEvent] = []
        self._chunks: list[tuple[Any, list[float]]] = []

    def load(self) -> None:
        """Load log events and optional stream chunks."""
        self._events = list(read_log_events(self._log_path))
        if self._stream_path:
            self._chunks = load_recorded_chunks(self._stream_path)

    def get_events(self) -> list[LogEvent]:
        return list(self._events)

    def get_control_sequence(self) -> list[dict[str, Any]]:
        """Return payloads of control_signal events in order."""
        out = []
        for ev in self._events:
            if getattr(ev.event_type, "value", ev.event_type) == "control_signal":
                out.append(ev.payload)
        return out

    def get_chunks(self) -> list[tuple[Any, list[float]]]:
        return list(self._chunks)

    def set_chunks(self, chunks: list[tuple[Any, list[float]]]) -> None:
        """Set chunks from memory (e.g. after applying stressors). Overwrites any loaded from stream_path."""
        self._chunks = list(chunks)

    def set_events(self, events: list[LogEvent]) -> None:
        """Set events from memory. Overwrites any loaded from log_path."""
        self._events = list(events)
