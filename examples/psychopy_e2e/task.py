"""
PsychoPy task that receives LoopLab control signals, changes a task parameter, and reports realized timing.

Run from run_demo.py with the shared adapter and clock. Each trial: pop_pending -> set stimulus from
signal.params -> draw -> flip -> report_realized(signal, lsl_clock()). Optional experiment_state and
logger enable task-level event logging (block_start, trial_start, trial_outcome, adaptive_params_update).
"""

from __future__ import annotations

from typing import Any

from looplab.task.psychopy_adapter import PsychoPyTaskAdapter


def run_psychopy_task(
    adapter: PsychoPyTaskAdapter,
    duration_sec: float,
    trial_duration: float = 0.25,
    experiment_state: Any = None,
    logger: Any = None,
) -> None:
    """
    Run a PsychoPy trial loop for the given duration. Each trial: get pending control signal,
    apply to stimulus (circle radius from params["value"]), flip, report realized with lsl_clock().
    If experiment_state and logger are provided, log block_start, trial_start, trial_outcome,
    and adaptive_params_update so the event log includes experiment-level events.
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

    use_experiment = experiment_state is not None and logger is not None
    if use_experiment:
        block = experiment_state.start_block(0, label="psychopy_e2e", lsl_time=lsl_clock())
        logger.log_block_start(lsl_clock(), block)

    timer = core.Clock()
    trial_index = 0
    while timer.getTime() < duration_sec:
        trial_start_time = lsl_clock()
        if use_experiment:
            experiment_state.start_trial(trial_index, 0, condition=None, lsl_time=trial_start_time)
            logger.log_trial_start(trial_start_time, experiment_state.current_trial)

        signal = adapter.pop_pending()
        if signal is not None and signal.action == "set_value":
            value = signal.params.get("value", 0.5)
            stim.radius = 0.1 + 0.2 * float(value)
            if use_experiment:
                experiment_state.adaptive_params.set("stimulus_size", value)
                logger.log_adaptive_params_update(lsl_clock(), experiment_state.adaptive_params.to_dict())
        stim.draw()
        win.flip()
        if signal is not None:
            adapter.report_realized(signal, lsl_clock())
        core.wait(trial_duration)

        if use_experiment:
            from looplab.experiment import TrialOutcome
            outcome = TrialOutcome(
                trial_index=trial_index,
                block_index=0,
                correct=None,
                rt_sec=trial_duration,
                condition=None,
                extra={"stimulus_size": experiment_state.adaptive_params.get("stimulus_size")},
            )
            logger.log_trial_outcome(lsl_clock(), outcome)
            experiment_state.record_outcome(outcome)
        trial_index += 1

    win.close()
