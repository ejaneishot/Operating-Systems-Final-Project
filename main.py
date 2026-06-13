"""Interactive command-line front-end for the CPU Scheduling Simulator.

Run it with::

    python main.py

Everything the simulator can do is reachable from a single menu:
enter or generate a workload, run any algorithm, compare them all,
draw Gantt charts, and export the results.

The heavy lifting lives in the ``scheduler`` package -- this file only
deals with reading input, printing menus and wiring things together.
"""

from __future__ import annotations

from typing import List, Optional

from scheduler import (
    Process,
    fcfs,
    priority_scheduling,
    round_robin,
    sjf,
    srtf,
)
from scheduler.visualize import (
    C,
    comparison_table,
    export_csv,
    heading,
    plot_comparison,
    plot_gantt,
    print_result,
)
from scheduler.workloads import random_workload, sample_workload


# --------------------------------------------------------------------------- #
# Small, reusable input helpers with validation.
# --------------------------------------------------------------------------- #
def ask_int(prompt: str, minimum: Optional[int] = None) -> int:
    while True:
        try:
            value = int(input(prompt).strip())
            if minimum is not None and value < minimum:
                print(f"  Please enter a value >= {minimum}.")
                continue
            return value
        except ValueError:
            print("  Please enter a whole number.")


def ask_choice(prompt: str, options: List[str]) -> str:
    options_lower = {o.lower(): o for o in options}
    while True:
        choice = input(f"{prompt} ({'/'.join(options)}): ").strip().lower()
        if choice in options_lower:
            return options_lower[choice]
        print(f"  Choose one of: {', '.join(options)}")


# --------------------------------------------------------------------------- #
# Workload entry.
# --------------------------------------------------------------------------- #
def enter_processes_manually() -> List[Process]:
    n = ask_int("How many processes? ", minimum=1)
    processes: List[Process] = []
    for i in range(n):
        print(f"\n{C.DIM}--- Process {i + 1} ---{C.RESET}")
        pid = input("  Process ID (blank for auto): ").strip() or f"P{i + 1}"
        arrival = ask_int("  Arrival time: ", minimum=0)
        burst = ask_int("  Burst time: ", minimum=1)
        priority = ask_int("  Priority (lower = higher priority): ", minimum=0)
        processes.append(Process(pid, arrival, burst, priority))
    return processes


def describe_workload(processes: List[Process]) -> None:
    print(f"\n{C.BOLD}Current workload ({len(processes)} processes):{C.RESET}")
    print(f"  {'PID':<6}{'Arrival':<9}{'Burst':<7}{'Priority':<9}")
    for p in processes:
        print(f"  {p.pid:<6}{p.arrival:<9}{p.burst:<7}{p.priority:<9}")


# --------------------------------------------------------------------------- #
# Running algorithms.
# --------------------------------------------------------------------------- #
def run_single(processes: List[Process]) -> None:
    name = ask_choice(
        "Which algorithm?", ["FCFS", "SJF", "SRTF", "Priority", "RR"]
    )
    result = run_named(name, processes)
    print_result(result)

    if ask_choice("\nShow matplotlib Gantt chart?", ["y", "n"]) == "y":
        plot_gantt(result)


def run_named(name: str, processes: List[Process]):
    if name == "FCFS":
        return fcfs(processes)
    if name == "SJF":
        return sjf(processes)
    if name == "SRTF":
        return srtf(processes)
    if name == "Priority":
        return priority_scheduling(processes)
    if name == "RR":
        q = ask_int("  Time quantum: ", minimum=1)
        return round_robin(processes, q)
    raise ValueError(name)


def compare_all(processes: List[Process]) -> None:
    q = ask_int("Time quantum for Round Robin: ", minimum=1)
    results = [
        fcfs(processes),
        sjf(processes),
        srtf(processes),
        priority_scheduling(processes),
        round_robin(processes, q),
    ]
    print(heading("Comparison"))
    print(comparison_table(results).to_string(index=False))

    best = min(results, key=lambda r: r.avg_waiting_time)
    print(f"\n{C.GREEN}Lowest average waiting time: {best.algorithm}{C.RESET}")

    if ask_choice("\nShow comparison bar chart?", ["y", "n"]) == "y":
        plot_comparison(results)


def export_results(processes: List[Process]) -> None:
    name = ask_choice(
        "Export which algorithm's results?", ["FCFS", "SJF", "SRTF", "Priority", "RR"]
    )
    result = run_named(name, processes)
    path = input("  File name (e.g. results.csv): ").strip() or "results.csv"
    export_csv(result, path)
    print(f"{C.GREEN}Saved to {path}{C.RESET}")


# --------------------------------------------------------------------------- #
# Menu loop.
# --------------------------------------------------------------------------- #
MENU = """
{title}
  1. Enter processes manually
  2. Use sample workload
  3. Generate random workload
  4. Run a single algorithm
  5. Compare all algorithms
  6. Export results to CSV
  0. Exit
"""


def main() -> None:
    processes: List[Process] = sample_workload()
    print(f"{C.DIM}(Loaded a sample workload to start with.){C.RESET}")

    while True:
        print(MENU.format(title=heading("CPU Scheduling Simulator")))
        choice = input("Select an option: ").strip()

        if choice == "1":
            processes = enter_processes_manually()
            describe_workload(processes)
        elif choice == "2":
            processes = sample_workload()
            describe_workload(processes)
        elif choice == "3":
            n = ask_int("How many random processes? ", minimum=1)
            processes = random_workload(n=n)
            describe_workload(processes)
        elif choice == "4":
            run_single(processes)
        elif choice == "5":
            compare_all(processes)
        elif choice == "6":
            export_results(processes)
        elif choice == "0":
            print("Goodbye.")
            break
        else:
            print("  Unknown option.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
