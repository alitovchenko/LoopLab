# Minimal PsychoPy task with LoopLab adapter

This folder shows how to drive a PsychoPy task from LoopLab control signals.

## Pattern

1. **Same process**: Create a `PsychoPyTaskAdapter` and pass it to the LoopLab runner. Run the controller loop in one thread and the PsychoPy window in the main (or another) thread.

2. **Polling**: In your PsychoPy trial loop, before each stimulus update or flip:
   - `signal = adapter.pop_pending()` to get the latest control signal (if any).
   - If `signal` is not None, apply it (e.g. set condition from `signal.params["value"]`).
   - After `win.flip()`, call `adapter.report_realized(signal, looplab.streams.clock.lsl_clock())`.

3. **Contract**: Control signals use `action` (e.g. `"set_value"`) and `params` (e.g. `{"value": 0.5}`). Your task interprets these (e.g. difficulty level, condition index).

## Example snippet (pseudocode)

```python
from psychopy import visual, core
from looplab.streams.clock import lsl_clock
# Assume adapter is created by runner and injected into your task
# adapter = PsychoPyTaskAdapter(logger=...)

win = visual.Window()
stim = visual.Circle(win, radius=0.2)

for trial in range(n_trials):
    signal = adapter.pop_pending()
    if signal is not None and signal.action == "set_value":
        value = signal.params.get("value", 0.5)
        # e.g. set stimulus size or condition
        stim.radius = 0.1 + 0.2 * value
    stim.draw()
    win.flip()
    if signal is not None:
        adapter.report_realized(signal, lsl_clock())
    core.wait(0.5)
```

## Running with LoopLab

Configure `task_adapter: psychopy` and point the runner at your task script if you use a subprocess; or run the loop and the PsychoPy main loop in the same process (e.g. loop in a thread, PsychoPy on main thread).
