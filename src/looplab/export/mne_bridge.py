"""Build MNE Raw from LoopLab ``stream.jsonl`` (optional ``mne`` dependency)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from looplab.replay.stream_recorder import load_recorded_chunks


def _require_mne():
    try:
        import mne  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "MNE is required for export: pip install -e \".[mne]\""
        ) from e
    return __import__("mne", fromlist=["*"])


def stream_jsonl_to_mne_raw(
    stream_path: str | Path,
    *,
    config: dict[str, Any] | None = None,
    channel_name_prefix: str = "EEG",
) -> tuple[Any, dict[str, Any]]:
    """
    Load ``stream.jsonl`` into ``mne.io.RawArray``.

    Returns:
        raw: MNE Raw instance
        meta: dict with t0_first_sample (LSL time), sfreq, n_samples, notes

    Channel names default to EEG001, EEG002, ... (``channel_name_prefix`` + zero-padded index).
    Data are treated as volts for MNE (values passed through as-is; document as arbitrary units).
    """
    mne = _require_mne()
    stream_path = Path(stream_path)
    chunks = load_recorded_chunks(stream_path)
    if not chunks:
        raise ValueError(f"No chunks in {stream_path}")

    parts = []
    for data, ts in chunks:
        parts.append(np.asarray(data, dtype=np.float64))
    data = np.vstack(parts)
    n_samples, n_channels = data.shape

    all_ts: list[float] = []
    for _, ts in chunks:
        all_ts.extend(ts)
    times = np.asarray(all_ts, dtype=np.float64)
    if times.size != n_samples:
        raise ValueError("Timestamp count does not match sample count")

    t0 = float(times[0])
    if times.size >= 2:
        dt = np.diff(times)
        dt = dt[dt > 1e-12]
        sfreq = float(1.0 / np.median(dt)) if dt.size else 250.0
    else:
        sfreq = 250.0

    buf_n = None
    if config:
        buf = config.get("buffer") or {}
        buf_n = buf.get("n_channels")
    if buf_n is not None and int(buf_n) != n_channels:
        # Trust stream over stale config
        pass

    ch_names = [f"{channel_name_prefix}{i + 1:03d}" for i in range(n_channels)]
    info = mne.create_info(ch_names, sfreq, ch_types="eeg")
    # (n_channels, n_samples)
    data_t = data.T
    raw = mne.io.RawArray(data_t, info, verbose=False)
    meta = {
        "t0_first_sample_lsl": t0,
        "sfreq": sfreq,
        "n_samples": n_samples,
        "n_channels": n_channels,
        "note": (
            "Times are LSL seconds; sfreq from median dt. Values are passed through as Volts "
            "in MNE convention—treat as arbitrary unless calibrated."
        ),
    }
    return raw, meta


def load_config_snapshot(run_dir: Path) -> dict[str, Any]:
    p = run_dir / "config_snapshot.json"
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)
