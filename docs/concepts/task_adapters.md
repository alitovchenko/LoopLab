# Task adapters

**Role:** Connect the **policy** to **your task** without LoopLab owning the trial loop.

- **PsychoPy adapter:** Thread-safe queue. The task calls `pop_pending()` before updating stimuli and `win.flip()`, then `report_realized(signal, lsl_clock())` after flip so benchmarks can compute **intended → realized** latency.
- **Other adapters:** Same idea—something consumes `ControlSignal`s and acknowledges when the task has applied them.

LoopLab **does not** schedule trials or draw stimuli; your script does. See [PsychoPy integration](../psychopy_integration.md) and [Deployment: PsychoPy](../deployment/psychopy_task_integration.md).
