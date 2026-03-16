# LoopLab

**EEG-first, Python-native closed-loop experiment SDK** with LSL, PsychoPy, and deterministic replay.

LoopLab is a research-grade orchestration framework that sits between streaming tools (LSL), online preprocessing, user-defined models, and adaptive task control. It is not a full BCI suite or a replacement for stimulus software—it coordinates the closed loop: ingest streams, process data, run a model, emit control signals, adapt the task, and log everything for replay and benchmarking.

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
  __main__.py    # CLI: run, replay, benchmark
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
