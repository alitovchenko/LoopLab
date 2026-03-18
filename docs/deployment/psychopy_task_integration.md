# PsychoPy task integration

**Deployment shape:** One process. **Controller loop** often runs on a **worker thread**; **PsychoPy** must run on the **main thread** (window/event loop). Share one **`PsychoPyTaskAdapter`** and **`lsl_clock()`**.

## Checklist

1. Runner creates the adapter when `task_adapter: psychopy` is set; pass it into your task code.
2. Each trial/frame: **`pop_pending()`** → apply signal to stimulus → **`win.flip()`** → **`report_realized(signal, lsl_clock())`**.
3. Optional: log **`trial_start`**, **`trial_outcome`**, **`adaptive_params_update`** via `EventLogger`.

## Reference paths

- **Full artifact + run report:** [Tutorial: PsychoPy e2e](../tutorials/psychopy_e2e.md), `examples/psychopy_e2e/`.
- **API details:** [psychopy_integration.md](../psychopy_integration.md).
- **Minimal code snippet:** `examples/psychopy_simple_task/`.

LoopLab does **not** own your trial schedule—only the adapter contract and logging hooks.
