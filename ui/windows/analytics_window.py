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
                    assessment: a sortable table (reusing TableView) plus
                    a horizontal bar chart of completion %. Horizontal
                    bars were chosen over vertical so assessment names
                    stay horizontal and readable even with several
                    assessments, rather than needing rotated labels.
  Grader Workload - how many items each TA has graded across the course
                    and their average score given, as a sortable table
                    plus a bar chart the TA can switch between "Graded
                    Count" and "Average Score Given". This is meant as a
                    consistency check across TAs, not a performance
                    evaluation of any individual TA.

Every chart has a "Save Chart" button beneath it (PNG or PDF, defaulting
into the same per-course export folder ExportWindow uses) so a TA can pull
a chart out to send to a professor without re-building it elsewhere.

More tabs (per-student lookup, at-risk list) are a planned follow-up once
this first set is in real use.

Unlike the app's small fixed-size popups, this window is resizable and
sized for charts/tables - modeled on HistogramWindow's own
(custom_titlebar=True, modal=False) combination, which is the one already
proven safe for a non-modal popup with a real title bar (see popup.py's
docstring on why chromeless + grab_set() was avoided).
"""
import os

from tkinter import ttk, filedialog, messagebox

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ui.widgets.popup import Popup
from ui.widgets.table_view import TableView
from db.analytics_repository import AnalyticsRepository
from config import EXPORT_DIRECTORY
from logging_setup import get_logger

logger = get_logger("ui.analytics_window")


class AnalyticsWindow(Popup):
    def __init__(self, parent, theme, analytics_repository: AnalyticsRepository, course_name: str):
        super().__init__(parent, "Analytics", theme, width=900, height=650,
                          resizable=True, custom_titlebar=True, modal=False)
        self.analytics = analytics_repository
        self.course_name = course_name
        self._open_figures = []  # every embedded figure, closed together on window close

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

    # ---- shared chart plumbing ----
    def _embed_chart(self, parent_frame, fig, default_filename: str):
        """Clears parent_frame, embeds fig, and adds a Save Chart button
        beneath it. Tracks fig in self._open_figures so every chart is
        closed together when the window closes, regardless of which tab
        it lives in."""
        for widget in parent_frame.winfo_children():
            widget.destroy()

        parent_frame.grid_rowconfigure(0, weight=1)
        parent_frame.grid_columnconfigure(0, weight=1)

        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self._open_figures.append(fig)

        ttk.Button(
            parent_frame, text="Save Chart",
            command=lambda: self._save_figure(fig, default_filename),
        ).grid(row=1, column=0, pady=(5, 0))

    def _save_figure(self, fig, default_filename: str):
        folder = os.path.join(EXPORT_DIRECTORY, self.course_name) if self.course_name else EXPORT_DIRECTORY
        os.makedirs(folder, exist_ok=True)
        filepath = filedialog.asksaveasfilename(
            initialdir=folder,
            initialfile=f"{default_filename}.png",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("PDF document", "*.pdf")],
            title="Save Chart",
        )
        if not filepath:
            return
        try:
            fig.savefig(filepath, facecolor=fig.get_facecolor(), bbox_inches="tight")
            messagebox.showinfo("Chart Saved", f"Saved to {filepath}")
        except Exception as e:
            logger.exception("Failed to save chart to %s", filepath)
            messagebox.showerror("Error", str(e))

    def _new_figure(self):
        """A fresh themed Figure/Axes pair - shared styling for every
        chart in this window (histogram, completion bars, workload bars)
        so they look consistent with each other and with the active
        theme."""
        fig, ax = plt.subplots()
        fig.patch.set_facecolor(self.theme.BG)
        ax.set_facecolor(self.theme.CARD)
        ax.grid(color=self.theme.BORDER, linestyle="--", alpha=0.3)
        ax.tick_params(colors=self.theme.FG)
        for spine in ax.spines.values():
            spine.set_color(self.theme.BORDER)
        return fig, ax

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

        self._overview_chart_frame = ttk.Frame(tab)
        self._overview_chart_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)

        self._render_overview_chart()

    def _render_overview_chart(self):
        summary = self.summaries[self._selected_assessment.current()]

        base_text = f"Base Grade: {summary.base_grade} | " if summary.base_grade is not None else ""
        avg_text = f"{summary.average:.2f}" if summary.average is not None else "N/A"
        high_text = f"{summary.highest:.2f}" if summary.highest is not None else "N/A"
        low_text = f"{summary.lowest:.2f}" if summary.lowest is not None else "N/A"
        self._stats_label.config(
            text=f"{base_text}Average: {avg_text} | Highest: {high_text} | Lowest: {low_text} "
                 f"| Graded: {summary.graded_count}/{summary.roster_size} ({summary.completion_percent}%)"
        )

        for widget in self._overview_chart_frame.winfo_children():
            widget.destroy()

        if not summary.scores:
            ttk.Label(self._overview_chart_frame, text="No numeric scores to plot yet.").grid(row=0, column=0)
            return

        fig, ax = self._new_figure()
        ax.hist(summary.scores, bins=10, edgecolor=self.theme.BORDER, color=self.theme.PURPLE)
        ax.set_title(f"{summary.table_suffix} Score Distribution", color=self.theme.FG)
        ax.set_xlabel("Scores", color=self.theme.FG)
        ax.set_ylabel("Number of Students", color=self.theme.FG)

        self._embed_chart(self._overview_chart_frame, fig, f"{summary.table_suffix}_histogram")

    # ---- Completion ----
    def _build_completion_tab(self, tab):
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        table_frame = ttk.Frame(tab)
        table_frame.grid(row=0, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        table = TableView(table_frame)
        table.frame.grid(row=0, column=0, sticky="nsew")
        rows = [
            [s.table_suffix, f"{s.graded_count}/{s.roster_size}", f"{s.completion_percent}%"]
            for s in self.summaries
        ]
        table.render(["Assessment", "Graded", "Completion"], rows)

        chart_frame = ttk.Frame(tab)
        chart_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        if not self.summaries:
            ttk.Label(chart_frame, text="No assessments yet.").grid(row=0, column=0)
            return

        labels = [s.table_suffix for s in self.summaries]
        percents = [s.completion_percent for s in self.summaries]

        fig, ax = self._new_figure()
        ax.barh(labels, percents, color=self.theme.PURPLE, edgecolor=self.theme.BORDER)
        ax.set_xlim(0, 100)
        ax.set_xlabel("Completion %", color=self.theme.FG)
        ax.set_title(f"{self.course_name} Grading Completion", color=self.theme.FG)
        ax.invert_yaxis()  # first assessment on top, matching the table's order

        self._embed_chart(chart_frame, fig, f"{self.course_name}_completion")

    # ---- Grader Workload ----
    def _build_workload_tab(self, tab):
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        self._workloads = self.analytics.get_grader_workload(self.course_name)

        table_frame = ttk.Frame(tab)
        table_frame.grid(row=0, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        table = TableView(table_frame)
        table.frame.grid(row=0, column=0, sticky="nsew")
        rows = [
            [w.ta_name, w.graded_count, w.average_score_given if w.average_score_given is not None else "-"]
            for w in self._workloads
        ]
        table.render(["Grader", "Graded Count", "Avg Score Given"], rows)

        if not self._workloads:
            ttk.Label(tab, text="No graded items yet.").grid(row=1, column=0, pady=10)
            return

        header = ttk.Frame(tab)
        header.grid(row=1, column=0, sticky="ew", padx=10, pady=(10, 2))
        ttk.Label(header, text="Chart: ").pack(side="left")
        self._workload_metric = ttk.Combobox(
            header, values=["Graded Count", "Average Score Given"], state="readonly", width=22,
        )
        self._workload_metric.pack(side="left", padx=5)
        self._workload_metric.current(0)
        self._workload_metric.bind("<<ComboboxSelected>>", lambda e: self._render_workload_chart())

        self._workload_chart_frame = ttk.Frame(tab)
        self._workload_chart_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)

        self._render_workload_chart()

    def _render_workload_chart(self):
        for widget in self._workload_chart_frame.winfo_children():
            widget.destroy()

        metric = self._workload_metric.get()
        labels = [w.ta_name for w in self._workloads]

        if metric == "Graded Count":
            values = [w.graded_count for w in self._workloads]
            ylabel = "Items Graded"
        else:
            plotted = [(w.ta_name, w.average_score_given) for w in self._workloads if w.average_score_given is not None]
            if not plotted:
                ttk.Label(self._workload_chart_frame, text="No numeric scores to average yet.").grid(row=0, column=0)
                return
            labels = [name for name, _ in plotted]
            values = [avg for _, avg in plotted]
            ylabel = "Average Score Given"

        fig, ax = self._new_figure()
        ax.bar(labels, values, color=self.theme.PURPLE, edgecolor=self.theme.BORDER)
        ax.set_ylabel(ylabel, color=self.theme.FG)
        ax.set_title(f"Grader Workload - {metric}", color=self.theme.FG)
        if len(labels) > 4:
            # Rotate labels once there are enough graders that horizontal
            # names would start overlapping - untested against a large TA
            # roster, so this threshold is a reasonable guess rather than
            # something verified against real data.
            ax.tick_params(axis="x", rotation=30)

        self._embed_chart(self._workload_chart_frame, fig, f"{self.course_name}_workload_{metric.replace(' ', '_').lower()}")

    def close(self):
        for fig in self._open_figures:
            plt.close(fig)
        super().close()