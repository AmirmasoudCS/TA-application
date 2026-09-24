"""
Dedicated Analytics window: a tabbed view (ttk.Notebook) over cross-
assessment analytics for the current course, replacing the old single
"Show Histogram" button. Built on db.analytics_repository.AnalyticsRepository
rather than querying the database directly.

Tabs:
  Overview        - per-assessment average/high/low/completion plus a
                    histogram for whichever assessment is selected. This
                    absorbs what used to be its own separate popup
                    (ui/windows/histogram_window.py) - the chart code here
                    is the same matplotlib approach, just embedded in a
                    tab instead of opening a second window.
  Completion      - how many of the roster have been graded so far, per
                    assessment. Reuses TableView (sortable columns for
                    free) rather than a new widget.
  Grader Workload - how many items each TA has graded across the course,
                    and their average score given - a consistency check
                    across TAs, not a performance evaluation of them.

More tabs (per-student lookup, at-risk list) are a planned follow-up once
this first set is in real use.

Unlike the app's small fixed-size popups, this window is resizable and
sized for charts/tables - modeled on HistogramWindow's own
(custom_titlebar=True, modal=False) combination, which is the one already
proven safe for a non-modal popup with a real title bar (see popup.py's
docstring on why chromeless + grab_set() was avoided).
"""
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ui.widgets.popup import Popup
from ui.widgets.table_view import TableView
from db.analytics_repository import AnalyticsRepository


class AnalyticsWindow(Popup):
    def __init__(self, parent, theme, analytics_repository: AnalyticsRepository, course_name: str):
        super().__init__(parent, "Analytics", theme, width=900, height=650,
                          resizable=True, custom_titlebar=True, modal=False)
        self.analytics = analytics_repository
        self.course_name = course_name
        self._figure = None

        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        notebook = ttk.Notebook(self.content)
        notebook.grid(row=0, column=0, sticky="nsew")

        self.summaries = self.analytics.get_assessment_summaries(course_name)

        overview_tab = ttk.Frame(notebook)
        completion_tab = ttk.Frame(notebook)
        workload_tab = ttk.Frame(notebook)
        notebook.add(overview_tab, text="Overview")
        notebook.add(completion_tab, text="Completion")
        notebook.add(workload_tab, text="Grader Workload")

        self._build_overview_tab(overview_tab)
        self._build_completion_tab(completion_tab)
        self._build_workload_tab(workload_tab)

        self.center_over_parent()

    # ---- Overview ----
    def _build_overview_tab(self, tab):
        tab.grid_rowconfigure(2, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        if not self.summaries:
            ttk.Label(tab, text="No assessments with grades yet.").grid(row=0, column=0, pady=20)
            return

        header = ttk.Frame(tab)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 2))
        ttk.Label(header, text="Assessment: ").pack(side="left")
        self._selected_assessment = ttk.Combobox(
            header, values=[s.table_suffix for s in self.summaries], state="readonly", width=25,
        )
        self._selected_assessment.pack(side="left", padx=5)
        self._selected_assessment.current(0)
        self._selected_assessment.bind("<<ComboboxSelected>>", lambda e: self._render_overview_chart())

        self._stats_label = ttk.Label(tab, text="")
        self._stats_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))

        self._chart_frame = ttk.Frame(tab)
        self._chart_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self._chart_frame.grid_rowconfigure(0, weight=1)
        self._chart_frame.grid_columnconfigure(0, weight=1)

        self._render_overview_chart()

    def _render_overview_chart(self):
        for widget in self._chart_frame.winfo_children():
            widget.destroy()
        if self._figure is not None:
            plt.close(self._figure)
            self._figure = None

        summary = self.summaries[self._selected_assessment.current()]

        base_text = f"Base Grade: {summary.base_grade} | " if summary.base_grade is not None else ""
        avg_text = f"{summary.average:.2f}" if summary.average is not None else "N/A"
        high_text = f"{summary.highest:.2f}" if summary.highest is not None else "N/A"
        low_text = f"{summary.lowest:.2f}" if summary.lowest is not None else "N/A"
        self._stats_label.config(
            text=f"{base_text}Average: {avg_text} | Highest: {high_text} | Lowest: {low_text} "
                 f"| Graded: {summary.graded_count}/{summary.roster_size} ({summary.completion_percent}%)"
        )

        if not summary.scores:
            ttk.Label(self._chart_frame, text="No numeric scores to plot yet.").grid(row=0, column=0)
            return

        fig, ax = plt.subplots()
        fig.patch.set_facecolor(self.theme.BG)
        ax.set_facecolor(self.theme.CARD)
        ax.hist(summary.scores, bins=10, edgecolor=self.theme.BORDER, color=self.theme.PURPLE)
        ax.set_title(f"{summary.table_suffix} Score Distribution", color=self.theme.FG)
        ax.set_xlabel("Scores", color=self.theme.FG)
        ax.set_ylabel("Number of Students", color=self.theme.FG)
        ax.grid(color=self.theme.BORDER, linestyle="--", alpha=0.3)
        ax.tick_params(colors=self.theme.FG)
        for spine in ax.spines.values():
            spine.set_color(self.theme.BORDER)
        self._figure = fig

        canvas = FigureCanvasTkAgg(fig, master=self._chart_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    # ---- Completion ----
    def _build_completion_tab(self, tab):
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        table = TableView(tab)
        table.frame.grid(row=0, column=0, sticky="nsew")
        rows = [
            [s.table_suffix, f"{s.graded_count}/{s.roster_size}", f"{s.completion_percent}%"]
            for s in self.summaries
        ]
        table.render(["Assessment", "Graded", "Completion"], rows)

    # ---- Grader Workload ----
    def _build_workload_tab(self, tab):
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        table = TableView(tab)
        table.frame.grid(row=0, column=0, sticky="nsew")
        workloads = self.analytics.get_grader_workload(self.course_name)
        rows = [
            [w.ta_name, w.graded_count, w.average_score_given if w.average_score_given is not None else "-"]
            for w in workloads
        ]
        table.render(["Grader", "Graded Count", "Avg Score Given"], rows)

    def close(self):
        if self._figure is not None:
            plt.close(self._figure)
        super().close()