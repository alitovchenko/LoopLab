"""
PsychoPy task that receives LoopLab control signals, changes a task parameter, and reports realized timing.

Run from run_demo.py with the shared adapter and clock. Each trial: pop_pending -> set stimulus from
signal.params -> draw -> flip -> report_realized(signal, lsl_clock()).
"""

from __future__ import annotations

from looplab.task.psychopy_adapter import PsychoPyTaskAdapter


def run_psychopy_task(
    adapter: PsychoPyTaskAdapter,
    duration_sec: float,
    trial_duration: float = 0.25,
) -> None:
    """
    Run a PsychoPy trial loop for the given duration. Each trial: get pending control signal,
    apply to stimulus (circle radius from params["value"]), flip, report realized with lsl_clock().
    """
    try:
        from psychopy import visual, core
    except ImportError as e:
        raise ImportError(
            "PsychoPy is required for this example. Install with: pip install -e \".[psychopy]\""
        ) from e

    from looplab.streams.clock import lsl_clock

    win = visual.Window(size=(400, 300), allowGUI=True)
    stim = visual.Circle(win, radius=0.2, fillColor="white")

    timer = core.Clock()
    while timer.getTime() < duration_sec:
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
