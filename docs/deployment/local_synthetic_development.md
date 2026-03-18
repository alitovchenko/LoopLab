# Local synthetic development

**Goal:** Develop and validate configs, models, and policies **without** an LSL stream or lab hardware.

## Workflow

1. **`proof-run --backend synthetic`** — same controller loop as live; chunks from the in-process generator.
2. Optional **`--config`** with **`synthetic:`** block for stress/realism (dropouts, noise, delayed acks).
3. **`validate-config`** on every config change.
4. Inspect **`run_report.md`** and **`replay_result.json`** before touching real EEG.

## CI parity

CI runs synthetic proof-run in subprocess tests. Native LSL jobs may be optional/flaky—treat synthetic green as the regression signal for pipeline logic.

See [Quickstart](../quickstart.md), [Extensions: Synthetic scenario](../extensions/add_synthetic_scenario.md).
