# PsychoPy end-to-end example

Fully documented end-to-end example: a **real PsychoPy task** receives control signals from LoopLab, changes a task parameter (stimulus size), returns realized timing via `report_realized`, and produces the **full LoopLab artifact set**.

## Canonical adaptive PsychoPy path

This folder is the **single canonical** adaptive PsychoPy bridge in the repo: same adapter and clock as production, with a minimal task you can replace.

1. The controller **loop ticks** (synthetic stream here); the adapter queues **`ControlSignal`** from the policy.
2. Each trial (or frame), the task calls **`adapter.pop_pending()`** and reads the pending signal.
3. The task updates a **meaningful parameter** (here: circle **radius** from `params["value"]` for `set_value`).
4. **`win.flip()`**, then **`adapter.report_realized(signal, lsl_clock())`** so intended→realized timing is recorded.
5. Task code logs **`trial_outcome`**, **`adaptive_params_update`** (e.g. `stimulus_size`), **`trial_start`**, **`block_start`** to JSONL for experiment-level reporting.

**Copy this pattern:** Keep the same runner config (`task_adapter: psychopy`), adapter, and clock; only replace the trial loop in `task.py` with your stimuli and design.

| Artifact | What it proves |
|----------|----------------|
| `run_report.md` / `run_report.json` | Methods, pipeline manifest, **Task-level summary (PsychoPy bridge)** (trials, intended/realized counts, IT→R mean). |
| `events.jsonl` | Pairs of `stimulus_intended` / `stimulus_realized`, control signals, trial/block/outcome events. |
| `benchmark_summary.json` | E2E and intended→realized latency stats. |
| `components_manifest.json` | Resolved feature extractor / model / policy (parity with proof-run). |
| `session_summary.json` | Includes `paradigm: psychopy_e2e` to tag this reference path. |

## Purpose

This example demonstrates the complete PsychoPy integration contract in one runnable flow: the controller loop runs in a background thread (synthetic data + tick), the PsychoPy window runs on the main thread, and both share the same adapter and clock. The run produces the same canonical artifacts as `proof-run` so you can inspect event logs, replay, benchmark (including intended→realized latency), and run summaries.

## Prerequisites

- LoopLab installed (e.g. `pip install -e .` from the repo root).
- PsychoPy optional extra: `pip install -e ".[psychopy]"`.

No LSL or hardware required; the example uses the synthetic backend.

## How to run

From the **example directory**:

```bash
cd examples/psychopy_e2e
python run_demo.py --out-dir demo_out --duration 4
```

From the **repo root** (with `PYTHONPATH=src` or after `pip install -e .`):

```bash
python examples/psychopy_e2e/run_demo.py --out-dir demo_out --duration 4 --seed 42
```

Options:

- `--out-dir`: Directory for all output files (default: `demo_out`).
- `--duration`: Run duration in seconds (default: 4).
- `--seed`: Random seed for replay (default: 42).

## What to expect

- A PsychoPy window opens and runs for the given duration. On each trial the task calls `adapter.pop_pending()`, applies the control signal (e.g. circle radius from `params["value"]`), flips, then `adapter.report_realized(signal, lsl_clock())`.
- After the window closes, the script runs replay and writes all artifacts to `--out-dir`.

**Artifacts produced:**

| File | Purpose |
|------|---------|
| `config_snapshot.json` | RunConfig used for the run (reproducibility). |
| `components_manifest.json` | Resolved pipeline components (same role as proof-run). |
| `events.jsonl` | Event log: `control_signal`, `stimulus_intended`, `stimulus_realized`, `benchmark_latency`; plus task-level events `block_start`, `trial_start`, `trial_outcome`, `adaptive_params_update` for experiment-level reporting. |
| `run_report.json` / `run_report.md` | Methods-ready report including task-level summary when tagged as psychopy_e2e. |
| `stream.jsonl` | Recorded stream chunks (synthetic). |
| `replay_result.json` | Replay outcome (match counts, determinism check). |
| `benchmark_summary.json` | Latency report: e2e and intended→realized means/stats. |
| `session_summary.json` | High-level summary: duration, `paradigm: psychopy_e2e`, artifacts_ok, replay_ok, backend, timestamp. |
| `run_package_summary.json` | Component versions, action/window counts, replay status, benchmark readiness, config hash, backend. |
| `RUN_SUMMARY.md` | One-page markdown summary of the run. |

You should see multiple `control_signal` and `stimulus_realized` events in `events.jsonl`, and `benchmark_summary.json` will include intended-to-realized latency when both are present. To get a human-readable report:

```bash
python -m looplab report --run-dir demo_out --human
```

## Contract summary

- **When to call `pop_pending`:** Each trial (or frame), *before* updating the stimulus and calling `win.flip()`, so the next frame reflects the latest control signal.
- **When to call `report_realized`:** *After* `win.flip()`, with the same signal you applied and the time from `lsl_clock()`, so LoopLab can compute intended→realized latency.
- **Same process:** The adapter and clock are shared; the controller loop runs in a background thread and the PsychoPy task on the main thread.

For the full contract (who creates the adapter, timing, and how to get `lsl_clock`), see [docs/psychopy_integration.md](../../docs/psychopy_integration.md). The task optionally uses the **experiment abstraction** (ExperimentState, TrialOutcome): it logs block/trial boundaries and trial outcomes so the event log describes adaptation in experiment terms (e.g. per-trial stimulus_size). See the main README "Experiment abstraction" section.
