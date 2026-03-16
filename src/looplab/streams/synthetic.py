"""Synthetic LSL outlet for testing and proof-run (no hardware)."""

from __future__ import annotations

import threading
import time
from typing import Optional

import numpy as np
import pylsl


def run_synthetic_outlet(
    duration_sec: float,
    n_channels: int = 2,
    srate: float = 100.0,
    stream_name: str = "FakeEEG",
    source_id: str = "fake_source_123",
) -> None:
    """
    Run a fake LSL EEG outlet for the given duration.
    Push random samples at approximately srate Hz. Intended to be run in a thread.
    """
    cf = getattr(pylsl, "cf_float32", getattr(pylsl, "ChannelFormat", None))
    if cf is None:
        cf = 1
    info = pylsl.StreamInfo(
        stream_name,
        "EEG",
        n_channels,
        srate,
        cf,
        source_id,
    )
    outlet = pylsl.StreamOutlet(info, chunk_size=16)
    start = pylsl.local_clock()
    sample = np.zeros(n_channels, dtype=np.float32)
    while pylsl.local_clock() - start < duration_sec:
        sample[:] = np.random.randn(n_channels).astype(np.float32)
        outlet.push_sample(sample.tolist())
        time.sleep(1.0 / srate)
    try:
        outlet.__del__()
    except Exception:
        pass


def start_synthetic_outlet_thread(
    duration_sec: float,
    n_channels: int = 2,
    srate: float = 100.0,
    stream_name: str = "FakeEEG",
) -> threading.Thread:
    """Start the synthetic outlet in a background thread. Returns the thread (call .join() to wait)."""
    thread = threading.Thread(
        target=run_synthetic_outlet,
        args=(duration_sec, n_channels, srate, stream_name),
        daemon=True,
    )
    thread.start()
    return thread
