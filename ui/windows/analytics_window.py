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
  Student Lookup  - search one student (by Sid or name) and see every
                    assessment they've been graded on, a "vs. class
                    average" delta per assessment (on the normalized
                    scale - see analytics_repository's module docstring),
                    and a progress chart of their normalized score
                    alongside the class average, ordered by when each was
                    graded (UpdatedAt) rather than assessment name, so it
                    reads as an actual timeline rather than an arbitrary
                    ordering. Records with no UpdatedAt (from before that
                    column existed) sort to the end. Flags the student if
                    their average is below the At-Risk tab's threshold.
                    "Export Report" (CSV/Excel/PDF Report/All, reusing
                    ExportWindow) generates a per-student report: for PDF
                    specifically this is a real document (title, summary
                    info, the same progress chart embedded as an image,
                    then the table) via ExportService.export_report_pdf,
                    not just a bare table dump.
  At-Risk         - every roster student whose overall normalized average
                    is below an adjustable threshold (shared with Student
                    Lookup's flag), sorted lowest-first, with its own
                    Export List (CSV/Excel/PDF/All, reusing ExportWindow)
                    since this is the view most likely to get sent
                    straight to a professor.

Every chart has a "Save Chart" button beneath it (PNG or PDF, defaulting
into the same per-course export folder ExportWindow uses) so a TA can pull
a chart out to send to a professor without re-building it elsewhere.

Unlike the app's small fixed-size popups, this window is resizable and
sized for charts/tables - modeled on HistogramWindow's own
(custom_titlebar=True, modal=False) combination, which is the one already
proven safe for a non-modal popup with a real title bar (see popup.py's
docstring on why chromeless + grab_set() was avoided).
"""
import os
import shutil
import tempfile
from datetime import datetime

from tkinter import ttk, filedialog, messagebox, DoubleVar, StringVar

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ui.widgets.popup import Popup
from ui.widgets.table_view import TableView
from ui.windows.export_window import ExportWindow
from db.analytics_repository import AnalyticsRepository
from services.export_service import ExportService
from config import EXPORT_DIRECTORY
from logging_setup import get_logger

logger = get_logger("ui.analytics_window")


class AnalyticsWindow(Popup):
    def __init__(self, parent, theme, analytics_repository: AnalyticsRepository, course_name: str):
        super().__init__(parent, "Analytics", theme, width=900, height=650,
                          resizable=True, custom_titlebar=True, modal=False)
        self.analytics = analytics_repository
        self.course_name = course_name
        self.export_service = ExportService()
        self._open_figures = []  # every embedded figure, closed together on window close
        # Shared between the Student Lookup tab (flags a searched student
        # if below this) and the At-Risk tab (lists everyone below this) -
        # one Popup instance, so changing it in one place is consistent.
        self._at_risk_threshold_var = DoubleVar(value=60.0)

        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        notebook = ttk.Notebook(self.content)
        notebook.grid(row=0, column=0, sticky="nsew")

        self.summaries = self.analytics.get_assessment_summaries(course_name)

        overview_tab = ttk.Frame(notebook)
        completion_tab = ttk.Frame(notebook)
        workload_tab = ttk.Frame(notebook)
        student_tab = ttk.Frame(notebook)
        at_risk_tab = ttk.Frame(notebook)
        notebook.add(overview_tab, text="Overview")
        notebook.add(completion_tab, text="Completion")
        notebook.add(workload_tab, text="Grader Workload")
        notebook.add(student_tab, text="Student Lookup")
        notebook.add(at_risk_tab, text="At-Risk")

        self._build_overview_tab(overview_tab)
        self._build_completion_tab(completion_tab)
        self._build_workload_tab(workload_tab)
        self._build_student_tab(student_tab)
        self._build_at_risk_tab(at_risk_tab)

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

    # ---- Student Lookup ----
    def _build_student_tab(self, tab):
        tab.grid_rowconfigure(1, weight=0)
        tab.grid_rowconfigure(2, weight=0)
        tab.grid_rowconfigure(4, weight=1)
        tab.grid_rowconfigure(5, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        self._all_students = self.analytics.list_students(self.course_name)
        self._student_display_values = [f"{s.sid} - {s.name}" for s in self._all_students]

        header = ttk.Frame(tab)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ttk.Label(header, text="Search (Sid or name): ").pack(side="left")
        self._student_search_var = StringVar()
        search_entry = ttk.Entry(header, textvariable=self._student_search_var, width=25)
        search_entry.pack(side="left", padx=5)
        search_entry.bind("<Return>", lambda e: self._lookup_student())
        ttk.Button(header, text="Search", command=self._lookup_student).pack(side="left", padx=5)

        ttk.Label(header, text="  or pick: ").pack(side="left")
        # Read-only, not editable: an editable Combobox whose 'values' get
        # rewritten on every keystroke (an earlier version of this) is a
        # genuinely fragile Tk pattern - backspace/arrow keys stop working
        # reliably once the value list is reassigned mid-typing. A
        # read-only Combobox has none of that risk, since there's no text
        # editing happening in it at all - only clicking or arrowing
        # through a fixed list, which is standard and reliable.
        self._student_picker = ttk.Combobox(
            header, values=self._student_display_values, state="readonly", width=28,
        )
        self._student_picker.pack(side="left", padx=5)
        self._student_picker.bind("<<ComboboxSelected>>", self._on_student_picked)

        ttk.Button(header, text="Export Report", command=self._open_student_report_export).pack(side="left", padx=(20, 0))

        self._student_info_label = ttk.Label(tab, text="Search for a student above to see their record.")
        self._student_info_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 2))

        self._student_risk_label = ttk.Label(tab, text="", style="AtRisk.TLabel")
        self._student_risk_label.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 10))

        self._student_table_frame = ttk.Frame(tab)
        self._student_table_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self._student_table_frame.grid_rowconfigure(0, weight=1)
        self._student_table_frame.grid_columnconfigure(0, weight=1)

        self._student_chart_frame = ttk.Frame(tab)
        self._student_chart_frame.grid(row=5, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # Set once a search succeeds; _open_student_report_export checks
        # these before doing anything, so "Export Report" with nothing
        # searched yet fails clearly instead of exporting stale/empty data.
        self._current_student_summary = None
        self._student_table = None

    def _on_student_picked(self, event):
        self._student_search_var.set(self._student_picker.get())
        self._lookup_student()

    def _lookup_student(self):
        raw = self._student_search_var.get().strip()
        if not raw:
            return

        # Accept "Sid - Name" (from the picker), a bare Sid typed
        # directly, or a free-text name/partial name.
        sid_part = raw.split(" - ", 1)[0].strip()
        if sid_part.isdigit():
            sid = int(sid_part)
        else:
            matches = [s for s in self._all_students if raw.lower() in s.name.lower()]
            if len(matches) == 1:
                sid = matches[0].sid
            elif len(matches) > 1:
                preview = ", ".join(f"{m.name} ({m.sid})" for m in matches[:8])
                more = "..." if len(matches) > 8 else ""
                self._student_info_label.config(
                    text=f"Multiple matches for '{raw}' - be more specific, or use the picker: {preview}{more}"
                )
                self._student_risk_label.config(text="")
                self._clear_student_results()
                return
            else:
                self._student_info_label.config(text=f"No student matching '{raw}' found on this course's roster.")
                self._student_risk_label.config(text="")
                self._clear_student_results()
                return

        summary = self.analytics.get_student_summary(self.course_name, sid)
        if summary is None:
            self._student_info_label.config(text=f"No student with Sid {sid} found on this course's roster.")
            self._student_risk_label.config(text="")
            self._clear_student_results()
            return

        self._render_student_summary(summary)

    def _clear_student_results(self):
        self._current_student_summary = None
        self._student_table = None
        for widget in self._student_table_frame.winfo_children():
            widget.destroy()
        for widget in self._student_chart_frame.winfo_children():
            widget.destroy()

    def _render_student_summary(self, summary):
        self._current_student_summary = summary

        avg_text = f"{summary.average:.2f}" if summary.average is not None else "N/A"
        self._student_info_label.config(
            text=f"{summary.name} (Sid {summary.sid}) | Overall average: {avg_text} "
                 f"| Graded on {summary.assessments_graded}/{summary.assessments_total} assessments"
        )

        threshold = self._at_risk_threshold_var.get()
        if summary.average is not None and summary.average < threshold:
            self._student_risk_label.config(
                text=f"\u26a0 At risk — average is below the {threshold:.0f}% threshold "
                     f"(see the At-Risk tab to change it)."
            )
        else:
            self._student_risk_label.config(text="")

        for widget in self._student_table_frame.winfo_children():
            widget.destroy()
        table = TableView(self._student_table_frame)
        table.frame.grid(row=0, column=0, sticky="nsew")
        self._student_table = table

        def fmt(value, suffix=""):
            return f"{value:.2f}{suffix}" if isinstance(value, (int, float)) else "-"

        rows = []
        for r in summary.records:
            delta = r.vs_class_average
            delta_text = "N/A" if delta is None else (f"+{delta:.2f}" if delta >= 0 else f"{delta:.2f}")
            rows.append([
                r.table_suffix, fmt(r.score), fmt(r.calculated), r.comment,
                r.grader_name, r.updated_at or "-", delta_text,
            ])
        table.render(["Assessment", "Score", "Calculated", "Comment", "Grader", "Last Modified", "Vs Class Avg"], rows)

        self._render_student_chart(summary)

    def _render_student_chart(self, summary):
        for widget in self._student_chart_frame.winfo_children():
            widget.destroy()

        fig = self._build_student_progress_figure(summary)
        if fig is None:
            ttk.Label(self._student_chart_frame, text="No numeric scores to chart yet.").grid(row=0, column=0)
            return

        self._embed_chart(self._student_chart_frame, fig, f"{summary.sid}_{summary.name}_progress".replace(" ", "_"))

    def _build_student_progress_figure(self, summary):
        """Builds (but doesn't embed) the student's progress-vs-class-
        average figure. Split out from _render_student_chart so the exact
        same chart can also be saved to a temp image and embedded in the
        PDF report (_generate_student_report_pdf) without duplicating the
        plotting logic. Returns None if there's nothing numeric to plot."""
        plotted = [r for r in summary.records if r.normalized is not None]
        if not plotted:
            return None

        # Chronological order (by when each was graded) reads as an actual
        # progress timeline; records with no timestamp (pre-dating the
        # UpdatedAt column) sort to the end rather than breaking the sort.
        plotted.sort(key=lambda r: (r.updated_at is None, r.updated_at))

        labels = [r.table_suffix for r in plotted]
        student_values = [r.normalized for r in plotted]
        has_class_data = any(r.class_normalized_average is not None for r in plotted)
        # NaN, not None: matplotlib's plot() expects numeric data and
        # handles NaN by breaking the line at that point, but chokes on a
        # raw None mixed into an otherwise-numeric list.
        class_values = [
            r.class_normalized_average if r.class_normalized_average is not None else float("nan")
            for r in plotted
        ]

        fig, ax = self._new_figure()
        x = range(len(labels))
        ax.plot(x, student_values, marker="o", color=self.theme.PURPLE, label=summary.name)
        if has_class_data:
            ax.plot(x, class_values, marker="o", linestyle="--", color=self.theme.FG, alpha=0.6, label="Class Average")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, color=self.theme.FG)
        if len(labels) > 4:
            ax.tick_params(axis="x", rotation=30)
        ax.set_ylabel("Normalized Score", color=self.theme.FG)
        ax.set_title(f"{summary.name} - Progress vs. Class Average", color=self.theme.FG)
        legend = ax.legend(facecolor=self.theme.CARD, edgecolor=self.theme.BORDER)
        for text in legend.get_texts():
            text.set_color(self.theme.FG)
        return fig

    # ---- Student report export ----
    def _open_student_report_export(self):
        if not self._current_student_summary:
            messagebox.showinfo("No Student Selected", "Search for a student first.")
            return
        ExportWindow(self, self.theme, self._on_student_report_export_chosen, course_name=self.course_name)

    def _on_student_report_export_chosen(self, format_key: str, folder: str):
        summary = self._current_student_summary
        base_name = f"{summary.sid}_{summary.name}_report".replace(" ", "_")

        def do_csv():
            return self._student_table.export_csv(base_name=base_name, directory=folder)

        def do_excel():
            return self._student_table.export_excel(base_name=base_name, directory=folder)

        def do_pdf_report():
            return self._generate_student_report_pdf(summary, folder, base_name)

        # The PDF option is always the full report (title, summary info,
        # embedded progress chart, then the table) rather than the plain
        # bordered-table dump TableView.export_pdf would otherwise give -
        # that's the whole point of "report" over a raw export.
        exporters = {
            "csv": [("CSV", do_csv)],
            "excel": [("Excel", do_excel)],
            "pdf": [("PDF Report", do_pdf_report)],
            "all": [("CSV", do_csv), ("Excel", do_excel), ("PDF Report", do_pdf_report)],
        }.get(format_key, [])

        written, errors = [], []
        for label, export_fn in exporters:
            try:
                path = export_fn()
                written.append(f"{label}: {path}")
            except Exception as e:
                logger.exception("%s export failed for student report (sid=%s)", label, summary.sid)
                errors.append(f"{label}: {e}")

        if written:
            messagebox.showinfo("Export Complete", "Saved:\n\n" + "\n".join(written))
        if errors:
            messagebox.showerror("Some Exports Failed", "\n".join(errors))

    def _generate_student_report_pdf(self, summary, folder: str, base_name: str) -> str:
        """Builds the actual report PDF: renders the same progress chart
        shown on-screen to a temp PNG (cleaned up afterward), then hands
        everything to ExportService.export_report_pdf for layout."""
        fig = self._build_student_progress_figure(summary)
        chart_path = None
        tmp_dir = None
        if fig is not None:
            tmp_dir = tempfile.mkdtemp(prefix="ta_app_report_")
            chart_path = os.path.join(tmp_dir, "chart.png")
            fig.savefig(chart_path, facecolor=fig.get_facecolor(), bbox_inches="tight", dpi=150)
            plt.close(fig)  # this figure is never embedded on-screen, so it isn't in self._open_figures

        try:
            avg_text = f"{summary.average:.2f}%" if summary.average is not None else "N/A"
            threshold = self._at_risk_threshold_var.get()
            info_lines = [
                f"Course: {self.course_name}",
                f"Student: {summary.name}    Sid: {summary.sid}",
                f"Overall Average (normalized): {avg_text}",
                f"Assessments Graded: {summary.assessments_graded}/{summary.assessments_total}",
                f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            ]
            if summary.average is not None and summary.average < threshold:
                info_lines.append(f"** Flagged At-Risk (below {threshold:.0f}% threshold) **")

            def fmt(value):
                return f"{value:.2f}" if isinstance(value, (int, float)) else "-"

            columns = ["Assessment", "Score", "Calculated", "Comment", "Grader", "Last Modified", "Vs Class Avg"]
            rows = []
            for r in summary.records:
                delta = r.vs_class_average
                delta_text = "N/A" if delta is None else (f"+{delta:.2f}" if delta >= 0 else f"{delta:.2f}")
                rows.append([r.table_suffix, fmt(r.score), fmt(r.calculated), r.comment,
                             r.grader_name, r.updated_at or "-", delta_text])

            return self.export_service.export_report_pdf(
                title=f"Student Report - {summary.name}",
                info_lines=info_lines, columns=columns, rows=rows,
                chart_image_path=chart_path, base_name=base_name, directory=folder,
            )
        finally:
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)

    # ---- At-Risk ----
    def _build_at_risk_tab(self, tab):
        tab.grid_rowconfigure(2, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        header = ttk.Frame(tab)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ttk.Label(header, text="Flag students below (%): ").pack(side="left")
        ttk.Spinbox(
            header, from_=0, to=100, increment=5, width=6,
            textvariable=self._at_risk_threshold_var,
        ).pack(side="left", padx=5)
        ttk.Button(header, text="Apply", command=self._render_at_risk_list).pack(side="left", padx=5)
        ttk.Button(header, text="Export List", command=self._open_at_risk_export).pack(side="left", padx=(20, 0))

        self._at_risk_info_label = ttk.Label(tab, text="")
        self._at_risk_info_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 5))

        self._at_risk_table_frame = ttk.Frame(tab)
        self._at_risk_table_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self._at_risk_table = None
        self._render_at_risk_list()

    def _render_at_risk_list(self):
        threshold = self._at_risk_threshold_var.get()
        at_risk = self.analytics.get_at_risk_students(self.course_name, threshold)

        for widget in self._at_risk_table_frame.winfo_children():
            widget.destroy()
        self._at_risk_table_frame.grid_rowconfigure(0, weight=1)
        self._at_risk_table_frame.grid_columnconfigure(0, weight=1)

        self._at_risk_table = TableView(self._at_risk_table_frame)
        self._at_risk_table.frame.grid(row=0, column=0, sticky="nsew")
        rows = [
            [s.sid, s.name, f"{s.average:.2f}" if s.average is not None else "-",
             f"{s.assessments_graded}/{s.assessments_total}"]
            for s in at_risk
        ]
        self._at_risk_table.render(["Sid", "Name", "Average", "Graded"], rows)

        self._at_risk_info_label.config(
            text=f"{len(at_risk)} student(s) below {threshold:.0f}% "
                 f"(students with no graded assessments yet aren't included)"
        )

    def _open_at_risk_export(self):
        if not self._at_risk_table or not self._at_risk_table.tree or not self._at_risk_table.tree.get_children():
            messagebox.showinfo("Nothing to Export", "No at-risk students to export.")
            return
        ExportWindow(self, self.theme, self._on_at_risk_export_chosen, course_name=self.course_name)

    def _on_at_risk_export_chosen(self, format_key: str, folder: str):
        base_name = f"{self.course_name}_at_risk"
        exporters = {
            "csv": [("CSV", self._at_risk_table.export_csv)],
            "excel": [("Excel", self._at_risk_table.export_excel)],
            "pdf": [("PDF", self._at_risk_table.export_pdf)],
            "all": [
                ("CSV", self._at_risk_table.export_csv),
                ("Excel", self._at_risk_table.export_excel),
                ("PDF", self._at_risk_table.export_pdf),
            ],
        }.get(format_key, [])

        written, errors = [], []
        for label, export_fn in exporters:
            try:
                path = export_fn(base_name=base_name, directory=folder)
                written.append(f"{label}: {path}")
            except Exception as e:
                logger.exception("%s export failed for at-risk list", label)
                errors.append(f"{label}: {e}")

        if written:
            messagebox.showinfo("Export Complete", "Saved:\n\n" + "\n".join(written))
        if errors:
            messagebox.showerror("Some Exports Failed", "\n".join(errors))

    def close(self):
        for fig in self._open_figures:
            plt.close(fig)
        super().close()