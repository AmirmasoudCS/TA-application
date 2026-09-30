"""
Sync popup: exchange grade data between TAs' separate local databases
without a shared server or live network connection. See
services/sync_service.py's module docstring for the full merge design and
its honest limitations (especially: deletions never propagate).

Two tabs (a ttk.Notebook, same pattern as AnalyticsWindow):
  Sync Out - writes the current course's roster and every graded score to
             a single JSON file, for the TA to place wherever their group
             actually shares files (Dropbox, USB, email, etc.).
  Sync In  - scans a folder for other TAs' sync files for this course,
             shows what's in each one before committing to anything, then
             merges them into the local database (last-write-wins by
             UpdatedAt - see SyncService.import_file/_incoming_is_newer).
"""
import os

from tkinter import ttk, filedialog, messagebox, StringVar

from ui.widgets.popup import Popup
from ui.widgets.table_view import TableView
from services.sync_service import SyncService
from config import SYNC_DIRECTORY
from logging_setup import get_logger

logger = get_logger("ui.sync_window")


class SyncWindow(Popup):
    def __init__(self, parent, theme, sync_service: SyncService, course_name: str, current_ta_name: str):
        super().__init__(parent, "Sync", theme, width=720, height=520,
                          resizable=True, custom_titlebar=True, modal=False)
        self.sync_service = sync_service
        self.course_name = course_name
        self.current_ta_name = current_ta_name
        self._found_files = []

        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        notebook = ttk.Notebook(self.content)
        notebook.grid(row=0, column=0, sticky="nsew")

        out_tab = ttk.Frame(notebook)
        in_tab = ttk.Frame(notebook)
        notebook.add(out_tab, text="Sync Out")
        notebook.add(in_tab, text="Sync In")

        self._build_out_tab(out_tab)
        self._build_in_tab(in_tab)

        self.center_over_parent()

    # ---- Sync Out ----
    def _build_out_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)

        ttk.Label(
            tab,
            text=f"Export everything you have for '{self.course_name}' - roster and every "
                 f"graded score - to a file you can share with other TAs.",
            wraplength=640, justify="left",
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 15))

        ttk.Label(tab, text="Save to folder:").grid(row=1, column=0, sticky="w", padx=15)
        folder_row = ttk.Frame(tab)
        folder_row.grid(row=2, column=0, sticky="ew", padx=15, pady=5)
        folder_row.grid_columnconfigure(0, weight=1)
        self._out_folder_var = StringVar(value=SYNC_DIRECTORY)
        ttk.Entry(folder_row, textvariable=self._out_folder_var, justify="center").grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ttk.Button(folder_row, text="Browse...", command=self._browse_out_folder).grid(row=0, column=1)

        ttk.Button(tab, text="Export My Data", command=self._do_sync_out).grid(row=3, column=0, pady=20)

        self._out_status_label = ttk.Label(tab, text="", wraplength=640, justify="left")
        self._out_status_label.grid(row=4, column=0, sticky="w", padx=15)

    def _browse_out_folder(self):
        chosen = filedialog.askdirectory(
            initialdir=self._out_folder_var.get() or SYNC_DIRECTORY, title="Choose sync folder"
        )
        if chosen:
            self._out_folder_var.set(chosen)

    def _do_sync_out(self):
        folder = self._out_folder_var.get().strip()
        if not folder:
            messagebox.showwarning("Input Error", "Please choose a folder.")
            return
        try:
            filepath = self.sync_service.export_course(self.course_name, self.current_ta_name, directory=folder)
        except Exception as e:
            logger.exception("Sync Out failed")
            messagebox.showerror("Sync Out Failed", str(e))
            return
        self._out_status_label.config(
            text=f"Exported to:\n{filepath}\n\nShare this file (or the whole folder) with the other TAs."
        )

    # ---- Sync In ----
    def _build_in_tab(self, tab):
        tab.grid_rowconfigure(3, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        ttk.Label(
            tab,
            text="Scan a folder for other TAs' sync files for this course, review what's in "
                 "them, then merge everything into your local data. Newer scores (by when "
                 "they were entered) automatically win over older ones - see the app's notes "
                 "on sync for the exact rule.",
            wraplength=640, justify="left",
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 15))

        ttk.Label(tab, text="Import from folder:").grid(row=1, column=0, sticky="w", padx=15)
        folder_row = ttk.Frame(tab)
        folder_row.grid(row=2, column=0, sticky="ew", padx=15, pady=5)
        folder_row.grid_columnconfigure(0, weight=1)
        self._in_folder_var = StringVar(value=SYNC_DIRECTORY)
        ttk.Entry(folder_row, textvariable=self._in_folder_var, justify="center").grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ttk.Button(folder_row, text="Browse...", command=self._browse_in_folder).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(folder_row, text="Scan", command=self._scan_sync_files).grid(row=0, column=2)

        self._sync_files_frame = ttk.Frame(tab)
        self._sync_files_frame.grid(row=3, column=0, sticky="nsew", padx=15, pady=10)
        self._sync_files_frame.grid_rowconfigure(0, weight=1)
        self._sync_files_frame.grid_columnconfigure(0, weight=1)

        ttk.Button(tab, text="Import All Listed Files", command=self._do_sync_in).grid(row=4, column=0, pady=(0, 10))

        self._in_status_label = ttk.Label(tab, text="", wraplength=640, justify="left")
        self._in_status_label.grid(row=5, column=0, sticky="w", padx=15, pady=(0, 15))

    def _browse_in_folder(self):
        chosen = filedialog.askdirectory(
            initialdir=self._in_folder_var.get() or SYNC_DIRECTORY, title="Choose sync folder"
        )
        if chosen:
            self._in_folder_var.set(chosen)

    def _scan_sync_files(self):
        folder = self._in_folder_var.get().strip() or SYNC_DIRECTORY
        for widget in self._sync_files_frame.winfo_children():
            widget.destroy()

        self._found_files = self.sync_service.list_sync_files(self.course_name, directory=folder)

        table = TableView(self._sync_files_frame)
        table.frame.grid(row=0, column=0, sticky="nsew")
        rows = [
            [f.exported_by, f.exported_at, f.student_count, f.assessment_count, os.path.basename(f.filepath)]
            for f in self._found_files
        ]
        table.render(["Exported By", "Exported At", "Students", "Assessments", "File"], rows)

        if not self._found_files:
            self._in_status_label.config(text=f"No sync files for '{self.course_name}' found in that folder.")
        else:
            self._in_status_label.config(
                text=f"Found {len(self._found_files)} file(s). Review above, then click Import."
            )

    def _do_sync_in(self):
        if not self._found_files:
            messagebox.showinfo("Nothing to Import", "Scan a folder first.")
            return
        if not self.confirm(
            "Confirm Import",
            f"This will merge {len(self._found_files)} file(s) into your local data for "
            f"'{self.course_name}'. Newer scores automatically win over older ones. This "
            f"cannot bring back a score someone deleted elsewhere - only adds and updates "
            f"are synced. Continue?",
        ):
            return

        applied = skipped = students_added = assessments_created = 0
        errors = []
        for info in self._found_files:
            result = self.sync_service.import_file(info.filepath)
            applied += result.applied
            skipped += result.skipped_older
            students_added += result.students_added
            assessments_created += result.assessments_created
            errors.extend(result.errors)

        summary = (
            f"Applied {applied} score update(s); skipped {skipped} "
            f"(your local version was already newer or the same).\n"
            f"Added {students_added} new student(s); created {assessments_created} new assessment table(s)."
        )
        if errors:
            summary += f"\n\n{len(errors)} error(s) occurred - check logs/taapp.log for details."
        self._in_status_label.config(text=summary)
        messagebox.showinfo("Sync In Complete", summary)