"""Online-safe preprocessing: optional detrend/scale on windowed data."""

from __future__ import annotations

from typing import Callable

import numpy as np


def noop_preprocess(data: np.ndarray) -> np.ndarray:
    """Identity preprocessing; return copy of data."""
    return np.asarray(data, dtype=np.float64).copy()


def detrend_window(data: np.ndarray, axis: int = -1) -> np.ndarray:
    """Remove linear trend along axis (default: time axis). O(window), non-blocking."""
    data = np.asarray(data, dtype=np.float64)
    n = data.shape[axis]
    if n < 2:
        return data.copy()
    x = np.linspace(0, 1, n, dtype=np.float64)
    # fit line per channel (axis 0) along time (axis 1)
    if axis == 0:
        data = data.T
    mean_x = x.mean()
    mean_y = data.mean(axis=1, keepdims=True)
    cov = (data * x).mean(axis=1, keepdims=True) - mean_y * mean_x
    var_x = x.var()
    if var_x == 0:
        return data.T.copy() if axis == 0 else data.copy()
    slope = cov / var_x
    intercept = mean_y - slope * mean_x
    out = data - (slope * x + intercept)
    if axis == 0:
        out = out.T
    return out


def zscore_window(data: np.ndarray, axis: int = -1) -> np.ndarray:
    """Z-score normalize along axis. O(window)."""
    data = np.asarray(data, dtype=np.float64)
    m = data.mean(axis=axis, keepdims=True)
    s = data.std(axis=axis, keepdims=True)
    s = np.where(s == 0, 1.0, s)
    return (data - m) / s


class PreprocessPipeline:
    """Apply a sequence of online-safe steps (each (data) -> data)."""

    def __init__(self, steps: list[Callable[[np.ndarray], np.ndarray]] | None = None):
        self._steps = list(steps) if steps else []

    def add_step(self, step: Callable[[np.ndarray], np.ndarray]) -> None:
        self._steps.append(step)

    def __call__(self, data: np.ndarray) -> np.ndarray:
        out = np.asarray(data, dtype=np.float64)
        for step in self._steps:
            out = step(out)
        return out
