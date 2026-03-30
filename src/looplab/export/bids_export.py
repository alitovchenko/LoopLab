"""Write BIDS EEG layout + FIF from a LoopLab run directory."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from looplab.export.mne_bridge import load_config_snapshot, stream_jsonl_to_mne_raw

SKIP_BIDS_EVENTS_DEFAULT = frozenset({"stream_chunk", "features"})


def _sanitize_task(task: str) -> str:
    t = task.strip().lower().replace(" ", "")
    t = re.sub(r"[^a-z0-9]", "", t)
    return t or "closedloop"


def _bids_prefix(*, sub: str, ses: str | None, task: str, run: int) -> str:
    sub = sub.removeprefix("sub-")
    task = _sanitize_task(task.removeprefix("task-"))
    parts = [f"sub-{sub}"]
    if ses:
        parts.append(f"ses-{ses.removeprefix('ses-')}")
    parts.append(f"task-{task}")
    parts.append(f"run-{run:02d}")
    return "_".join(parts)


def _events_rows(
    events_path: Path,
    t0: float,
    *,
    include_all_events: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(events_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            et = str(d.get("event_type", ""))
            if not include_all_events and et in SKIP_BIDS_EVENTS_DEFAULT:
                continue
            onset = float(d["lsl_time"]) - t0
            rows.append(
                {
                    "onset": round(onset, 6),
                    "duration": 0.0,
                    "trial_type": et,
                }
            )
    return rows


def export_run_to_bids(
    run_dir: str | Path,
    bids_root: str | Path,
    *,
    sub: str,
    task: str,
    ses: str | None = None,
    run: int = 1,
    overwrite: bool = False,
    include_all_events: bool = False,
) -> dict[str, Any]:
    """
    Export ``stream.jsonl`` + ``events.jsonl`` to BIDS under ``bids_root``.

    Writes FIF, ``*_eeg.json``, ``*_channels.tsv``, ``*_events.tsv``,
    ``dataset_description.json``, and ``sourcedata/looplab/`` with full ``events.jsonl`` + manifest.

    Requires MNE: ``pip install -e \".[mne]\"``.
    """
    run_dir = Path(run_dir).resolve()
    bids_root = Path(bids_root).resolve()
    stream_path = run_dir / "stream.jsonl"
    events_path = run_dir / "events.jsonl"
    if not stream_path.exists():
        raise FileNotFoundError(f"Missing {stream_path}")

    config = load_config_snapshot(run_dir)
    raw, meta = stream_jsonl_to_mne_raw(stream_path, config=config)
    prefix = _bids_prefix(sub=sub, ses=ses, task=task, run=run)

    if ses:
        eeg_dir = bids_root / f"sub-{sub.removeprefix('sub-')}" / f"ses-{ses.removeprefix('ses-')}" / "eeg"
    else:
        eeg_dir = bids_root / f"sub-{sub.removeprefix('sub-')}" / "eeg"
    sourcedata_dir = bids_root / "sourcedata" / "looplab" / prefix
    eeg_dir.mkdir(parents=True, exist_ok=True)
    sourcedata_dir.mkdir(parents=True, exist_ok=True)

    fif_name = f"{prefix}_eeg.fif"
    fif_path = eeg_dir / fif_name
    json_path = eeg_dir / f"{prefix}_eeg.json"
    channels_path = eeg_dir / f"{prefix}_channels.tsv"
    events_tsv_path = eeg_dir / f"{prefix}_events.tsv"

    if not overwrite and fif_path.exists():
        raise FileExistsError(f"Refusing to overwrite {fif_path} (use overwrite=True)")

    raw.save(str(fif_path), overwrite=True, verbose=False)

    sfreq = float(meta["sfreq"])
    task_clean = _sanitize_task(task)
    eeg_sidecar = {
        "TaskName": task_clean,
        "SamplingFrequency": sfreq,
        "EEGReference": "unknown",
        "PowerLineFrequency": 50,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(eeg_sidecar, f, indent=2)

    with open(channels_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["name", "type", "units"])
        for ch in raw.ch_names:
            w.writerow([ch, "eeg", "uV"])

    t0 = float(meta["t0_first_sample_lsl"])
    if events_path.exists():
        ev_rows = _events_rows(events_path, t0, include_all_events=include_all_events)
        with open(events_tsv_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["onset", "duration", "trial_type"], delimiter="\t")
            w.writeheader()
            for row in ev_rows:
                w.writerow(row)
    else:
        with open(events_tsv_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["onset", "duration", "trial_type"], delimiter="\t")
            w.writeheader()

    ds_desc = {
        "Name": "LoopLab export",
        "BIDSVersion": "1.9.0",
        "DatasetType": "raw",
        "License": "CC0",
    }
    dd_path = bids_root / "dataset_description.json"
    if overwrite or not dd_path.exists():
        with open(dd_path, "w", encoding="utf-8") as f:
            json.dump(ds_desc, f, indent=2)

    # sourcedata: full events + manifest
    manifest: dict[str, Any] = {
        "mapping_version": "1",
        "run_dir": str(run_dir),
        "bids_prefix": prefix,
        "meta": meta,
    }
    if events_path.exists():
        raw_ev = events_path.read_bytes()
        manifest["events_jsonl_sha256"] = hashlib.sha256(raw_ev).hexdigest()
        dest_ev = sourcedata_dir / "events.jsonl"
        if overwrite or not dest_ev.exists():
            dest_ev.write_bytes(raw_ev)

    manifest_path = sourcedata_dir / "looplab_export_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return {
        "fif": str(fif_path),
        "eeg_json": str(json_path),
        "channels_tsv": str(channels_path),
        "events_tsv": str(events_tsv_path),
        "sourcedata_events": str(sourcedata_dir / "events.jsonl") if events_path.exists() else None,
        "manifest": str(manifest_path),
        "meta": meta,
    }
