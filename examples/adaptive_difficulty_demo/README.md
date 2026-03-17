# Adaptive difficulty demo

Reference paradigm: **pipeline output drives task difficulty** (e.g. easy / medium / hard). The policy bins the model output (scalar) into three levels and emits control signals that a task can use to adapt difficulty or attention demand.

## Goal

- Demonstrate a closed loop where the **control signal** is explicitly a **difficulty level** (0, 1, 2), not a raw value.
- Produce the same artifact set as the minimal closed-loop demo: config snapshot, event log, recorded stream, replay result, benchmark summary, session summary, and readable run report.

## Config

- **Location:** `config.yaml` in this directory.
- **Key settings:** `model: identity`, `policy: adaptive_difficulty`. The policy uses `policy_config` (e.g. `threshold_low`, `threshold_high`) to bin the identity model’s scalar output into levels 0 (easy), 1 (medium), 2 (hard).

## How to run

From the repo root (or with `PYTHONPATH=src`):

```bash
python examples/adaptive_difficulty_demo/run_demo.py --out-dir demo_out --duration 4 --seed 42
```

Then inspect `demo_out/`: `config_snapshot.json`, `events.jsonl`, `stream.jsonl`, `replay_result.json`, `benchmark_summary.json`, `session_summary.json`, `run_package_summary.json`, `RUN_SUMMARY.md`.

**Readable run report:**

```bash
python -m looplab report --run-dir demo_out --human
```

Use `--write` to refresh `run_package_summary.json` and `RUN_SUMMARY.md` in the run directory.

## Expected behavior

- **Control signals:** Each tick produces a control signal with `action="set_difficulty"` and `params={"level": 0 | 1 | 2}` (0 = easy, 1 = medium, 2 = hard), depending on the binned model output.
- **Replay:** Replay uses the same config (same policy and model). `replay_result.json` should show `"matches": true` for deterministic replay with the same seed.
- **Benchmark:** With `benchmark: true` in config, `benchmark_summary.json` contains e2e and per-stage latency stats.

## Replay support

The run records the stream to `out_dir/stream.jsonl` and events to `out_dir/events.jsonl`. The same `config.yaml` (and thus the same `adaptive_difficulty` policy and identity model) is used for the replay step inside `run_demo.py`, so replay is consistent with the live run.

To re-run replay only (e.g. with a different seed), use the looplab replay CLI with the same config and plugins loaded, or run `run_demo.py` again with a different `--seed`.

## See also

- `examples/closed_loop_demo/` — minimal identity pipeline.
- `examples/model_feedback_demo/` — model output drives feedback type (A/B).
