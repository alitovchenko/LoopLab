"""
Minimal PsychoPy task that consumes LoopLab control signals.
Run this in the same process as the LoopLab controller, or adapt for subprocess/IPC.

Usage: typically started by your runner; adapter is shared with the controller loop.
"""

from __future__ import annotations


def run_task_loop(adapter, n_trials: int = 10, trial_duration: float = 0.5):
    """
    Simple loop: each trial, pop pending control signal, apply to stimulus, flip, report realized.
    adapter: PsychoPyTaskAdapter with set_logger() called.
    """
    try:
        from psychopy import visual, core
    except ImportError:
        raise ImportError("psychopy required: pip install psychopy") from None

    from looplab.streams.clock import lsl_clock

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


if __name__ == "__main__":
    # Standalone: create adapter without logger (no LoopLab run)
    from looplab.task.psychopy_adapter import PsychoPyTaskAdapter
    adapter = PsychoPyTaskAdapter()
    run_task_loop(adapter, n_trials=5)
