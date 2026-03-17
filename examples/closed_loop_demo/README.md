# Closed-loop demo

Reference paradigm: a minimal closed loop with config-driven pipeline (buffer → preprocess → features → model → policy → task adapter), full timing instrumentation, and canonical artifacts.

## Goal

- Validate the Phase 1 contract: control signals logged, stream recorded, replay matches, benchmark summary and session summary produced.
- Run without hardware using synthetic backend, or with live LSL by switching the stream name in config.

## How to run

**Synthetic (no LSL, CI-safe):**

```bash
python -m looplab proof-run --backend synthetic --duration 4 --out-dir closed_loop_demo_out --seed 42
```

Then inspect `closed_loop_demo_out/`: `config_snapshot.json`, `events.jsonl`, `stream.jsonl`, `replay_result.json`, `benchmark_summary.json`, `session_summary.json`.

**Report:**

```bash
python -m looplab report --run-dir closed_loop_demo_out --human
```

**Live (with LSL stream):**

1. Start your LSL stream (or use the synthetic LSL outlet from tests).
2. Edit `config.yaml`: set `lsl.name` to your stream name, and `log_path` / `record_stream_path` as desired.
3. Run: `python -m looplab run --config config.yaml --duration 60 --tick-hz 10`

## What to expect

- **Synthetic:** N control signals (one per chunk), `replay_result.json` with `"matches": true`, benchmark summary with e2e and per-stage latencies (mean, std, p95).
- **Session summary:** `artifacts_ok`, `replay_ok`, `lsl_available` (true for LSL backend, false for synthetic), `backend`.

This demo does not include a PsychoPy window; it uses the same pipeline as proof-run. For a task that applies control signals to a stimulus, see `examples/psychopy_simple_task/`.

## See also

Differentiated reference paradigms:

- **`examples/adaptive_difficulty_demo/`** — pipeline output drives task difficulty (easy/medium/hard); adaptive attention / difficulty control.
- **`examples/model_feedback_demo/`** — model output directly drives feedback type (A/B); model-based feedback.
