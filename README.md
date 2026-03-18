# LoopLab

**EEG-first, Python-native closed-loop experiment SDK** with LSL, PsychoPy, and deterministic replay.

LoopLab is a research-grade orchestration framework that sits between streaming tools (LSL), online preprocessing, user-defined models, and adaptive task control. It is the coordinator of the closed loop, allowing you to ingest streams, process data, run a model, emit control signals, adapt the task, and log everything for replay and benchmarking.

## Documentation (guided path)

**New users:** start at **[docs/index.md](docs/index.md)** → [Quickstart](docs/quickstart.md) (install → validate config → synthetic proof-run → run report), then [Concepts](docs/concepts/index.md), [Tutorials](docs/tutorials/index.md), [Extensions](docs/extensions/index.md), [Deployment](docs/deployment/index.md).

**Run artifacts:** JSON contracts and stable vs experimental fields are documented in **[docs/artifact_schemas.md](docs/artifact_schemas.md)** (`schemas/*.schema.json` for validation).

## Features

- **LSL-based stream ingestion** with configurable stream selection and chunk size
- **Ring buffer** with LSL-time–aligned samples
- **Online-safe preprocessing** (optional detrend/zscore) and simple rolling feature extraction
- **Model and policy API**: plug-in Python models, control signals with validity window
- **Controller loop**: buffer → preprocess → features → model → policy → task adapter
- **Task adapter** for PsychoPy (queue of control signals; task polls at frame/trial boundaries)
- **Event logging**: intended vs realized stimulus events, all timestamps in LSL time
- **Stream recorder** and **deterministic replay** from log + recorded stream
- **Timing benchmarks**: hooks and simple latency report (e2e, intended→realized)

## Recent workstreams

These tracks landed together to support **technical communication**, **real-task PsychoPy integration**, and **developer ergonomics**:

