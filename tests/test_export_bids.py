"""BIDS/MNE export (optional ``mne``)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("mne")

from looplab.export.bids_export import export_run_to_bids
from looplab.export.mne_bridge import stream_jsonl_to_mne_raw


def _write_minimal_run(run: Path) -> Path:
    """Tiny stream + events like a proof-run."""
    run.mkdir(parents=True)
    chunk1 = {
        "t_start": 1000.0,
        "t_end": 1000.0 + 3 / 250.0,
        "n_samples": 2,
        "n_channels": 2,
        "data": [[0.1, 0.2], [0.11, 0.21]],
        "timestamps": [1000.0, 1000.0 + 1 / 250.0],
    }
    chunk2 = {
        "t_start": 1000.0 + 2 / 250.0,
        "t_end": 1000.0 + 4 / 250.0,
        "n_samples": 2,
        "n_channels": 2,
        "data": [[0.12, 0.22], [0.13, 0.23]],
        "timestamps": [1000.0 + 2 / 250.0, 1000.0 + 3 / 250.0],
    }
    with open(run / "stream.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps(chunk1) + "\n")
        f.write(json.dumps(chunk2) + "\n")
    ev = [
        {"event_type": "control_signal", "lsl_time": 1000.01, "payload": {}},
        {"event_type": "stream_chunk", "lsl_time": 1000.02, "payload": {}},
    ]
    with open(run / "events.jsonl", "w", encoding="utf-8") as f:
        for e in ev:
            f.write(json.dumps(e) + "\n")
    (run / "config_snapshot.json").write_text(
        json.dumps({"buffer": {"n_channels": 2}, "lsl": {"chunk_size": 32}}),
        encoding="utf-8",
    )
    return run


def test_stream_jsonl_to_mne_raw_shape(tmp_path):
    run = _write_minimal_run(tmp_path / "r")
    raw, meta = stream_jsonl_to_mne_raw(run / "stream.jsonl", config={})
    assert raw.get_data().shape[0] == 2
    assert raw.get_data().shape[1] == 4
    assert meta["n_channels"] == 2
    assert meta["sfreq"] > 0


def test_export_run_to_bids_writes_files(tmp_path):
    run = _write_minimal_run(tmp_path / "r")
    bids = tmp_path / "bids"
    out = export_run_to_bids(
        run,
        bids,
        sub="01",
        task="closedloop",
        ses="01",
        run=1,
        overwrite=True,
    )
    assert Path(out["fif"]).exists()
    assert Path(out["eeg_json"]).exists()
    assert Path(out["channels_tsv"]).exists()
    assert Path(out["events_tsv"]).exists()
    assert Path(out["manifest"]).exists()
    assert out["sourcedata_events"] and Path(out["sourcedata_events"]).exists()
    tsv = Path(out["events_tsv"]).read_text(encoding="utf-8")
    assert "control_signal" in tsv
    assert "stream_chunk" not in tsv
