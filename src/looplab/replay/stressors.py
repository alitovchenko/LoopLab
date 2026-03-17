"""Stream and event stressors for fault simulation (Workstream F).

Operates on chunk lists and event lists so replay and reporting can be tested
under missing chunks, noise, drift, abrupt state changes, delayed/absent realized events.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from looplab.logging.schema import LogEvent


# Chunk list type: list of (samples array, timestamps list)
ChunkList = list[tuple[np.ndarray, list[float]]]


def drop_chunks(chunks: ChunkList, drop_ratio: float, rng: np.random.Generator | None = None) -> ChunkList:
    """Drop a fraction of chunks at random. Returns a shorter list."""
    if drop_ratio <= 0:
        return list(chunks)
    if drop_ratio >= 1:
        return []
    rng = rng or np.random.default_rng()
    n = len(chunks)
    keep = rng.random(n) > drop_ratio
    return [c for c, k in zip(chunks, keep) if k]


def drop_chunks_by_index(chunks: ChunkList, indices_to_drop: set[int]) -> ChunkList:
    """Drop chunks at the given indices. Indices out of range are ignored."""
    return [c for i, c in enumerate(chunks) if i not in indices_to_drop]


def drop_chunks_in_interval(chunks: ChunkList, t_start: float, t_end: float) -> ChunkList:
    """Drop chunks whose time range overlaps [t_start, t_end]. Uses chunk's last timestamp."""
    out: ChunkList = []
    for samples, timestamps in chunks:
        if not timestamps:
            out.append((samples, timestamps))
            continue
        t_last = timestamps[-1] if timestamps else 0.0
        t_first = timestamps[0] if timestamps else 0.0
        if t_last < t_start or t_first > t_end:
            out.append((samples, timestamps))
    return out


def add_noise(
    chunks: ChunkList,
    noise_scale: float,
    t_start: float,
    t_end: float,
    rng: np.random.Generator | None = None,
) -> ChunkList:
    """Add Gaussian noise to chunks whose time range overlaps [t_start, t_end]."""
    rng = rng or np.random.default_rng()
    out: ChunkList = []
    for samples, timestamps in chunks:
        samples = np.asarray(samples, dtype=np.float64)
        if not timestamps:
            out.append((samples.copy(), list(timestamps)))
            continue
        t_first, t_last = timestamps[0], timestamps[-1]
        if t_last < t_start or t_first > t_end:
            out.append((samples.copy(), list(timestamps)))
            continue
        noise = rng.standard_normal(samples.shape).astype(np.float64) * noise_scale
        out.append((samples + noise, list(timestamps)))
    return out


def add_drift(
    chunks: ChunkList,
    drift_per_channel: list[float] | float,
    t0: float | None = None,
) -> ChunkList:
    """Add linear drift in time to each channel. drift_per_channel: slope per channel or single scalar."""
    out: ChunkList = []
    for samples, timestamps in chunks:
        samples = np.asarray(samples, dtype=np.float64)
        if not timestamps:
            out.append((samples.copy(), list(timestamps)))
            continue
        ts = np.array(timestamps, dtype=np.float64)
        if t0 is None:
            t0 = ts[0]
        if isinstance(drift_per_channel, (int, float)):
            drift = (ts - t0) * float(drift_per_channel)
            if samples.ndim == 2:
                drift = drift[:, np.newaxis]
            out.append((samples + drift, list(timestamps)))
        else:
            slopes = np.array(drift_per_channel, dtype=np.float64)
            if samples.ndim == 2 and samples.shape[1] == len(slopes):
                drift = (ts - t0)[:, np.newaxis] * slopes
                out.append((samples + drift, list(timestamps)))
            else:
                out.append((samples.copy(), list(timestamps)))
    return out


def add_abrupt_change(
    chunks: ChunkList,
    at_time: float,
    scale: float = 1.0,
    offset: float = 0.0,
) -> ChunkList:
    """For chunks with t_end >= at_time, apply scale and offset: samples = samples * scale + offset."""
    out: ChunkList = []
    for samples, timestamps in chunks:
        samples = np.asarray(samples, dtype=np.float64)
        if not timestamps:
            out.append((samples.copy(), list(timestamps)))
            continue
        t_last = timestamps[-1]
        if t_last >= at_time:
            out.append((samples * scale + offset, list(timestamps)))
        else:
            out.append((samples.copy(), list(timestamps)))
    return out


def delay_realized_events(events: list[LogEvent], delay_seconds: float) -> list[LogEvent]:
    """Shift lsl_time of each stimulus_realized event by delay_seconds. Returns new list."""
    out: list[LogEvent] = []
    for ev in events:
        et = getattr(ev.event_type, "value", ev.event_type)
        if et == "stimulus_realized":
            out.append(LogEvent(event_type=ev.event_type, lsl_time=ev.lsl_time + delay_seconds, payload=ev.payload))
        else:
            out.append(LogEvent(event_type=ev.event_type, lsl_time=ev.lsl_time, payload=dict(ev.payload)))
    return out


def drop_realized_events(events: list[LogEvent], indices: set[int]) -> list[LogEvent]:
    """Remove stimulus_realized events at the given indices (indices among realized events only)."""
    realized_indices: list[int] = []
    for i, ev in enumerate(events):
        et = getattr(ev.event_type, "value", ev.event_type)
        if et == "stimulus_realized":
            realized_indices.append(i)
    to_drop = {realized_indices[j] for j in indices if 0 <= j < len(realized_indices)}
    return [ev for i, ev in enumerate(events) if i not in to_drop]


def drop_realized_in_interval(events: list[LogEvent], t_start: float, t_end: float) -> list[LogEvent]:
    """Remove stimulus_realized events whose lsl_time is in [t_start, t_end]."""
    out: list[LogEvent] = []
    for ev in events:
        et = getattr(ev.event_type, "value", ev.event_type)
        if et == "stimulus_realized" and t_start <= ev.lsl_time <= t_end:
            continue
        out.append(LogEvent(event_type=ev.event_type, lsl_time=ev.lsl_time, payload=dict(ev.payload)))
    return out
