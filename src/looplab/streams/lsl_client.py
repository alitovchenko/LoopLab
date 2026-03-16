"""LSL stream discovery and inlet client with pull_chunk wrapper."""

from __future__ import annotations

from typing import Any

import numpy as np
import pylsl


def discover_stream(
    name: str | None = None,
    type_: str | None = None,
    source_id: str | None = None,
    timeout: float = 5.0,
):
    """Resolve a single LSL stream by name, type, or source_id. Returns first match."""
    pred = ""
    if name:
        pred = f"name='{name}'"
    if type_:
        pred = f"type='{type_}'" if not pred else f"{pred} and type='{type_}'"
    if source_id:
        pred = f"source_id='{source_id}'" if not pred else f"{pred} and source_id='{source_id}'"
    streams = pylsl.resolve_streams(wait_time=timeout)
    if pred:
        # pylsl.resolve_bypred is not in all versions; filter manually
        for s in streams:
            info = s
            if name and s.name() != name:
                continue
            if type_ and s.type() != type_:
                continue
            if source_id and s.source_id() != source_id:
                continue
            return s
        raise RuntimeError(f"No LSL stream found matching {pred} within {timeout}s")
    if not streams:
        raise RuntimeError(f"No LSL streams found within {timeout}s")
    return streams[0]


def create_inlet(
    stream_info: pylsl.StreamInfo,
    chunk_size: int = 0,
    max_buffered: float = 360.0,
) -> pylsl.StreamInlet:
    """Create a StreamInlet with optional chunk size and max buffered duration (seconds)."""
    chunk = chunk_size if chunk_size > 0 else pylsl.IRREGULAR_RATE
    return pylsl.StreamInlet(stream_info, chunk_size=chunk, max_buffered=max_buffered)


class LSLInletClient:
    """Thin wrapper around pylsl.StreamInlet: discover, connect, pull_chunk with timestamps."""

    def __init__(
        self,
        name: str | None = None,
        type_: str | None = None,
        source_id: str | None = None,
        chunk_size: int = 0,
        max_buffered: float = 360.0,
        timeout: float = 5.0,
    ):
        self._name = name
        self._type = type_
        self._source_id = source_id
        self._chunk_size = chunk_size
        self._max_buffered = max_buffered
        self._timeout = timeout
        self._inlet: pylsl.StreamInlet | None = None
        self._stream_info: pylsl.StreamInfo | None = None

    def connect(self) -> None:
        """Discover stream and open inlet."""
        info = discover_stream(
            name=self._name,
            type_=self._type,
            source_id=self._source_id,
            timeout=self._timeout,
        )
        self._stream_info = info
        self._inlet = create_inlet(info, chunk_size=self._chunk_size, max_buffered=self._max_buffered)

    def pull_chunk(
        self,
        timeout: float = 0.0,
        max_samples: int = 0,
    ) -> tuple[np.ndarray, list[float] | None]:
        """
        Pull a chunk of samples. Returns (data, timestamps).
        data shape: (n_samples, n_channels). timestamps are LSL local_clock times per sample.
        """
        if self._inlet is None:
            raise RuntimeError("LSLInletClient not connected; call connect() first")
        if max_samples <= 0:
            max_samples = 1024  # arbitrary default
        samples, timestamps = self._inlet.pull_chunk(max_samples=max_samples, timeout=timeout)
        if not samples:
            return np.array([]).reshape(0, 0), None
        data = np.array(samples)
        ts = list(timestamps) if timestamps else None
        return data, ts

    def close(self) -> None:
        """Close the inlet."""
        if self._inlet is not None:
            self._inlet.close()
            self._inlet = None

    def __enter__(self) -> "LSLInletClient":
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