| Workstream | What it adds | Where to look |
|------------|--------------|---------------|
| **Methods-ready run reporting** | Every proof-run (and `report --run-dir … --write`) can emit **`run_report.json`** / **`run_report.md`**: citable pipeline fields, timing stats, adaptation & experiment event counts, replay agreement, diagnostics summary, **artifact inventory**. **`components_manifest.json`** records resolved feature/model/policy (defaults + effective config, class names, LoopLab version). | [Proof run](#proof-run-canonical-verification) artifact table; `python -m looplab report --run-dir <dir> [--human] [--write]` |
| **PsychoPy canonical adaptive path** | One runnable demo wires adaptation → task parameter (e.g. stimulus size) → **`report_realized`** → trial/block/outcome logging. Runs tag **`paradigm: psychopy_e2e`**; **run reports** include a **Task-level summary (PsychoPy bridge)** (trials, intended/realized counts, IT→R mean). Same **`components_manifest.json`** parity as proof-run. | **`examples/psychopy_e2e/`** (README: *Canonical adaptive PsychoPy path*); [docs/psychopy_integration.md](docs/psychopy_integration.md) |
| **Plugin introspection** | **`list-components`** (class, full default config, docstring line, optional `component_version`), **`validate-config`** with **`--plugin`** for custom demos, richer **UnknownComponentError** hints. | [Developer tooling](#developer-tooling) |
| **Synthetic scenarios** | Proof-run with YAML **`synthetic`** section: drift, dropouts, ack delay, irregular timing, etc., for stress/realism without hardware. | [Synthetic scenarios](#synthetic-scenarios-configurable-stress-and-realism); `examples/synthetic_scenario/` |
| **Benchmark protocol** | What E2E, per-stage, and intended→realized mean; synthetic vs task-level vs LSL; versioned reference stats. | [docs/benchmarking.md](docs/benchmarking.md); `examples/benchmark_reference_runs/` |
| **Artifact schemas** | Stable vs experimental fields for `session_summary`, `benchmark_summary`, `diagnostics`, `replay_result`, `components_manifest`, `run_report`; optional JSON Schema in `schemas/`. | [docs/artifact_schemas.md](docs/artifact_schemas.md) |

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

**LSL (same mapping everywhere: matrix, artifacts, `check-lsl`):** **Supported** = synthetic core path → `lsl_support_tier`: **`synthetic_supported`**. **Best effort** = native LSL runtime → **`native_lsl_functional`** \| **`native_lsl_unavailable`**. **Monitoring-only** = `test-lsl` CI lane. Details and examples: [docs/deployment/lsl_compatibility_matrix.md](docs/deployment/lsl_compatibility_matrix.md).

```bash
python -m looplab check-lsl          # human: policy lines + probe result + lsl_support_tier
python -m looplab check-lsl --json   # + environment (OS, Python, pylsl, liblsl); exit 0 ≠ full live cert
```

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

## Proof run (canonical verification)

A **proof run** verifies the pipeline end-to-end: one command, no EEG hardware, synthetic stream, full record → replay → divergence report → benchmark. Use it to verify the installation and that all completion criteria are met.

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
| `components_manifest.json` | Resolved pipeline: LoopLab version, feature/model/policy class names, default vs effective config, optional per-component `component_version`. |
| `diagnostics.json` | Run-quality checks: `health` (`healthy` / `degraded` / `unhealthy`), `findings` (info/warning/critical), `checks`, thresholds used. |
| `session_summary.json` | High-level summary plus `run_health`, `diagnostic_findings`, `warning_messages` (merged legacy + diagnostic warnings). |
| `run_package_summary.json` | Run package summary: includes optional `diagnostics` block, component versions, replay, benchmark readiness, `warning_inventory`. |
| `RUN_SUMMARY.md` | One-page markdown report including **Run diagnostics** (health and findings). Points to **run_report.md** for methods detail. |
| `run_report.json` | Methods-ready aggregate: citable **methods** block (window size, model/policy/feature names, adaptation target, timing stats, warning status), pipeline (from manifest or config), experiment/adaptation counts, optional **task_level_summary** (e.g. PsychoPy bridge when `paradigm: psychopy_e2e`), replay, benchmark highlights, diagnostics, artifact inventory. |
| `run_report.md` | Human-readable version of the same, including **Task-level summary (PsychoPy bridge)** when present. |

When LSL discovery fails (exit 2), `out_dir` may still contain `config_snapshot.json` and a minimal `session_summary.json` with `lsl_available: false` and an `error` field.

**Methods-ready fields:** Use **`run_report.json`** / **`run_report.md`** for a single place to cite window size, buffer, feature extractor / model / policy names, adaptation target, backend, duration, effective windows/s, timing summaries, replay agreement, diagnostics health, and trial/block counts (when experiment events are logged). PsychoPy e2e runs also surface **task-level** trial/outcome counts and stimulus intended/realized stats in the same report. Raw detail remains in `benchmark_summary.json` (`e2e_stats`, `intended_to_realized_stats`, per-stage latencies). Cite LoopLab version from `components_manifest.json` or `run_report.methods.looplab_version` and `config_snapshot.json` for full reproducibility.

No hardware or config file required. Another developer can clone the repo, `pip install -e .`, and run this to confirm the pipeline works end-to-end. For a PsychoPy task that produces the full artifact set in one run, see **`examples/psychopy_e2e/`**. For differentiated adaptive paradigms (difficulty control, model-based feedback), see **`examples/adaptive_difficulty_demo/`** and **`examples/model_feedback_demo/`**.

## Examples

| Example | Description |
|--------|-------------|
| `examples/closed_loop_demo/` | Minimal config-driven loop (identity model/policy); run via `proof-run` or `run --config`. |
| `examples/adaptive_difficulty_demo/` | Pipeline drives task difficulty (easy/medium/hard); custom policy, full artifacts. |
| `examples/model_feedback_demo/` | Model output drives feedback type (A/B); custom model and policy, full artifacts. |
| `examples/psychopy_e2e/` | **Canonical adaptive PsychoPy path:** real task, full artifacts + `components_manifest.json`, `paradigm: psychopy_e2e`, task-level run-report section. |
| `examples/psychopy_simple_task/` | Minimal PsychoPy pattern: pop_pending, apply, report_realized. |
| `examples/stress_replay/` | Replay with stream stressors (drop chunks, noise) for fault simulation. |
| `examples/synthetic_scenario/` | Proof-run with configurable synthetic scenario (drift, dropouts, ack delay, etc.). |
| `examples/plugin_templates/` | Stub files for custom feature extractors, models, and policies. |

## Developer tooling

| Command | Purpose |
|--------|---------|
| `python -m looplab list-components` | Full catalog: implementing class, `default_config`, optional `component_version`, one-line description. Use `--json` for machines. |
| `python -m looplab list` | Short list of names and default config keys (backward compatible). |
| `python -m looplab validate-config --config path/to/config.yaml` | Check that `feature_extractor`, `model`, and `policy` are registered and that `*_config` can instantiate each component. |
| `python -m looplab validate-config --config ... --plugin path/to/plugins.py` | Load a plugin module first (same as demos that `import plugins` before `create_runner`). Repeat `--plugin` for multiple files. |
| `validate-config … --strict` / `--json` | Optional: fail on preprocess/task_adapter warnings (`--strict`); structured exit payload (`--json`). |
| `python -m looplab new feature\|model\|policy <name>` | Write a starter `.py` next to [examples/plugin_templates/](examples/plugin_templates/). |

Unknown component errors suggest **`list-components`** and **`validate-config`**. After **`proof-run`**, see **`components_manifest.json`** for exactly what was wired.

## Adding plugins

You can add custom feature extractors, models, and policies without editing core code. Implement the protocol, register by name, and reference from config. Run **`looplab list-components`** (or **`looplab list`**) to see registered plugins. Optional: `register_*(..., component_version="1.0.0")` for manifests and introspection.

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
  model/         # Model protocol, registry, example + stress (faulty) models
  controller/    # ControlSignal, Policy, ControllerLoop
  task/          # TaskAdapter, PsychoPyTaskAdapter
  logging/       # Event schema, JSONL writer, EventLogger
  benchmark/     # Hooks, latency report, run summary
  replay/        # StreamRecorder, ReplayEngine, ReplayRunner, stressors
  config/        # RunConfig, load_config
  runner.py      # create_runner
  introspection.py  # list-components catalog
  __main__.py    # CLI: run, replay, proof-run, list-components, validate-config, …
```

## PsychoPy integration

Use `PsychoPyTaskAdapter`: the controller pushes `ControlSignal` objects into a thread-safe queue. Your PsychoPy script (same process) should:

1. At each frame or trial boundary, call `adapter.pop_pending()` to get the latest control signal.
2. Apply the change (e.g. set condition, difficulty, stimulus).
3. After `win.flip()`, call `adapter.report_realized(signal, lsl_clock())` so the logger records the realized event.

The full **PsychoPy integration contract** (who creates the adapter, when to call `pop_pending`, meaning of `report_realized`, how to obtain `lsl_clock`) is in [docs/psychopy_integration.md](docs/psychopy_integration.md). The **end-to-end adaptive reference** is **`examples/psychopy_e2e/`** (numbered plug-in flow, full artifacts, methods-ready report with task-level summary). See `examples/psychopy_simple_task/` for a minimal code-only pattern and `examples/closed_loop_demo/` for config-based proof-run style reference.

## Synthetic vs live parity

Proof-run supports `--backend synthetic` (pure Python, no LSL) and `--backend lsl`. Both use the same `ControllerLoop` and produce the **same canonical artifact layout** (including **`components_manifest.json`**, **`run_report.json`** / **`run_report.md`**, diagnostics, package summary) when the run completes successfully. Developing and testing against synthetic is therefore valid for live runs; the only difference is the data source (in-process generator vs LSL discovery). Replay uses “one pipeline run per chunk”; synthetic proof-run ticks once per chunk to match.

## Synthetic scenarios (configurable stress and realism)

When running with `--backend synthetic`, you can pass a config file that includes a **`synthetic`** section to control signal type and degradation schedules (scenarios: `stationary_clean`, `drifting_attention`, `regime_shift`; schedules: dropouts, noise_bursts, ack_delay_ms, event_omission, policy_noop, low_confidence, irregular_timing, invalid_windows). Example: `python -m looplab proof-run --config examples/synthetic_scenario/config.yaml --out-dir scenario_out --duration 4`. See [examples/synthetic_scenario/](examples/synthetic_scenario/) and `pytest tests/test_synthetic_scenarios.py`.

## Experiment abstraction

LoopLab provides **experiment-level types** so adaptation can be described and logged in trial/block terms, not only as raw control signals. This supports methods-ready reporting (e.g. "trial 5, block 0, difficulty=2, outcome=correct").

- **TrialContext** – Identifies the current trial (trial_index, block_index, condition, onset_lsl_time). Use when logging trial start.
- **BlockContext** – Identifies the current block (block_index, label, start_lsl_time). Use when logging block start.
- **ExperimentState** – Holds current_trial, current_block, and **AdaptiveParameterState** (a mutable dict of named adaptive parameters, e.g. difficulty, feedback_type). Methods: `start_block`, `start_trial`, `record_outcome`.
- **TrialOutcome** – Result of a trial (trial_index, block_index, correct, rt_sec, condition, extra). The task reports this at trial end.
- **Task-level event stream** – The same event log (events.jsonl) can include event types: `trial_start`, `trial_end`, `block_start`, `block_end`, `trial_outcome`, `adaptive_params_update`. EventLogger has `log_trial_start`, `log_block_start`, `log_trial_outcome`, `log_adaptive_params_update` (and optional trial_end/block_end).

The **task** (e.g. PsychoPy script) owns the trial loop; it can create an `ExperimentState`, update it when applying control signals (e.g. set difficulty or stimulus_size in adaptive_params), and call the logger to write these events. The runner does not create ExperimentState by default; demos that want experiment-level logging create it and pass it to the task. See `examples/adaptive_difficulty_demo/` and `examples/psychopy_e2e/` for demos that log adaptation in experiment terms.

## Deterministic replay

Record the stream during the run with `record_stream_path` in config. Replay loads the event log and recorded chunks, feeds chunks into the buffer in order, and re-runs the same pipeline (preprocess, features, model, policy). Compare replayed control signals to the logged ones to verify determinism (fixed seed, no wall-clock in the pipeline).

## Fault simulation

LoopLab can simulate **missing chunks**, **noisy periods**, **drift**, **abrupt state changes**, **delayed or absent task acknowledgments**, and **invalid model outputs** for testing and documentation.

- **Stream stressors** ([looplab.replay.stressors](src/looplab/replay/stressors.py)): `drop_chunks`, `drop_chunks_by_index`, `drop_chunks_in_interval`, `add_noise`, `add_drift`, `add_abrupt_change` operate on chunk lists; use with replay to see divergence when data is missing or corrupted.
- **Event stressors**: `delay_realized_events`, `drop_realized_events`, `drop_realized_in_interval` modify event lists so benchmark report sees delayed or absent realized events.
- **Faulty model** ([looplab.model.stress_models](src/looplab/model/stress_models.py)): register as `"faulty"`; with configurable probability returns NaN/Inf so policy and pipeline behavior can be tested. Invalid model output is not sanitized; policies may need to handle NaN/Inf.

Example: `examples/stress_replay/run_stress_replay.py` runs replay with optional `--drop-ratio` and `--noise-scale`. Run tests with `pytest tests/test_replay_stressors.py`.

## License

MIT.
