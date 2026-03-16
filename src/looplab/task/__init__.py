"""Task adapters for stimulus control (e.g. PsychoPy)."""

from looplab.task.adapter import TaskAdapter
from looplab.task.psychopy_adapter import PsychoPyTaskAdapter

__all__ = [
    "TaskAdapter",
    "PsychoPyTaskAdapter",
]
