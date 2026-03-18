# PsychoPy integration contract

**Runnable reference:** The end-to-end adaptive path (loop → task parameter → `report_realized` → full artifacts) lives in **`examples/psychopy_e2e`** — see that README’s *Canonical adaptive PsychoPy path* section.

This document defines how a PsychoPy task integrates with LoopLab’s controller loop and logging.

## 1. Who creates the adapter and where it lives

- **Creator:** The LoopLab runner creates the `PsychoPyTaskAdapter` when you use `task_adapter: psychopy` in config. The same adapter is passed to the `ControllerLoop` and must be shared with your PsychoPy script.
- **Process/thread:** Typically the controller loop and the PsychoPy window run in the **same process**. The loop can run in a background thread while the PsychoPy main loop runs on the main thread (or the other way around). The adapter is thread-safe (queue protected by a lock). For a different process you would need your own IPC and an adapter-like proxy; that is not covered here.

## 2. When to call `pop_pending` and with what timing

- **When:** Call `adapter.pop_pending()` at each **frame** or at each **trial boundary**, before you update the stimulus and call `win.flip()`. That way the stimulus on the next frame reflects the latest control signal.
- **Meaning:** `pop_pending()` removes and returns the oldest pending control signal, or `None` if the queue is empty. Use the returned signal to set condition, difficulty, or stimulus parameters (e.g. from `signal.action` and `signal.params`).
- **Timing:** Poll once per frame or once per trial. If you poll less often, you may miss or delay applying signals; if you poll more often, you only get a signal when the controller has pushed one.

## 3. Meaning of `report_realized(signal, lsl_time)`

- **When:** Call this **after** `win.flip()` for the frame/trial where you applied the given `signal`. Pass the **LSL clock time** at the moment the stimulus was actually shown (e.g. right after `win.flip()`).
- **Meaning:** LoopLab records a “stimulus realized” event so that intended→realized latency can be computed. The logger must be set on the adapter (`adapter.set_logger(logger)`), which the runner does when benchmark/logging is enabled.
- **Arguments:** `signal` is the same `ControlSignal` you got from `pop_pending()` and applied; `lsl_time` is the canonical time (seconds) when the stimulus was realized (e.g. from `lsl_clock()`).

## 4. How to obtain `lsl_clock` in the PsychoPy process

- **Same process:** Use `from looplab.streams.clock import lsl_clock` and call `lsl_clock()` after `win.flip()`. That returns the same clock the controller uses (LSL local time, or the synthetic override in proof-run).
- **Different process:** If the task runs in another process, you need a shared time base (e.g. NTP-synced or LSL clock in both). LoopLab does not provide IPC or cross-process clock; you would pass timestamps via your own IPC.

## Minimal copy-paste snippet (same process)

```python
from psychopy import visual, core
from looplab.streams.clock import lsl_clock
# adapter: PsychoPyTaskAdapter, created by runner and passed into your task

win = visual.Window(size=(400, 300), allowGUI=True)
stim = visual.Circle(win, radius=0.2, fillColor="white")

for trial in range(n_trials):
    signal = adapter.pop_pending()
    if signal is not None and signal.action == "set_value":
        value = signal.params.get("value", 0.5)
        stim.radius = 0.1 + 0.2 * float(value)
    stim.draw()
    win.flip()
    if signal is not None:
        adapter.report_realized(signal, lsl_clock())
    core.wait(trial_duration)

win.close()
```

See `examples/psychopy_simple_task/` for a runnable minimal task.

## Full end-to-end example

**`examples/psychopy_e2e/`** is a single runnable example that combines a real PsychoPy window with the LoopLab pipeline in the same process and produces the **full LoopLab artifact set** (events.jsonl, stream.jsonl, replay_result, benchmark_summary, session_summary, run_package_summary, RUN_SUMMARY.md). Run it with:

```bash
cd examples/psychopy_e2e && python run_demo.py --out-dir demo_out --duration 4
```

See `examples/psychopy_e2e/README.md` for prerequisites, artifact list, and contract summary.
