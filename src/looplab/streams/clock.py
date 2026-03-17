"""LSL clock as canonical time base for events and replay.

Supports an optional override (e.g. synthetic clock) so proof-run can avoid
importing pylsl when running with --backend synthetic.
"""

from __future__ import annotations

from typing import Callable

_clock_fn: Callable[[], float] | None = None


def set_clock(fn: Callable[[], float] | None) -> None:
    """Set an alternative clock (e.g. for synthetic proof-run). Pass None to reset to default."""
    global _clock_fn
    _clock_fn = fn


def lsl_clock() -> float:
    """Return current time in LSL local clock (seconds). Use for all event timestamps."""
    if _clock_fn is not None:
        return _clock_fn()
    import pylsl
    return pylsl.local_clock()
