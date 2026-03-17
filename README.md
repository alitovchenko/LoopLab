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

**Run report:** For any run (or proof-run output directory), generate a unified report:  
`python -m looplab report --run-dir proof_run_output` or `--log session.jsonl`. Use `--human` for a one-page summary, or default JSON with event counts and timing (e2e, intended→realized, per-stage latencies and jitter when benchmark events are present).

**Canonical proof artifact:** Proof-run writes a fixed set of files under `--out-dir` (e.g. `proof_run_output/`):

| File | Contents |
|------|----------|
| `config_snapshot.json` | RunConfig used for the run (LSL, buffer, paths, etc.), JSON-serializable. |
| `events.jsonl` | Event log (one JSON object per line). |
| `stream.jsonl` | Recorded LSL stream chunks. |
| `replay_result.json` | Replay outcome: `match_count`, `mismatch_count`, `total_logged`, `total_replayed`, `matches`, `divergences`. |
| `benchmark_summary.json` | Latency report (e.g. e2e mean, intended→realized if present). |
| `session_summary.json` | High-level summary: `duration_sec`, `seed`, `out_dir`, `artifacts_ok`, `replay_ok`, `lsl_available`, `timestamp`. |
| `run_package_summary.json` | Run package summary: component versions, action/window counts, replay match status, benchmark readiness, warnings, config hash, backend. |
| `RUN_SUMMARY.md` | One-page markdown report of the run package summary (same data as above). |

When LSL discovery fails (exit 2), `out_dir` may still contain `config_snapshot.json` and a minimal `session_summary.json` with `lsl_available: false` and an `error` field.

**Methods-ready fields:** For reporting pipeline timing in methods, use `benchmark_summary.json`: `e2e_mean`, `e2e_stats` (mean, std, p50, p95), `intended_to_realized_mean`, `intended_to_realized_stats`, and per-stage `*_latency_stats` when benchmark hooks are enabled. Cite the pipeline version and `config_snapshot.json` for reproducibility.

No hardware or config file required. Another developer can clone the repo, `pip install -e .`, and run this to confirm Phase 1 works end-to-end. For a PsychoPy task that produces the full artifact set in one run, see **`examples/psychopy_e2e/`**.

## Adding plugins

You can add custom feature extractors, models, and policies without editing core code. Implement the protocol, register by name, and reference from config.

- **Feature extractors:** Implement `FeatureExtractor` (e.g. `extract(data, t_start, t_end, context)`). Call `register_feature_extractor("myname", MyExtractor, {"param": default})`. In config set `feature_extractor: "myname"` and optionally `feature_extractor_config: {...}`.
- **Models:** Implement `Model` and `register_model("myname", MyModel, default_config)`. Config: `model: "myname"`, `model_config: {...}`. See [model/base.py](src/looplab/model/base.py) and [model/example_models.py](src/looplab/model/example_models.py).
- **Policies:** Implement `Policy` and `register_policy("myname", MyPolicy, default_config)`. Config: `policy: "myname"`, `policy_config: {...}`.

Register at import time (e.g. in your package’s `__init__.py` or before `create_runner`). The runner uses `create_feature_extractor`, `create_model`, and `create_policy` to build the pipeline from config.

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

Use `PsychoPyTaskAdapter`: the controller pushes `ControlSignal` objects into a thread-safe queue. Your PsychoPy script (same process) should:

1. At each frame or trial boundary, call `adapter.pop_pending()` to get the latest control signal.
2. Apply the change (e.g. set condition, difficulty, stimulus).
3. After `win.flip()`, call `adapter.report_realized(signal, lsl_clock())` so the logger records the realized event.

The full **PsychoPy integration contract** (who creates the adapter, when to call `pop_pending`, meaning of `report_realized`, how to obtain `lsl_clock`) is in [docs/psychopy_integration.md](docs/psychopy_integration.md). See `examples/psychopy_simple_task/` for a minimal runnable pattern and `examples/closed_loop_demo/` for a config-based proof-run style reference.

## Synthetic vs live parity

Proof-run supports `--backend synthetic` (pure Python, no LSL) and `--backend lsl`. Both use the same `ControllerLoop` and produce the **same canonical artifact layout** (config_snapshot, events, stream, replay_result, benchmark_summary, session_summary) and the same report key structure. Developing and testing against synthetic is therefore valid for live runs; the only difference is the data source (in-process generator vs LSL discovery). Replay uses “one pipeline run per chunk”; synthetic proof-run ticks once per chunk to match.

## Deterministic replay

Record the stream during the run with `record_stream_path` in config. Replay loads the event log and recorded chunks, feeds chunks into the buffer in order, and re-runs the same pipeline (preprocess, features, model, policy). Compare replayed control signals to the logged ones to verify determinism (fixed seed, no wall-clock in the pipeline).

## Fault simulation (Workstream F)

LoopLab can simulate **missing chunks**, **noisy periods**, **drift**, **abrupt state changes**, **delayed or absent task acknowledgments**, and **invalid model outputs** for testing and documentation.

- **Stream stressors** ([looplab.replay.stressors](src/looplab/replay/stressors.py)): `drop_chunks`, `drop_chunks_by_index`, `drop_chunks_in_interval`, `add_noise`, `add_drift`, `add_abrupt_change` operate on chunk lists; use with replay to see divergence when data is missing or corrupted.
- **Event stressors**: `delay_realized_events`, `drop_realized_events`, `drop_realized_in_interval` modify event lists so benchmark report sees delayed or absent realized events.
- **Faulty model** ([looplab.model.stress_models](src/looplab/model/stress_models.py)): register as `"faulty"`; with configurable probability returns NaN/Inf so policy and pipeline behavior can be tested. Invalid model output is not sanitized; policies may need to handle NaN/Inf.

Example: `examples/stress_replay/run_stress_replay.py` runs replay with optional `--drop-ratio` and `--noise-scale`. Run tests with `pytest tests/test_replay_stressors.py`.

## License

MIT.
