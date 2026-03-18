# Core concepts

The controller pipeline is linear; time and causality flow **left to right**:

```text
LSL / synthetic chunks → ring buffer → preprocess → features → model → policy → task adapter → task
                              ↑                                                          ↓
                         event log ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
```

| Topic | What it is |
|-------|------------|
| [Streams](streams.md) | Where chunks of multichannel samples enter; LSL vs synthetic; chunk size and timing |
| [Features](features.md) | Rolling summaries from buffer windows (e.g. band power, simple stats) |
| [Models](models.md) | Map features → model output (e.g. latent state, confidence) |
| [Policies](policies.md) | Map model output → `ControlSignal` (action + params + validity window) |
| [Task adapters](task_adapters.md) | Bridge from policy to the task (e.g. PsychoPy queue); intended vs realized events |
| [Experiment state](experiment_state.md) | Optional trial/block/adaptive-param logging alongside raw signals |
| [Diagnostics](diagnostics.md) | Run health checks over logs and benchmarks |
| [Replay](replay.md) | Re-feed recorded stream + re-run pipeline; compare to logged control signals |
| [Reports](reports.md) | `run_report`, `benchmark_summary`, manifests—what to cite in methods |

Read in order above, or jump to what you need.
