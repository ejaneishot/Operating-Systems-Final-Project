"""A modern dark-themed GUI for the CPU Scheduling Simulator.

Built with Tkinter + ttk (no extra dependencies) and an embedded matplotlib
canvas for the Gantt and comparison charts. It is purely a *front-end*: all
scheduling is done by the same ``scheduler`` package used by the CLI, so there
is exactly one implementation of every algorithm to understand and maintain.

Run it with::

    python gui.py
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from scheduler import (
    Process,
    fcfs,
    priority_scheduling,
    round_robin,
    sjf,
    srtf,
)
from scheduler.visualize import export_csv, render_comparison, render_gantt
from scheduler.workloads import random_workload, sample_workload


# --------------------------------------------------------------------------- #
# Colour palette (Catppuccin Mocha) -- one place to restyle the whole app.
# --------------------------------------------------------------------------- #
class Theme:
    BG = "#1e1e2e"
    SURFACE = "#313244"
    SURFACE2 = "#45475a"
    TEXT = "#cdd6f4"
    SUBTEXT = "#a6adc8"
    ACCENT = "#89b4fa"
    GREEN = "#a6e3a1"
    RED = "#f38ba8"
    FONT = ("Segoe UI", 10)
    FONT_BOLD = ("Segoe UI", 11, "bold")
    FONT_TITLE = ("Segoe UI", 16, "bold")


ALGORITHMS = ["FCFS", "SJF", "SRTF", "Priority", "Round Robin"]


class SchedulerGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CPU Scheduling Simulator")
        self.geometry("1180x720")
        self.configure(bg=Theme.BG)
        self.minsize(1000, 640)

        self.processes: List[Process] = sample_workload()

        self._configure_style()
        self._build_layout()
        self._refresh_process_table()
        self._on_algorithm_change()

    # ------------------------------------------------------------------ #
    # Styling
    # ------------------------------------------------------------------ #
    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".", background=Theme.BG, foreground=Theme.TEXT,
                        font=Theme.FONT, borderwidth=0)
        style.configure("Card.TFrame", background=Theme.SURFACE)
        style.configure("TLabel", background=Theme.BG, foreground=Theme.TEXT)
        style.configure("Card.TLabel", background=Theme.SURFACE, foreground=Theme.TEXT)
        style.configure("Title.TLabel", background=Theme.BG, foreground=Theme.TEXT,
                        font=Theme.FONT_TITLE)
        style.configure("Sub.TLabel", background=Theme.SURFACE, foreground=Theme.SUBTEXT)
        style.configure("Metric.TLabel", background=Theme.SURFACE,
                        foreground=Theme.GREEN, font=Theme.FONT_BOLD)

        # Buttons
        style.configure("Accent.TButton", background=Theme.ACCENT, foreground=Theme.BG,
                        font=Theme.FONT_BOLD, padding=8, borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#b4befe")])
        style.configure("TButton", background=Theme.SURFACE2, foreground=Theme.TEXT,
                        padding=6, borderwidth=0)
        style.map("TButton", background=[("active", Theme.ACCENT),
                                        ("active", "!disabled", Theme.ACCENT)])

        # Entries / combobox
        for el in ("TEntry", "TCombobox"):
            style.configure(el, fieldbackground=Theme.SURFACE2, foreground=Theme.TEXT,
                            background=Theme.SURFACE2, borderwidth=0, padding=5,
                            arrowcolor=Theme.TEXT)
        style.map("TCombobox", fieldbackground=[("readonly", Theme.SURFACE2)])

        # Treeview (tables)
        style.configure("Treeview", background=Theme.SURFACE, fieldbackground=Theme.SURFACE,
                        foreground=Theme.TEXT, rowheight=26, borderwidth=0)
        style.configure("Treeview.Heading", background=Theme.SURFACE2,
                        foreground=Theme.TEXT, font=Theme.FONT_BOLD, borderwidth=0)
        style.map("Treeview", background=[("selected", Theme.ACCENT)],
                  foreground=[("selected", Theme.BG)])

        style.configure("TNotebook", background=Theme.BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=Theme.SURFACE, foreground=Theme.SUBTEXT,
                        padding=(16, 8), font=Theme.FONT_BOLD)
        style.map("TNotebook.Tab", background=[("selected", Theme.SURFACE2)],
                  foreground=[("selected", Theme.TEXT)])

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _build_layout(self) -> None:
        ttk.Label(self, text="CPU Scheduling Simulator", style="Title.TLabel").pack(
            anchor="w", padx=20, pady=(16, 10)
        )

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self._build_left_panel(body)
        self._build_right_panel(body)

        self.status = ttk.Label(self, text="Ready.", style="Sub.TLabel", anchor="w")
        self.status.configure(background=Theme.SURFACE)
        self.status.pack(fill="x", side="bottom", ipady=6)

    def _build_left_panel(self, parent) -> None:
        left = ttk.Frame(parent, style="Card.TFrame", padding=16)
        left.pack(side="left", fill="y", padx=(0, 16))

        ttk.Label(left, text="Add Process", style="Card.TLabel",
                  font=Theme.FONT_BOLD).grid(row=0, column=0, columnspan=2, sticky="w")

        self.entries = {}
        fields = [("PID", "pid"), ("Arrival", "arrival"),
                  ("Burst", "burst"), ("Priority", "priority")]
        for i, (label, key) in enumerate(fields, start=1):
            ttk.Label(left, text=label, style="Card.TLabel").grid(
                row=i, column=0, sticky="w", pady=4)
            entry = ttk.Entry(left, width=14)
            entry.grid(row=i, column=1, sticky="ew", pady=4, padx=(8, 0))
            self.entries[key] = entry

        ttk.Button(left, text="+ Add", style="Accent.TButton",
                   command=self._add_process).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(8, 12))

        # Process list
        ttk.Label(left, text="Processes", style="Card.TLabel",
                  font=Theme.FONT_BOLD).grid(row=6, column=0, columnspan=2, sticky="w")
        cols = ("PID", "Arr", "Burst", "Prio")
        self.proc_tree = ttk.Treeview(left, columns=cols, show="headings", height=7)
        for c, w in zip(cols, (50, 50, 50, 50)):
            self.proc_tree.heading(c, text=c)
            self.proc_tree.column(c, width=w, anchor="center")
        self.proc_tree.grid(row=7, column=0, columnspan=2, sticky="ew", pady=6)

        for text, cmd in [("Remove Selected", self._remove_selected),
                          ("Load Sample", self._load_sample),
                          ("Random Workload", self._load_random),
                          ("Clear All", self._clear_all)]:
            ttk.Button(left, text=text, command=cmd).grid(
                column=0, columnspan=2, sticky="ew", pady=2)

        ttk.Separator(left, orient="horizontal").grid(
            row=99, column=0, columnspan=2, sticky="ew", pady=12)

        # Run controls
        ttk.Label(left, text="Algorithm", style="Card.TLabel").grid(
            row=100, column=0, sticky="w", pady=4)
        self.algo_var = tk.StringVar(value=ALGORITHMS[0])
        self.algo_box = ttk.Combobox(left, textvariable=self.algo_var,
                                     values=ALGORITHMS, state="readonly", width=14)
        self.algo_box.grid(row=100, column=1, sticky="ew", pady=4, padx=(8, 0))
        self.algo_box.bind("<<ComboboxSelected>>", lambda _e: self._on_algorithm_change())

        self.quantum_label = ttk.Label(left, text="Quantum", style="Card.TLabel")
        self.quantum_label.grid(row=101, column=0, sticky="w", pady=4)
        self.quantum_entry = ttk.Entry(left, width=14)
        self.quantum_entry.insert(0, "2")
        self.quantum_entry.grid(row=101, column=1, sticky="ew", pady=4, padx=(8, 0))

        ttk.Button(left, text="Run", style="Accent.TButton",
                   command=self._run_selected).grid(
            row=102, column=0, columnspan=2, sticky="ew", pady=(12, 4))
        ttk.Button(left, text="Compare All Algorithms",
                   command=self._compare_all).grid(row=103, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(left, text="Export Results to CSV",
                   command=self._export_csv).grid(row=104, column=0, columnspan=2, sticky="ew", pady=2)

    def _build_right_panel(self, parent) -> None:
        right = ttk.Frame(parent)
        right.pack(side="right", fill="both", expand=True)

        notebook = ttk.Notebook(right)
        notebook.pack(fill="both", expand=True)

        # --- Results tab ---
        results = ttk.Frame(notebook, style="Card.TFrame", padding=12)
        notebook.add(results, text="  Results  ")

        self.metric_var = tk.StringVar(value="Run an algorithm to see results.")
        ttk.Label(results, textvariable=self.metric_var, style="Metric.TLabel").pack(
            anchor="w", pady=(0, 8))

        cols = ("PID", "Arrival", "Burst", "Priority", "Start",
                "Completion", "Waiting", "Turnaround", "Response")
        self.result_tree = ttk.Treeview(results, columns=cols, show="headings", height=6)
        for c in cols:
            self.result_tree.heading(c, text=c)
            self.result_tree.column(c, width=80, anchor="center")
        self.result_tree.pack(fill="x", pady=(0, 10))

        self.gantt_fig = Figure(figsize=(7, 2.6), dpi=100)
        self._style_figure(self.gantt_fig)
        self.gantt_canvas = FigureCanvasTkAgg(self.gantt_fig, master=results)
        self.gantt_canvas.get_tk_widget().pack(fill="both", expand=True)

        # --- Compare tab ---
        compare = ttk.Frame(notebook, style="Card.TFrame", padding=12)
        notebook.add(compare, text="  Compare  ")
        self.compare_fig = Figure(figsize=(7, 4.5), dpi=100)
        self._style_figure(self.compare_fig)
        self.compare_canvas = FigureCanvasTkAgg(self.compare_fig, master=compare)
        self.compare_canvas.get_tk_widget().pack(fill="both", expand=True)
        self.notebook = notebook

    # ------------------------------------------------------------------ #
    # Matplotlib dark styling
    # ------------------------------------------------------------------ #
    def _style_figure(self, fig: Figure) -> None:
        fig.patch.set_facecolor(Theme.SURFACE)

    def _style_axes(self, ax) -> None:
        ax.set_facecolor(Theme.SURFACE)
        ax.tick_params(colors=Theme.TEXT)
        for spine in ax.spines.values():
            spine.set_color(Theme.SUBTEXT)
        ax.xaxis.label.set_color(Theme.TEXT)
        ax.yaxis.label.set_color(Theme.TEXT)
        ax.title.set_color(Theme.TEXT)

    # ------------------------------------------------------------------ #
    # Workload management
    # ------------------------------------------------------------------ #
    def _add_process(self) -> None:
        try:
            pid = self.entries["pid"].get().strip() or f"P{len(self.processes) + 1}"
            p = Process(
                pid,
                int(self.entries["arrival"].get()),
                int(self.entries["burst"].get()),
                int(self.entries["priority"].get() or 0),
            )
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc) or "Please enter whole numbers.")
            return
        self.processes.append(p)
        for e in self.entries.values():
            e.delete(0, tk.END)
        self._refresh_process_table()
        self._set_status(f"Added {p.pid}.")

    def _remove_selected(self) -> None:
        selected = self.proc_tree.selection()
        if not selected:
            return
        pids = {self.proc_tree.item(i, "values")[0] for i in selected}
        self.processes = [p for p in self.processes if p.pid not in pids]
        self._refresh_process_table()

    def _load_sample(self) -> None:
        self.processes = sample_workload()
        self._refresh_process_table()
        self._set_status("Loaded sample workload.")

    def _load_random(self) -> None:
        self.processes = random_workload(n=5)
        self._refresh_process_table()
        self._set_status("Generated random workload.")

    def _clear_all(self) -> None:
        self.processes = []
        self._refresh_process_table()

    def _refresh_process_table(self) -> None:
        self.proc_tree.delete(*self.proc_tree.get_children())
        for p in self.processes:
            self.proc_tree.insert("", "end", values=(p.pid, p.arrival, p.burst, p.priority))

    def _on_algorithm_change(self) -> None:
        is_rr = self.algo_var.get() == "Round Robin"
        state = "normal" if is_rr else "disabled"
        self.quantum_entry.configure(state=state)

    # ------------------------------------------------------------------ #
    # Running
    # ------------------------------------------------------------------ #
    def _build_result(self, name: str):
        if not self.processes:
            raise ValueError("Add at least one process first.")
        if name == "FCFS":
            return fcfs(self.processes)
        if name == "SJF":
            return sjf(self.processes)
        if name == "SRTF":
            return srtf(self.processes)
        if name == "Priority":
            return priority_scheduling(self.processes)
        if name == "Round Robin":
            return round_robin(self.processes, int(self.quantum_entry.get()))
        raise ValueError(name)

    def _run_selected(self) -> None:
        try:
            result = self._build_result(self.algo_var.get())
        except ValueError as exc:
            messagebox.showerror("Cannot run", str(exc))
            return

        self.result_tree.delete(*self.result_tree.get_children())
        for p in sorted(result.processes, key=lambda x: x.pid):
            self.result_tree.insert("", "end", values=(
                p.pid, p.arrival, p.burst, p.priority, p.start, p.completion,
                p.waiting_time, p.turnaround_time, p.response_time,
            ))

        self.metric_var.set(
            f"{result.algorithm}    |    "
            f"Avg Waiting: {result.avg_waiting_time:.2f}    "
            f"Avg Turnaround: {result.avg_turnaround_time:.2f}    "
            f"Avg Response: {result.avg_response_time:.2f}"
        )

        self.gantt_fig.clear()
        ax = self.gantt_fig.add_subplot(111)
        render_gantt(ax, result)
        self._style_axes(ax)
        self.gantt_fig.tight_layout()
        self.gantt_canvas.draw()
        self._set_status(f"Ran {result.algorithm}.")
        self._last_result = result

    def _compare_all(self) -> None:
        if not self.processes:
            messagebox.showerror("Cannot run", "Add at least one process first.")
            return
        try:
            q = int(self.quantum_entry.get() or 2)
        except ValueError:
            q = 2
        results = [
            fcfs(self.processes), sjf(self.processes), srtf(self.processes),
            priority_scheduling(self.processes), round_robin(self.processes, q),
        ]
        self.compare_fig.clear()
        ax = self.compare_fig.add_subplot(111)
        render_comparison(ax, results)
        self._style_axes(ax)
        leg = ax.get_legend()
        if leg:
            leg.get_frame().set_facecolor(Theme.SURFACE2)
            for txt in leg.get_texts():
                txt.set_color(Theme.TEXT)
        self.notebook.select(1)
        self.update_idletasks()
        self.compare_fig.tight_layout()
        self.compare_canvas.draw()

        best = min(results, key=lambda r: r.avg_waiting_time)
        self._set_status(f"Compared all. Lowest avg waiting: {best.algorithm}.")

    def _export_csv(self) -> None:
        if not getattr(self, "_last_result", None):
            messagebox.showinfo("Nothing to export", "Run an algorithm first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=f"{self._last_result.algorithm}_results.csv")
        if path:
            export_csv(self._last_result, path)
            self._set_status(f"Exported to {path}.")

    def _set_status(self, text: str) -> None:
        self.status.configure(text=text)


def main() -> None:
    SchedulerGUI().mainloop()


if __name__ == "__main__":
    main()
