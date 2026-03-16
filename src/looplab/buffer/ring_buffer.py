"""Ring buffer for stream samples and LSL timestamps. Fixed capacity, drop oldest."""

from __future__ import annotations

import threading
from typing import Optional

import numpy as np


class RingBuffer:
    """
    Ring buffer storing (samples, timestamps). Samples shape (n_samples, n_channels).
    Fixed capacity in number of samples; appending beyond capacity drops oldest.
    Thread-safe via a single lock.
    """

    def __init__(self, max_samples: int, n_channels: int):
        if max_samples <= 0 or n_channels <= 0:
            raise ValueError("max_samples and n_channels must be positive")
        self._max_samples = max_samples
        self._n_channels = n_channels
        self._data = np.zeros((max_samples, n_channels), dtype=np.float64)
        self._times: np.ndarray = np.zeros(max_samples, dtype=np.float64)
        self._head = 0  # next write index
        self._size = 0  # current number of valid samples
        self._lock = threading.Lock()

    def append(self, samples: np.ndarray, timestamps: list[float] | np.ndarray | None) -> None:
        """
        Append chunk. samples shape (n, n_channels). timestamps length n or None.
        """
        n = samples.shape[0]
        if samples.shape[1] != self._n_channels:
            raise ValueError(
                f"Expected {self._n_channels} channels, got {samples.shape[1]}"
            )
        if timestamps is not None:
            ts = np.asarray(timestamps, dtype=np.float64)
            if len(ts) != n:
                raise ValueError("timestamps length must match sample count")
        else:
            ts = np.full(n, np.nan, dtype=np.float64)

        with self._lock:
            for i in range(n):
                self._data[self._head] = samples[i]
                self._times[self._head] = ts[i]
                self._head = (self._head + 1) % self._max_samples
                if self._size < self._max_samples:
                    self._size += 1

    def get_window(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Return (samples, timestamps) for the current window in chronological order.
        samples shape (size, n_channels), timestamps shape (size,).
        """
        with self._lock:
            if self._size == 0:
                return np.array([]).reshape(0, self._n_channels), np.array([])
            start = (self._head - self._size + self._max_samples) % self._max_samples
            if start + self._size <= self._max_samples:
                data = self._data[start : start + self._size].copy()
                times = self._times[start : start + self._size].copy()
            else:
                part1 = self._max_samples - start
                data = np.vstack([self._data[start:], self._data[: self._size - part1]])
                times = np.concatenate(
                    [self._times[start:], self._times[: self._size - part1]]
                )
            return data, times

    @property
    def size(self) -> int:
        """Current number of samples in the buffer."""
        with self._lock:
            return self._size

    @property
    def max_samples(self) -> int:
        return self._max_samples

    @property
    def n_channels(self) -> int:
        return self._n_channels
