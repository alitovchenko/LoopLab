# LoopLab

**EEG-first, Python-native closed-loop experiment SDK** with LSL, PsychoPy, and deterministic replay.

LoopLab is a research-grade orchestration framework that sits between streaming tools (LSL), online preprocessing, user-defined models, and adaptive task control. It is the coordinator of the closed loop, allowing you to ingest streams, process data, run a model, emit control signals, adapt the task, and log everything for replay and benchmarking.

## Features (Phase 1)

- **LSL-based stream ingestion** with configurable stream selection and chunk size
- **Ring buffer** with LSL-time–aligned samples
- **Online-safe preprocessing** (optional detrend/zscore) and simple rolling feature extraction
- **Model and policy API**: plug-in Python models, control signals with validity window
- **Controller loop**: buffer → preprocess → features → model → policy → task adapter
- **Task adapter** for PsychoPy (queue of control signals; task polls at frame/trial boundaries)
- **Event logging**: intended vs realized stimulus events, all timestamps in LSL time
- **Stream recorder** and **deterministic replay** from log + recorded stream
- **Timing benchmarks**: hooks and simple latency report (e2e, intended→realized)

## Install

```bash
pip install -e .
# Optional: PsychoPy and/or MNE
pip install -e ".[psychopy]"
pip install -e ".[full]"
```

Requires Python 3.10+, `numpy`, `pylsl`.

## Testing

The test suite includes an e2e test that runs `python -m looplab proof-run` in a subprocess, so **the package must be installed** (e.g. editable) before running tests. To confirm proof-run test behavior locally, mirror CI with this exact sequence:

```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .[dev]
.venv/bin/python -m pytest
```

Optional (run proof-run manually):  
`.venv/bin/python -m looplab proof-run --duration 2 --out-dir proof_run_output`

Tests that require native LSL discovery (`tests/test_integration_synthetic_lsl.py`) are skipped unless `RUN_LSL_TESTS=1`. CI runs them in a separate **optional, monitoring-only** job (`test-lsl`): that lane monitors upstream/native LSL compatibility only. A failure there does not indicate a LoopLab regression—only that native LSL is unstable in that environment.

Or after activating the venv: `pip install -e .[dev]` then `python -m pytest`. The `[dev]` extra installs pytest; `pip install -e .` alone is enough if pytest is already available.

## Quick start

1. **Config** (YAML or JSON):

```yaml
lsl:
  name: "MyEEG"
  chunk_size: 32
  timeout: 5.0
buffer:
  max_samples: 10000
  n_channels: 32
preprocess: "none"
feature_extractor: "simple"
model: "identity"
policy: "identity"
task_adapter: "psychopy"
log_path: "session.jsonl"
benchmark: true
```

2. **Run** (with an LSL stream named `MyEEG` running):

```bash
python -m looplab run --config config.yaml --duration 60 --tick-hz 10
```

3. **Replay** a session:

```bash
python -m looplab replay --log session.jsonl --stream session_stream.jsonl --seed 42
```

4. **Benchmark report** from a log that contains benchmark events:

```bash
python -m looplab benchmark --log session.jsonl
```

## Phase 1 proof run (canonical verification)

Phase 1 is validated by a **proof run**: one command, no EEG hardware, synthetic LSL stream, full record → replay → divergence report → benchmark. Use it to verify the installation and that all completion criteria are met.

```bash
python -m looplab proof-run
```

Optional flags: `--duration 4` (seconds), `--out-dir proof_run_output`, `--seed 42`, `--strict` (exit 1 if replay diverges).

**What to expect:** A short session runs (a few seconds), then:
- Replay: `Replay: N/N control signals matched (determinism OK).`
- Benchmark: human-readable summary, e.g. `E2E latency (chunk→control): mean 0.012 s (N samples)`.
- Final line: `Proof-run: all checks passed.`
- Exit code 0 means all checks passed; exit code 2 means LSL discovery failed (e.g. in a restricted environment).

**Canonical proof artifact:** Proof-run writes a fixed set of files under `--out-dir` (e.g. `proof_run_output/`):

| File | Contents |
|------|----------|
| `config_snapshot.json` | RunConfig used for the run (LSL, buffer, paths, etc.), JSON-serializable. |
| `events.jsonl` | Event log (one JSON object per line). |
| `stream.jsonl` | Recorded LSL stream chunks. |
| `replay_result.json` | Replay outcome: `match_count`, `mismatch_count`, `total_logged`, `total_replayed`, `matches`, `divergences`. |
| `benchmark_summary.json` | Latency report (e.g. e2e mean, intended→realized if present). |
| `session_summary.json` | High-level summary: `duration_sec`, `seed`, `out_dir`, `artifacts_ok`, `replay_ok`, `lsl_available`, `timestamp`. |

When LSL discovery fails (exit 2), `out_dir` may still contain `config_snapshot.json` and a minimal `session_summary.json` with `lsl_available: false` and an `error` field.

No hardware or config file required. Another developer can clone the repo, `pip install -e .`, and run this to confirm Phase 1 works end-to-end.

## Project layout

```
src/looplab/
  streams/       # LSL clock, discovery, inlet client
  buffer/        # Ring buffer
  preprocess/    # Pipeline (detrend, zscore)
  features/      # Feature extractor protocol + simple implementation
  model/         # Model protocol, registry, example identity model
  controller/    # ControlSignal, Policy, ControllerLoop
  task/          # TaskAdapter, PsychoPyTaskAdapter
  logging/       # Event schema, JSONL writer, EventLogger
  benchmark/     # Hooks, latency report
  replay/        # StreamRecorder, ReplayEngine, ReplayRunner
  config/        # RunConfig, load_config
  runner.py      # create_runner
  __main__.py    # CLI: run, replay, benchmark, proof-run
```

## PsychoPy integration

Use `PsychoPyTaskAdapter`: the controller pushes `ControlSignal` objects into a thread-safe queue. Your PsychoPy script (same process or documented IPC) should:

1. At each frame or trial boundary, call `adapter.pop_pending()` to get the latest control signal.
2. Apply the change (e.g. set condition, difficulty, stimulus).
3. After `win.flip()`, call `adapter.report_realized(signal, lsl_clock())` so the logger records the realized event.

See `examples/psychopy_simple_task/` for a minimal pattern.

## Deterministic replay

Record the stream during the run with `record_stream_path` in config. Replay loads the event log and recorded chunks, feeds chunks into the buffer in order, and re-runs the same pipeline (preprocess, features, model, policy). Compare replayed control signals to the logged ones to verify determinism (fixed seed, no wall-clock in the pipeline).

## License

MIT.
