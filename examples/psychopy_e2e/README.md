# PsychoPy end-to-end example

Fully documented end-to-end example: a **real PsychoPy task** receives control signals from LoopLab, changes a task parameter (stimulus size), returns realized timing via `report_realized`, and produces the **full LoopLab artifact set**.

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
| `events.jsonl` | Event log: `control_signal`, `stimulus_intended`, `stimulus_realized`, `benchmark_latency`. |
| `stream.jsonl` | Recorded stream chunks (synthetic). |
| `replay_result.json` | Replay outcome (match counts, determinism check). |
| `benchmark_summary.json` | Latency report: e2e and intended→realized means/stats. |
| `session_summary.json` | High-level summary: duration, artifacts_ok, replay_ok, backend, timestamp. |
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

For the full contract (who creates the adapter, timing, and how to get `lsl_clock`), see [docs/psychopy_integration.md](../../docs/psychopy_integration.md).
