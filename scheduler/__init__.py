"""CPU Scheduling Simulator package.

Public API re-exported for convenience::

    from scheduler import fcfs, sjf, srtf, round_robin, priority_scheduling
    from scheduler import Process, ScheduleResult
"""

from .algorithms import (
    ALGORITHMS,
    fcfs,
    priority_scheduling,
    round_robin,
    sjf,
    srtf,
)
from .models import GanttSegment, Process, ProcessResult, ScheduleResult

__all__ = [
    "Process",
    "ProcessResult",
    "GanttSegment",
    "ScheduleResult",
    "fcfs",
    "sjf",
    "srtf",
    "priority_scheduling",
    "round_robin",
    "ALGORITHMS",
]
