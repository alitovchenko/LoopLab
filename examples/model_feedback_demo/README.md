# Model-based feedback demo

Reference paradigm: **model output drives feedback type** with **confidence-aware suppression**. Raw features (e.g. feature mean) are passed through a threshold model → 0/1; the policy maps that to `show_feedback` type "A" or "B", or **suppresses** feedback (type "none") when the model reports low confidence (e.g. when the feature is near the threshold).

## Goal

- Demonstrate a closed loop where the **control signal** is **feedback type** (`"A"`, `"B"`, or `"none"` when suppressed), driven by the model output and its confidence.
- Support **confidence-aware suppression**: when the model is uncertain (e.g. |mean − threshold| < ε), the policy can emit `show_feedback` with `type: "none"` so the task does not show feedback.
- Produce the full artifact set and support an optional **degraded** run using the synthetic scenario system.

## Config

- **Location:** `config.yaml` in this directory.
- **Key settings:** `model: binary_feedback` (with `threshold`, `confidence_epsilon`, `confidence_low`), `policy: feedback` (with `validity_seconds`, `confidence_threshold`). The model outputs 0 or 1 and a confidence; the policy maps 0 → "A", 1 → "B", or "none" when confidence &lt; confidence_threshold.

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

## Expected outputs

- **Artifacts:** `config_snapshot.json`, `events.jsonl`, `stream.jsonl`, `replay_result.json`, `benchmark_summary.json`, `session_summary.json`, `run_package_summary.json`, `RUN_SUMMARY.md`. All are written by `run_demo.py`.
- **events.jsonl:** Contains `control_signal` with `show_feedback` and `params.type` ("A", "B", or "none"). Under degraded runs, event counts may differ; replay may show fewer matches.

## Example run report

After a run, `RUN_SUMMARY.md` is generated in the output directory (event counts, replay result, benchmark stats). To regenerate or view: `python -m looplab report --run-dir demo_out --human --write`.

## Raw features vs model-derived control

- **Pipeline:** Raw feature (e.g. mean from the feature extractor) → **model** (threshold) → 0 or 1 → **policy** → `show_feedback` with type "A" or "B". The control is thus **model-derived**, not the raw feature value.
- **Logging:** `events.jsonl` records `control_signal` (with `action`, `params`). If feature or model outputs are logged elsewhere, you can compare raw features to the emitted control over time.

## Confidence-aware suppression

- The **model** can return `confidence < 1` when the decision is uncertain (e.g. when |mean − threshold| &lt; `confidence_epsilon`); then it uses `confidence_low` (e.g. 0.3).
- The **policy** compares `model_output.confidence` to `confidence_threshold`. When confidence is below that threshold, it emits `show_feedback` with `params={"type": "none"}` so the task can **suppress** feedback instead of showing A or B.
- This allows the paradigm to avoid showing feedback when the model is near the decision boundary.

## Interpretable adaptation traces

- **In events.jsonl:** Look at `control_signal` events: `params.type` will be "A", "B", or "none". Over time you see when feedback is shown vs suppressed. Event counts in `RUN_SUMMARY.md` (e.g. number of control_signal events, or breakdown by type if computed) summarize this.
- **Interpretation:** More "none" when the feature stream hovers near the threshold; more "A"/"B" when the feature is clearly below/above threshold. Under `--degraded`, dropouts and noise can change how often the model is near threshold, so you may see more suppressed feedback or different A/B balance.

## Degraded scenario

Run with synthetic degradation (dropouts, noise bursts, drifting-attention signal):

```bash
python examples/model_feedback_demo/run_demo.py --out-dir degraded_out --duration 4 --degraded
```

The chunk loop uses the synthetic scenario system (dropouts 0.05, noise bursts every 8 s, scenario `drifting_attention`). Replay, benchmark, and report run as usual; `session_summary.json` has `"degraded": true`. Expect potentially fewer replay matches or more suppressed feedback; inspect `RUN_SUMMARY.md` and `replay_result.json` for behavior under degradation.

## Expected behavior

- **Control signals:** Each tick produces `action="show_feedback"` with `params={"type": "A" | "B" | "none"}`. "A" when model is 0 and confidence ≥ threshold; "B" when model is 1 and confidence ≥ threshold; "none" when confidence &lt; confidence_threshold.
- **Replay:** Same config (model and policy). For a normal run with fixed seed, `replay_result.json` should show `"matches": true`. Under `--degraded`, fewer matches or different counts are expected.
- **Benchmark:** With `benchmark: true`, `benchmark_summary.json` contains e2e and per-stage latency stats.

## Replay support

The run records the stream to `out_dir/stream.jsonl` and events to `out_dir/events.jsonl`. The same `config.yaml` (and thus the same `binary_feedback` model and `feedback` policy) is used for the replay step inside `run_demo.py`, so replay is consistent with the live run.

To re-run replay only (e.g. with a different seed), use the looplab replay CLI with the same config and plugins loaded, or run `run_demo.py` again with a different `--seed`.

## See also

- `examples/closed_loop_demo/` — minimal identity pipeline.
- `examples/adaptive_difficulty_demo/` — pipeline output drives task difficulty (easy/medium/hard).
