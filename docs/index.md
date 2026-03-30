# LoopLab documentation

Guided path from install to a meaningful **run report**—no private hand-holding required.

| Layer | Purpose |
|-------|---------|
| **[Quickstart](quickstart.md)** | Install → validate config → synthetic proof-run → read run report |
| **[Concepts](concepts/index.md)** | How streams, features, models, policies, adapters, experiment state, diagnostics, replay, and reports fit together |
| **[Tutorials](tutorials/index.md)** | Runnable demos: adaptive difficulty, model feedback, PsychoPy e2e |
| **[Extensions](extensions/index.md)** | Add a model, feature extractor, policy, or synthetic scenario |
| **[Deployment](deployment/index.md)** | Local synthetic workflow, PsychoPy integration, **[LSL matrix](deployment/lsl_compatibility_matrix.md)** (`check-lsl`) |

**Also:** [PsychoPy integration contract](psychopy_integration.md) (API-level reference). **[Benchmarking protocol](benchmarking.md)** (latency definitions, synthetic vs PsychoPy vs LSL, reference bundles). **[Artifact schemas](artifact_schemas.md)** (JSON contracts for run outputs; [JSON Schema files](../schemas/)). **[Export formats](export_formats.md)** (BIDS + MNE FIF from a run directory; `export-bids` CLI, requires `[mne]`).

---

**Suggested first path:** [quickstart.md](quickstart.md) → [concepts/index.md](concepts/index.md) → one [tutorial](tutorials/index.md) → [reports concept](concepts/reports.md).
