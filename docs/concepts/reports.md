# Reports

**Role:** Turn a run directory into **methods-ready** prose and JSON without re-parsing raw JSONL by hand.

| Artifact | Use |
|----------|-----|
| **`run_report.md` / `run_report.json`** | Single place for window size, buffer, feature/model/policy names, adaptation target, backend, duration, timing (e2e, intended→realized), warning status, experiment/adaptation event counts, replay summary, diagnostics summary, **artifact inventory** |
| **`components_manifest.json`** | Resolved classes, default vs effective config per component, LoopLab version |
| **`benchmark_summary.json`** | Full latency stats, per-stage latencies (see [Benchmarking](../benchmarking.md) for definitions) |
| **`RUN_SUMMARY.md`** | Shorter package summary; points to run_report for detail |

**CLI:**

```bash
python -m looplab report --run-dir <dir> --human
python -m looplab report --run-dir <dir> --write
```

**PsychoPy e2e:** With `paradigm: psychopy_e2e`, run_report adds **Task-level summary (PsychoPy bridge)** (trials, stimulus intended/realized counts, etc.).

See: [Quickstart](../quickstart.md), [Benchmarking](../benchmarking.md).

**Offline interchange:** To export continuous EEG and events to **BIDS** / **MNE** (FIF) for lab pipelines, see [Export formats](../export_formats.md) and `python -m looplab export-bids` (optional `mne`).
