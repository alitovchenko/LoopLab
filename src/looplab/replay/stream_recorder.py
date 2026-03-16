"""Record stream chunks to file during live run for replay."""

from __future__ import annotations

import json
from pathlib import Path
from typing import BinaryIO, TextIO

import numpy as np


class StreamRecorder:
    """
    Append recorded chunks: each line JSON with t_start, t_end, n_samples, and base64 or
    raw array shape + dump. Use LSL time for t_start/t_end.
    """

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file: TextIO | None = None

    def open(self) -> None:
        self._file = open(self._path, "a", encoding="utf-8")

    def record(self, samples: np.ndarray, timestamps: list[float] | np.ndarray) -> None:
        if samples.size == 0:
            return
        if self._file is None:
            self.open()
        assert self._file is not None
        ts = np.asarray(timestamps)
        t_start = float(ts[0])
        t_end = float(ts[-1])
        # Store as list for JSON; for large streams consider binary sidecar
        payload = {
            "t_start": t_start,
            "t_end": t_end,
            "n_samples": samples.shape[0],
            "n_channels": samples.shape[1],
            "data": samples.tolist(),
            "timestamps": ts.tolist(),
        }
        self._file.write(json.dumps(payload) + "\n")
        self._file.flush()

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

    def __enter__(self) -> "StreamRecorder":
        self.open()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def load_recorded_chunks(path: str | Path) -> list[tuple[np.ndarray, list[float]]]:
    """Load recorded stream file: list of (samples, timestamps)."""
    out: list[tuple[np.ndarray, list[float]]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            data = np.array(d["data"], dtype=np.float64)
            ts = d["timestamps"]
            out.append((data, ts))
    return out
