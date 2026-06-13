"""The scheduling algorithms -- optimised for speed, clean to read.

Design choices that make this both fast and easy to follow:

* **Inputs are never copied or mutated.** Each algorithm works on flat
  integer arrays (``remaining``, ``start``, ``completion``) indexed by the
  process's original position. The same workload can be fed to every
  algorithm with zero copying.

* **The right data structure per algorithm:**
    - FCFS         -> sort by arrival + one linear sweep   (O(n log n))
    - SJF/Priority -> binary min-heap on the chosen key     (O(n log n))
    - SRTF         -> event-driven min-heap on remaining     (O(n log n))
    - Round Robin  -> deque, O(1) at both ends               (O(total slices))

  The naive "scan every ready process each step" approach is O(n^2); the
  heap replaces that scan with an O(log n) pop.

Every algorithm returns a :class:`ScheduleResult` carrying per-process
:class:`ProcessResult` timings and the Gantt timeline.
"""

from __future__ import annotations

import heapq
from collections import deque
from typing import Callable, List

from .models import GanttSegment, Process, ProcessResult, ScheduleResult

_INF = float("inf")


# --------------------------------------------------------------------------- #
# Gantt + result helpers
# --------------------------------------------------------------------------- #
def _emit(gantt: List[GanttSegment], label: str, start: int, end: int) -> None:
    """Append a segment, merging with the previous one if they're contiguous."""
    if end <= start:
        return
    if gantt and gantt[-1].label == label and gantt[-1].end == start:
        gantt[-1].end = end
    else:
        gantt.append(GanttSegment(label, start, end))


def _build(name: str, processes: List[Process],
           start: List[int], completion: List[int],
           gantt: List[GanttSegment]) -> ScheduleResult:
    results = [
        ProcessResult(p.pid, p.arrival, p.burst, p.priority, start[i], completion[i])
        for i, p in enumerate(processes)
    ]
    return ScheduleResult(name, results, gantt)


def _arrival_order(processes: List[Process]) -> List[int]:
    """Indices of the processes sorted by (arrival, pid)."""
    return sorted(range(len(processes)),
                  key=lambda i: (processes[i].arrival, processes[i].pid))


# --------------------------------------------------------------------------- #
# FCFS -- sort + sweep, optimal for this one.
# --------------------------------------------------------------------------- #
def fcfs(processes: List[Process]) -> ScheduleResult:
    """First Come First Serve."""
    n = len(processes)
    start = [0] * n
    completion = [0] * n
    gantt: List[GanttSegment] = []
    time = 0

    for i in _arrival_order(processes):
        p = processes[i]
        if time < p.arrival:                      # CPU idle until this arrives
            _emit(gantt, GanttSegment.IDLE, time, p.arrival)
            time = p.arrival
        start[i] = time
        time += p.burst
        completion[i] = time
        _emit(gantt, p.pid, start[i], time)

    return _build("FCFS", processes, start, completion, gantt)


# --------------------------------------------------------------------------- #
# Non-preemptive heap family: SJF, Priority.
# --------------------------------------------------------------------------- #
def _non_preemptive_heap(processes: List[Process], name: str,
                         key: Callable[[Process], int]) -> ScheduleResult:
    """Pick the best ready process with a min-heap, run it to completion.

    ``key`` decides what "best" means (shortest burst, highest priority...).
    The heap entry ``(key, pid, index)`` makes ties break deterministically
    by process id.
    """
    n = len(processes)
    order = _arrival_order(processes)
    start = [0] * n
    completion = [0] * n
    gantt: List[GanttSegment] = []

    heap: List[tuple] = []
    time = 0
    nxt = 0          # next not-yet-released process in arrival order
    done = 0

    while done < n:
        # Release everything that has arrived by `time` into the ready heap.
        while nxt < n and processes[order[nxt]].arrival <= time:
            idx = order[nxt]
            p = processes[idx]
            heapq.heappush(heap, (key(p), p.arrival, p.pid, idx))
            nxt += 1

        if not heap:                              # nothing ready -> idle
            jump = processes[order[nxt]].arrival
            _emit(gantt, GanttSegment.IDLE, time, jump)
            time = jump
            continue

        _, _, _, idx = heapq.heappop(heap)
        p = processes[idx]
        start[idx] = time
        time += p.burst
        completion[idx] = time
        _emit(gantt, p.pid, start[idx], time)
        done += 1

    return _build(name, processes, start, completion, gantt)


