"""LSL clock as canonical time base for events and replay."""

import pylsl


def lsl_clock() -> float:
    """Return current time in LSL local clock (seconds). Use for all event timestamps."""
    return pylsl.local_clock()
