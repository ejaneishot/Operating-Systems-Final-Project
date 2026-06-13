"""Data models for the CPU scheduling simulator.

Two clean halves:

* :class:`Process`        - immutable *input* (what the user typed in).
* :class:`ProcessResult`  - the *output* timings the scheduler computed.

Keeping input and output separate is what lets the algorithms run without
ever copying or mutating the caller's data: the same workload can be fed to
every algorithm back to back with zero defensive copying.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, List


@dataclass(frozen=True, slots=True)
class Process:
    """An immutable process specification.

    ``frozen`` makes it read-only (so no algorithm can corrupt it) and
    ``slots`` removes the per-instance ``__dict__`` for lower memory and
    faster attribute access -- both matter when simulating large workloads.

    Priority convention: a *lower* number means a *higher* priority.
    """

    pid: str
    arrival: int
    burst: int
    priority: int = 0

    def __post_init__(self) -> None:
        if self.arrival < 0:
            raise ValueError(f"{self.pid}: arrival time cannot be negative")
        if self.burst <= 0:
            raise ValueError(f"{self.pid}: burst time must be positive")


@dataclass(slots=True)
class ProcessResult:
    """Computed timings for one process after scheduling."""

    pid: str
    arrival: int
    burst: int
    priority: int
    start: int        # first time the process got the CPU
    completion: int   # time the process finished

    @property
    def turnaround_time(self) -> int:
        return self.completion - self.arrival

    @property
    def waiting_time(self) -> int:
        return self.turnaround_time - self.burst

    @property
    def response_time(self) -> int:
        return self.start - self.arrival


@dataclass(slots=True)
class GanttSegment:
    """A contiguous block on the CPU timeline (a process id, or ``"idle"``)."""

    label: str
    start: int
    end: int

    IDLE: ClassVar[str] = "idle"

    @property
    def duration(self) -> int:
        return self.end - self.start

    @property
    def is_idle(self) -> bool:
        return self.label == self.IDLE


@dataclass(slots=True)
class ScheduleResult:
    """Everything produced by running one algorithm on one workload."""

    algorithm: str
    processes: List[ProcessResult]
    gantt: List[GanttSegment]

    @property
    def avg_waiting_time(self) -> float:
        return _mean(p.waiting_time for p in self.processes)

    @property
    def avg_turnaround_time(self) -> float:
        return _mean(p.turnaround_time for p in self.processes)

    @property
    def avg_response_time(self) -> float:
        return _mean(p.response_time for p in self.processes)

    @property
    def execution_order(self) -> List[str]:
        """Order in which processes first started running (ignoring idle)."""
        seen: List[str] = []
        for seg in self.gantt:
            if not seg.is_idle and seg.label not in seen:
                seen.append(seg.label)
        return seen


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0