def sjf(processes: List[Process]) -> ScheduleResult:
    """Shortest Job First (non-preemptive)."""
    return _non_preemptive_heap(processes, "SJF", key=lambda p: p.burst)


def priority_scheduling(processes: List[Process],
                        lower_is_higher: bool = True) -> ScheduleResult:
    """Priority scheduling (non-preemptive). Lower number = higher priority."""
    sign = 1 if lower_is_higher else -1
    return _non_preemptive_heap(processes, "Priority", key=lambda p: sign * p.priority)


# --------------------------------------------------------------------------- #
# SRTF -- preemptive, event-driven min-heap on remaining time.
# --------------------------------------------------------------------------- #
def srtf(processes: List[Process]) -> ScheduleResult:
    """Shortest Remaining Time First (preemptive SJF).

    Instead of stepping one time unit at a time, we jump straight to the next
    decision point: a process runs until it finishes or the next arrival
    occurs, whichever comes first -- the only moments the choice can change.
    """
    n = len(processes)
    order = _arrival_order(processes)
    remaining = [p.burst for p in processes]
    start = [-1] * n
    completion = [0] * n
    gantt: List[GanttSegment] = []

    heap: List[tuple] = []
    time = 0
    nxt = 0
    done = 0

    while done < n:
        while nxt < n and processes[order[nxt]].arrival <= time:
            idx = order[nxt]
            p = processes[idx]
            heapq.heappush(heap, (remaining[idx], p.arrival, p.pid, idx))
            nxt += 1

        if not heap:
            jump = processes[order[nxt]].arrival
            _emit(gantt, GanttSegment.IDLE, time, jump)
            time = jump
            continue

        rem, _, _, idx = heapq.heappop(heap)
        if start[idx] == -1:
            start[idx] = time

        next_arrival = processes[order[nxt]].arrival if nxt < n else _INF
        run = rem if next_arrival is _INF else min(rem, next_arrival - time)

        _emit(gantt, processes[idx].pid, time, time + run)
        time += run
        rem -= run

        if rem == 0:
            completion[idx] = time
            done += 1
        else:
            p = processes[idx]
            heapq.heappush(heap, (rem, p.arrival, p.pid, idx))

    return _build("SRTF", processes, start, completion, gantt)


# --------------------------------------------------------------------------- #
# Round Robin -- deque, O(1) at both ends.
# --------------------------------------------------------------------------- #
def round_robin(processes: List[Process], quantum: int) -> ScheduleResult:
    """Round Robin with a fixed time quantum.

    Processes that arrive *during* a slice join the queue before the
    just-preempted process is re-added (standard textbook convention).
    """
    if quantum <= 0:
        raise ValueError("time quantum must be a positive integer")

    n = len(processes)
    order = _arrival_order(processes)
    remaining = [p.burst for p in processes]
    start = [-1] * n
    completion = [0] * n
    gantt: List[GanttSegment] = []

    queue: deque[int] = deque()
    time = 0
    nxt = 0
    done = 0

    def release(upto: int) -> None:
        nonlocal nxt
        while nxt < n and processes[order[nxt]].arrival <= upto:
            queue.append(order[nxt])
            nxt += 1

    release(0)

    while done < n:
        if not queue:                             # idle until next arrival
            jump = processes[order[nxt]].arrival
            _emit(gantt, GanttSegment.IDLE, time, jump)
            time = jump
            release(time)
            continue

        idx = queue.popleft()
        if start[idx] == -1:
            start[idx] = time

        run = quantum if remaining[idx] > quantum else remaining[idx]
        begin = time
        time += run
        remaining[idx] -= run
        _emit(gantt, processes[idx].pid, begin, time)

        release(time)                             # arrivals during this slice
        if remaining[idx] > 0:
            queue.append(idx)
        else:
            completion[idx] = time
            done += 1

    return _build(f"Round Robin (q={quantum})", processes,
                  start, completion, gantt)


# --------------------------------------------------------------------------- #
# Registry. RR is wrapped so every entry shares the same call signature.
# --------------------------------------------------------------------------- #
ALGORITHMS: dict[str, Callable[..., ScheduleResult]] = {
    "FCFS": fcfs,
    "SJF": sjf,
    "SRTF": srtf,
    "Priority": priority_scheduling,
    "RR": round_robin,
}
