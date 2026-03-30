# Export: BIDS, MNE, and common EEG formats

LoopLab records continuous data as **`stream.jsonl`** (JSON lines: `data`, `timestamps`, `t_start`/`t_end` per chunk) and events as **`events.jsonl`**. Those are ideal for replay and benchmarks but are **not** standard lab interchange formats. This page defines how exports map into **MNE-Python** `Raw` and a **BIDS**-compatible tree.

**CLI:** `python -m looplab export-bids` (requires `pip install -e ".[mne]"`).

---

## Source artifacts (run directory)

| File | Role |
|------|------|
| `stream.jsonl` | Chunks from `StreamRecorder` (`src/looplab/replay/stream_recorder.py`); each line: `data` (samples × channels), `timestamps` (LSL seconds), `n_samples`, `n_channels`. |
| `events.jsonl` | `LogEvent` lines (`src/looplab/logging/schema.py`): `event_type`, `lsl_time`, `payload`. |
| `config_snapshot.json` | `lsl.chunk_size`, `buffer.n_channels`, stream `name`; used for defaults when stream is ambiguous. |
| `session_summary.json` | Optional: duration, backend (metadata only for sidecars). |

---

## Time base

- All times are **LSL local time in seconds** (same clock as `events.jsonl`).
- **Onset** for BIDS `events.tsv` = `lsl_time - t0`, where **`t0`** is the timestamp of the **first EEG sample** in the exported continuous array.
- **Sampling frequency** `sfreq`: median of positive `diff(timestamps)` across concatenated stream samples. If chunks have **gaps**, the continuous array is still **gapless concatenation**; effective `sfreq` describes the median **within-chunk** spacing (documented limitation: not identical to a hardware sampler if chunks were irregular).

---

## BIDS entities

One LoopLab **`run_dir`** maps to one BIDS **run** (and one optional **session**):

| Entity | CLI flag | Example |
|--------|----------|---------|
| `sub` | `--sub` | `01` → `sub-01` |
| `ses` | `--ses` | `01` → `ses-01` (optional) |
| `task` | `--task` | `closedloop` → `task-closedloop` |
| `run` | `--run` | `1` → `run-01` |

Files are written under `--bids-root`, e.g.  
`sub-01/ses-01/eeg/sub-01_ses-01_task-closedloop_run-01_eeg.fif`.

---

## Events mapping (`events.jsonl` → BIDS `events.tsv`)

BIDS requires at least `onset`, `duration`, and often `trial_type` or `stimulus_type`. LoopLab uses a **lossy** mapping; full fidelity stays in **`sourcedata/looplab/`** (see below).

| `event_type` | `onset` | `duration` | `trial_type` / notes |
|--------------|---------|------------|----------------------|
| `control_signal` | yes | `0` | `control_signal`; `value` from `payload.params` if serializable |
| `stimulus_intended` | yes | `0` | `stimulus_intended` |
| `stimulus_realized` | yes | `0` | `stimulus_realized` |
| `model_output` | yes | `0` | `model_output` |
| `trial_start` | yes | `0` | `trial_start` |
| `trial_end` | yes | `0` | `trial_end` |
| `block_start` / `block_end` | yes | `0` | same |
| `trial_outcome` | yes | `0` | `trial_outcome` |
| `benchmark_latency` | yes | `0` | `benchmark_latency` (often omitted in analysis BIDS; kept for traceability) |
| `stream_chunk`, `features` | optional skip | — | High volume; **not** exported to BIDS `events.tsv` by default (`--include-all-events` to include with `trial_type=event_type`) |

---

## MNE representation

- **`mne.io.RawArray`** from concatenated `stream.jsonl` data, `create_info` with channel names `EEG001`… or from config.
- Units: documented as **arbitrary** unless you calibrate; BIDS `channels.tsv` uses `uV` as placeholder when unknown—**override in your pipeline** if needed.
- **FIF** is the default export format for MNE round-trip.

---

## Preserved rich log (non-BIDS)

Under `bids_root/sourcedata/looplab/<run_key>/`:

- Copy of **`events.jsonl`** (full payloads).
- **`looplab_export_manifest.json`**: `mapping_version`, source paths, optional content hash.

Nothing in BIDS replaces this; reviewers can cite `sourcedata` for closed-loop provenance.

---

## Limitations

- **Not** a substitute for vendor raw files from the amplifier.
- **Resampling** is not applied by default; severely irregular timing may warrant offline resampling in MNE before group stats.
- **Channel locations** are not set; BIDS `coordsystem` / `electrodes.tsv` are out of scope unless added later.

---

## Python API

```python
from looplab.export.bids_export import export_run_to_bids  # requires mne

export_run_to_bids(
    run_dir="proof_out",
    bids_root="my_bids_dataset",
    sub="01",
    task="closedloop",
    ses="01",
    run=1,
    overwrite=False,
)
```

See source under `src/looplab/export/`.
