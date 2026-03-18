# Tutorial: Adaptive difficulty (vigilance-style task)

**Demo:** `examples/adaptive_difficulty_demo/`

Models a **vigilance / sustained-attention** style loop: the pipeline observes the stream and the **policy** adjusts **task difficulty** (easy / medium / hard). The task logs trials, blocks, outcomes, and adaptive parameters so run reports show experiment-level structure.

## Steps

1. Install: `pip install -e ".[dev,yaml]"` (and PsychoPy extra if the task opens a window).
2. Read `examples/adaptive_difficulty_demo/README.md` for exact commands.
3. Typical flow: register plugins from `plugins.py`, load config, run `run_demo.py` with `--out-dir`.
4. Inspect **`run_report.md`** in the output directory: pipeline names, timing, adaptation counts, trial/block summaries.

## Concepts used

- [Policies](../concepts/policies.md) — difficulty decisions
- [Experiment state](../concepts/experiment_state.md) — trial/outcome logging
- [Reports](../concepts/reports.md)

**Validate config before running:**

```bash
python -m looplab validate-config --config examples/adaptive_difficulty_demo/config.yaml \
  --plugin examples/adaptive_difficulty_demo/plugins.py
```
