# Adaptive difficulty demo

Reference paradigm: **adaptive vigilance / attention** — pipeline output (one scalar state) drives **multi-parameter** task adaptation. The policy bins the model output into three difficulty tiers and emits a single control signal whose `params` include difficulty tier plus derived parameters (target frequency, stimulus duration, ITI, distractor load), so the paradigm reflects state-dependent adaptation of multiple knobs.

## Goal

- Demonstrate a closed loop where the **control signal** is a **multi-parameter set**: `difficulty_tier` (0, 1, 2), `target_frequency_hz`, `stimulus_duration_sec`, `iti_sec`, `distractor_load`, all derived from the same binned state (identity model output).
- Produce the full artifact set: config snapshot, event log, recorded stream, replay result, benchmark summary, session summary, and readable run report; support an optional **degraded** run using the synthetic scenario system.

## Config

- **Location:** `config.yaml` in this directory.
- **Key settings:** `model: identity`, `policy: adaptive_difficulty`. The policy uses `policy_config` (e.g. `threshold_low`, `threshold_high`) to bin the identity model’s scalar output into levels 0 (easy), 1 (medium), 2 (hard) and emits `set_difficulty` with all vigilance params for that tier.

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

## Expected outputs

- **Artifacts:** `config_snapshot.json`, `events.jsonl`, `stream.jsonl`, `replay_result.json`, `benchmark_summary.json`, `session_summary.json`, `run_package_summary.json`, `RUN_SUMMARY.md`. All are written by `run_demo.py`; no extra steps required.
- **events.jsonl:** Contains `control_signal` (with `set_difficulty` and full `params`), `adaptive_params_update`, `block_start`, `trial_start`, `trial_outcome`, and optionally `benchmark_latency`.
- **replay_result.json:** For a normal run with fixed seed, expect `"matches": true` and zero divergences. Under `--degraded`, replay uses the recorded (degraded) stream; fewer matches or different counts are possible and are expected.

## Example run report

After a run, `RUN_SUMMARY.md` is generated automatically in the output directory. It summarizes event counts, replay result, benchmark stats, and any warnings. To regenerate or view it: `python -m looplab report --run-dir demo_out --human --write`.

## Expected behavior

- **Multi-parameter adaptation:** Each tick produces a control signal with `action="set_difficulty"` and `params` containing `level`, `difficulty_tier` (0 | 1 | 2), `target_frequency_hz`, `stimulus_duration_sec`, `iti_sec`, `distractor_load`. Values are derived from the same binned state (0 = easy, 1 = medium, 2 = hard); e.g. higher tier → higher frequency, shorter stimulus/ITI, higher distractor load.
- **Experiment-level logging:** The demo uses the experiment abstraction (see LoopLab "Experiment abstraction" in the main README). It logs `block_start`, `trial_start`, `trial_outcome`, and `adaptive_params_update` so adaptation is described in experiment terms: one block, logical trials every N chunks, with per-trial difficulty and outcome in `events.jsonl`.
- **Replay:** Replay uses the same config (same policy and model). For a normal run, `replay_result.json` should show `"matches": true` with the same seed.
- **Benchmark:** With `benchmark: true` in config, `benchmark_summary.json` contains e2e and per-stage latency stats.

## Degraded scenario

Run with synthetic degradation (dropouts, noise bursts, drifting-attention signal) to test behavior under a degraded stream:

```bash
python examples/adaptive_difficulty_demo/run_demo.py --out-dir degraded_out --duration 4 --degraded
```

The chunk loop uses the synthetic scenario system (`SyntheticConfig`: dropouts probability 0.05, noise bursts every 8 s, scenario `drifting_attention`) instead of the default white-noise stream. Replay, benchmark, and report pipeline run as usual; `session_summary.json` will have `"degraded": true`. Inspect `RUN_SUMMARY.md` and `replay_result.json` for behavior under dropouts/noise (e.g. fewer replay matches or different event counts are expected and documented).

## Replay support

The run records the stream to `out_dir/stream.jsonl` and events to `out_dir/events.jsonl`. The same `config.yaml` (and thus the same `adaptive_difficulty` policy and identity model) is used for the replay step inside `run_demo.py`, so replay is consistent with the live run.

To re-run replay only (e.g. with a different seed), use the looplab replay CLI with the same config and plugins loaded, or run `run_demo.py` again with a different `--seed`.

## See also

- `examples/closed_loop_demo/` — minimal identity pipeline.
- `examples/model_feedback_demo/` — model output drives feedback type (A/B).
