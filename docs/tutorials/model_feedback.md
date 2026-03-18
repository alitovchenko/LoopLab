# Tutorial: Model-based feedback

**Demo:** `examples/model_feedback_demo/`

The **model** maps features to a latent representation; the **policy** chooses **feedback type** (e.g. A vs B) for the task. Shows how to extend both sides of the loop for closed-loop neurofeedback-style paradigms.

## Steps

1. Read `examples/model_feedback_demo/README.md`.
2. Use **`validate-config`** with `--plugin` pointing at that demo’s `plugins.py`.
3. Run `run_demo.py`; open **`run_report.md`** and `events.jsonl` to connect model outputs to control signals.

## Concepts used

- [Models](../concepts/models.md), [Policies](../concepts/policies.md)
- [Reports](../concepts/reports.md)

```bash
python -m looplab validate-config --config examples/model_feedback_demo/config.yaml \
  --plugin examples/model_feedback_demo/plugins.py
```
