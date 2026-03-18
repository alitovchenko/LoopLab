"""Chunk generator: yields (data, timestamps) with dropouts, irregular timing, invalid windows, signal scenarios."""

from __future__ import annotations

from typing import Iterator

import numpy as np

from looplab.synthetic.config import (
    InvalidWindowsConfig,
    IrregularTimingConfig,
    NoiseBurstConfig,
    SyntheticConfig,
)
from looplab.synthetic.signals import (
    add_noise_burst,
    drifting_latent_state,
    regime_shift,
    stationary_clean,
)


def generate_chunks(
    cfg: SyntheticConfig,
    duration_sec: float,
    n_channels: int,
    chunk_size: int,
    srate: float,
    start_time: float,
    base_chunk_interval: float = 0.02,
) -> Iterator[tuple[np.ndarray, list[float], bool]]:
    """
    Yield (data, timestamps, valid) for each chunk. valid=False means invalid window (caller may skip tick).
    Applies: scenario signal, dropouts, noise bursts, irregular timing, invalid windows.
    """
    rng = np.random.default_rng(cfg.seed)
    dropouts = cfg.dropouts
    noise_bursts = cfg.noise_bursts
    irregular = cfg.irregular_timing
    invalid = cfg.invalid_windows

    t = start_time
    sample_idx = 0
    chunk_index = 0

    while t - start_time < duration_sec:
        # Dropout: skip this chunk with probability
        if dropouts.enabled and dropouts.probability > 0 and rng.random() < dropouts.probability:
            sample_idx += chunk_size
            chunk_index += 1
            continue

        # Irregular timing: jitter next delivery
        interval = base_chunk_interval
        if irregular.enabled and irregular.jitter_seconds > 0:
            interval = max(0.001, interval + rng.uniform(-irregular.jitter_seconds, irregular.jitter_seconds))

        ts_start = start_time + sample_idx / srate
        timestamps = [ts_start + j / srate for j in range(chunk_size)]

        # Invalid window: emit NaN chunk with probability (caller can skip or handle)
        if invalid.enabled and invalid.probability > 0 and rng.random() < invalid.probability:
            data = np.full((chunk_size, n_channels), np.nan, dtype=np.float64)
            yield data, timestamps, False
            sample_idx += chunk_size
            chunk_index += 1
            t += interval
            continue

        # Signal generator by scenario
        if cfg.scenario == "drifting_latent_state" or cfg.scenario == "drifting_attention":
            data = drifting_latent_state(
                chunk_size, n_channels, rng, ts_start, srate, cfg.drift_per_channel
            )
        elif cfg.scenario == "regime_shift":
            data = regime_shift(
                chunk_size, n_channels, rng, ts_start, srate,
                cfg.regime_shift_times, cfg.regime_scale, cfg.regime_offset,
            )
        else:
            data = stationary_clean(chunk_size, n_channels, rng)

        # Noise bursts: add noise in windows every_n_seconds
        if noise_bursts.enabled and noise_bursts.every_n_seconds > 0:
            burst_center = (chunk_index * base_chunk_interval) // noise_bursts.every_n_seconds * noise_bursts.every_n_seconds
            burst_t_start = start_time + burst_center - 0.1
            burst_t_end = start_time + burst_center + 0.1
            data = add_noise_burst(
                data, ts_start, ts_start + chunk_size / srate,
                burst_t_start, burst_t_end, srate, noise_bursts.scale, rng,
            )

        yield data, timestamps, True
        sample_idx += chunk_size
        chunk_index += 1
        t += interval
