"""Signal generators for synthetic scenarios: stationary, drifting, regime shift."""

from __future__ import annotations

import numpy as np


def stationary_clean(
    n_samples: int,
    n_channels: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """White Gaussian noise, zero mean unit variance."""
    return rng.standard_normal((n_samples, n_channels)).astype(np.float64)


def drifting_latent_state(
    n_samples: int,
    n_channels: int,
    rng: np.random.Generator,
    t_start: float,
    srate: float,
    drift_per_channel: list[float] | None = None,
) -> np.ndarray:
    """Gaussian noise plus linear drift in time. drift_per_channel: slope per channel (e.g. [0.01, -0.01])."""
    data = rng.standard_normal((n_samples, n_channels)).astype(np.float64)
    if drift_per_channel and len(drift_per_channel) >= n_channels:
        times = np.arange(n_samples, dtype=np.float64) / srate + t_start
        for c in range(n_channels):
            data[:, c] += float(drift_per_channel[c]) * times
    return data


def regime_shift(
    n_samples: int,
    n_channels: int,
    rng: np.random.Generator,
    t_start: float,
    srate: float,
    regime_shift_times: list[float] | None,
    scale: float = 1.0,
    offset: float = 0.0,
) -> np.ndarray:
    """Gaussian noise; after each regime_shift_time, multiply by scale and add offset (step change)."""
    data = rng.standard_normal((n_samples, n_channels)).astype(np.float64)
    if not regime_shift_times:
        return data
    times = np.arange(n_samples, dtype=np.float64) / srate + t_start
    t_end = float(times[-1])
    for t_shift in sorted(regime_shift_times):
        if t_shift > t_end:
            break
        mask = times >= t_shift
        data[mask] = data[mask] * scale + offset
    return data


def add_noise_burst(
    data: np.ndarray,
    t_start: float,
    t_end: float,
    burst_t_start: float,
    burst_t_end: float,
    srate: float,
    scale: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Add Gaussian noise to samples in [burst_t_start, burst_t_end]. data is (n_samples, n_channels); times from t_start at srate."""
    out = data.copy()
    n_samples = data.shape[0]
    times = np.arange(n_samples, dtype=np.float64) / srate + t_start
    mask = (times >= burst_t_start) & (times <= burst_t_end)
    if np.any(mask):
        n = int(np.sum(mask))
        out[mask] += scale * rng.standard_normal((n, data.shape[1])).astype(np.float64)
    return out
