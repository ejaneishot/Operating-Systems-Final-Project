"""Presentation layer: terminal tables, matplotlib charts and CSV export.

Kept separate from the algorithms so both front-ends (CLI and GUI) can share
exactly the same drawing/formatting code.
"""

from __future__ import annotations

import csv
from typing import List

import matplotlib.pyplot as plt
import pandas as pd

from .models import ScheduleResult

_PALETTE = [
    "#89b4fa", "#a6e3a1", "#f9e2af", "#f38ba8",
    "#cba6f7", "#94e2d5", "#fab387", "#b4befe",
]


# --------------------------------------------------------------------------- #
# Terminal colours / headings.
# --------------------------------------------------------------------------- #
class C:
    """ANSI colour codes for the CLI front-end."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"


def heading(text: str) -> str:
    bar = "=" * len(text)
    return f"{C.BOLD}{C.CYAN}{text}\n{bar}{C.RESET}"


# --------------------------------------------------------------------------- #
# Terminal table.
# --------------------------------------------------------------------------- #
def print_result(result: ScheduleResult) -> None:
    print(heading(result.algorithm))
    header = f"{'PID':<6}{'Arrival':<9}{'Burst':<7}{'Priority':<9}{'Start':<7}{'Completion':<12}{'Waiting':<9}{'Turnaround':<12}{'Response':<9}"
    print(header)
    for p in sorted(result.processes, key=lambda x: x.pid):
        print(
            f"{p.pid:<6}{p.arrival:<9}{p.burst:<7}{p.priority:<9}{p.start:<7}"
            f"{p.completion:<12}{p.waiting_time:<9}{p.turnaround_time:<12}{p.response_time:<9}"
        )
    print(
        f"\n{C.GREEN}Average waiting: {result.avg_waiting_time:.2f}   "
        f"Average turnaround: {result.avg_turnaround_time:.2f}   "
        f"Average response: {result.avg_response_time:.2f}{C.RESET}"
    )


# --------------------------------------------------------------------------- #
# Comparison table (pandas).
# --------------------------------------------------------------------------- #
def comparison_table(results: List[ScheduleResult]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Algorithm": [r.algorithm for r in results],
            "Avg Waiting": [round(r.avg_waiting_time, 2) for r in results],
            "Avg Turnaround": [round(r.avg_turnaround_time, 2) for r in results],
            "Avg Response": [round(r.avg_response_time, 2) for r in results],
        }
    )


# --------------------------------------------------------------------------- #
# Gantt chart.
# --------------------------------------------------------------------------- #
def _colour_for(label: str, colours: dict) -> str:
    if label not in colours:
        colours[label] = _PALETTE[len(colours) % len(_PALETTE)]
    return colours[label]


def render_gantt(ax, result: ScheduleResult) -> None:
    """Draw ``result``'s Gantt chart onto an existing matplotlib axes."""
    colours: dict = {}
    for seg in result.gantt:
        colour = "#45475a" if seg.is_idle else _colour_for(seg.label, colours)
        ax.broken_barh([(seg.start, seg.duration)], (0, 1), facecolors=colour,
                       edgecolors="#1e1e2e")
        if seg.duration > 0:
            ax.text(seg.start + seg.duration / 2, 0.5, seg.label,
                    ha="center", va="center", fontsize=9,
                    color="#1e1e2e" if not seg.is_idle else "#cdd6f4")

    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_xlabel("Time")
    ax.set_title(f"{result.algorithm} - Gantt Chart")


def plot_gantt(result: ScheduleResult) -> None:
    """Open a standalone matplotlib window with ``result``'s Gantt chart."""
    fig, ax = plt.subplots(figsize=(9, 2.5))
    render_gantt(ax, result)
    fig.tight_layout()
    plt.show()


# --------------------------------------------------------------------------- #
# Comparison bar chart.
# --------------------------------------------------------------------------- #
def render_comparison(ax, results: List[ScheduleResult]) -> None:
    """Draw a grouped bar chart comparing average metrics onto ``ax``."""
    labels = [r.algorithm for r in results]
    metrics = {
        "Avg Waiting": [r.avg_waiting_time for r in results],
        "Avg Turnaround": [r.avg_turnaround_time for r in results],
        "Avg Response": [r.avg_response_time for r in results],
    }

    n_groups = len(labels)
    n_bars = len(metrics)
    width = 0.8 / n_bars
    x = range(n_groups)

    for i, (name, values) in enumerate(metrics.items()):
        offsets = [pos + (i - (n_bars - 1) / 2) * width for pos in x]
        ax.bar(offsets, values, width=width, label=name, color=_PALETTE[i % len(_PALETTE)])

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Time")
    ax.set_title("Algorithm Comparison")
    ax.legend()


def plot_comparison(results: List[ScheduleResult]) -> None:
    """Open a standalone matplotlib window with the comparison bar chart."""
    fig, ax = plt.subplots(figsize=(9, 5))
    render_comparison(ax, results)
    fig.tight_layout()
    plt.show()


# --------------------------------------------------------------------------- #
# CSV export.
# --------------------------------------------------------------------------- #
def export_csv(result: ScheduleResult, path: str) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "PID", "Arrival", "Burst", "Priority", "Start", "Completion",
            "Waiting", "Turnaround", "Response",
        ])
        for p in sorted(result.processes, key=lambda x: x.pid):
            writer.writerow([
                p.pid, p.arrival, p.burst, p.priority, p.start, p.completion,
                p.waiting_time, p.turnaround_time, p.response_time,
            ])
