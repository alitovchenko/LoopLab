# Model-based feedback demo

Reference paradigm: **model output directly drives feedback type** (e.g. condition A vs B). The model outputs 0 or 1 (e.g. from a threshold on features); the policy maps that to a control signal that a task can use to show feedback A or B.

## Goal

- Demonstrate a closed loop where the **control signal** is explicitly **feedback type** (`"A"` or `"B"`), driven by the model output.
- Produce the same artifact set as the minimal closed-loop demo: config snapshot, event log, recorded stream, replay result, benchmark summary, session summary, and readable run report.

## Config

- **Location:** `config.yaml` in this directory.
- **Key settings:** `model: binary_feedback`, `policy: feedback`. The model uses `model_config` (e.g. `threshold`) to output 0 or 1; the policy maps 0 → `show_feedback` type "A", 1 → type "B".

## How to run

From the repo root (or with `PYTHONPATH=src`):

```bash
python examples/model_feedback_demo/run_demo.py --out-dir demo_out --duration 4 --seed 42
```

Then inspect `demo_out/`: `config_snapshot.json`, `events.jsonl`, `stream.jsonl`, `replay_result.json`, `benchmark_summary.json`, `session_summary.json`, `run_package_summary.json`, `RUN_SUMMARY.md`.

**Readable run report:**

```bash
python -m looplab report --run-dir demo_out --human
```

Use `--write` to refresh `run_package_summary.json` and `RUN_SUMMARY.md` in the run directory.

## Expected behavior

- **Control signals:** Each tick produces a control signal with `action="show_feedback"` and `params={"type": "A" | "B"}`, depending on whether the model output is 0 or 1.
- **Replay:** Replay uses the same config (same model and policy). `replay_result.json` should show `"matches": true` for deterministic replay with the same seed.
- **Benchmark:** With `benchmark: true` in config, `benchmark_summary.json` contains e2e and per-stage latency stats.

## Replay support

The run records the stream to `out_dir/stream.jsonl` and events to `out_dir/events.jsonl`. The same `config.yaml` (and thus the same `binary_feedback` model and `feedback` policy) is used for the replay step inside `run_demo.py`, so replay is consistent with the live run.

To re-run replay only (e.g. with a different seed), use the looplab replay CLI with the same config and plugins loaded, or run `run_demo.py` again with a different `--seed`.

## See also

- `examples/closed_loop_demo/` — minimal identity pipeline.
- `examples/adaptive_difficulty_demo/` — pipeline output drives task difficulty (easy/medium/hard).
