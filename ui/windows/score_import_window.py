"""
Popup for bulk-importing scores into an existing assessment table from a
CSV/Excel file - e.g. one exported by another TA, or by an autograder.

Modeled on ui/windows/course_setup_window.py's RosterSelectStep: lists
files found in config.SCORE_IMPORT_DIRECTORY via ScoreImportService, with
a manual-entry fallback. Unlike roster import (which only ever creates
new student rows), a score import writes into a specific, already-created
assessment table, so this window also asks which table to import into.

This window only parses the file and hands the result back via
on_complete - it does not touch the database itself. Resolving grader
names to TaIds and calling AssessmentRepository.bulk_upsert is the
caller's (MainWindow's) job, same division of responsibility as
CommentWindow/UpdateWindow.
"""
from tkinter import StringVar
from tkinter import ttk

from ui.widgets.popup import Popup
from services.score_import_service import ScoreImportService, ScoreImportError, SUPPORTED_EXTENSIONS


class ScoreImportWindow(Popup):
    def __init__(self, parent, theme, on_complete, score_import_service: ScoreImportService = None):
        """on_complete: callable(table_suffix: str, rows: List[ScoreImportRow]) -> None"""
        super().__init__(parent, "Bulk Import Scores", theme, width=420, height=340, custom_titlebar=False)
        self.on_complete = on_complete
        self.score_import_service = score_import_service or ScoreImportService()
        self.content.grid_columnconfigure(0, weight=1)

        ttk.Label(self.content, text="Assessment table to import into (e.g. Quiz1): ", wraplength=380).grid(
            row=0, column=0, pady=(10, 2), sticky="w"
        )
        self._table_var = StringVar()
        table_entry = ttk.Entry(self.content, textvariable=self._table_var, width=35)
        table_entry.grid(row=1, column=0, pady=5, padx=10, sticky="w")
        table_entry.focus_set()

        ttk.Label(self.content, text="Choose a score file: ", wraplength=380).grid(row=2, column=0, pady=(10, 2), sticky="w")
        available = self.score_import_service.list_score_files()
        self._filename_var = StringVar()

        if available:
            combo = ttk.Combobox(self.content, textvariable=self._filename_var,
                                  values=available, width=32, state="readonly")
            combo.grid(row=3, column=0, pady=5, padx=10, sticky="w")
            combo.current(0)
        else:
            ttk.Label(self.content, text="(no files found in data/score_imports)", wraplength=380).grid(
                row=3, column=0, padx=10, sticky="w"
            )

        formats = "/".join(ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS)
        ttk.Label(self.content, text=f"Or type a filename ({formats}): ", wraplength=380).grid(
            row=4, column=0, pady=(10, 2), sticky="w"
        )
        entry = ttk.Entry(self.content, textvariable=self._filename_var, width=35)
        entry.grid(row=5, column=0, pady=5, padx=10, sticky="w")

        submit_btn = ttk.Button(self.content, text="Import", command=self._submit, width=12)
        submit_btn.grid(row=6, column=0, pady=15)
        self.bind("<Return>", lambda e=None: submit_btn.invoke())
        self.center_over_parent()

    def _submit(self):
        table_suffix = self._table_var.get().strip()
        filename = self._filename_var.get().strip()

        if not table_suffix:
            self.notify("warning", "Input Error", "Please enter which assessment table to import into.")
            return
        if not filename:
            self.notify("warning", "Input Error", "Please choose or type a file name.")
            return
        if not filename.lower().endswith(SUPPORTED_EXTENSIONS):
            formats = ", ".join(SUPPORTED_EXTENSIONS)
            self.notify("warning", "Unsupported File Type", f"Score file must end in one of: {formats}")
            return

        try:
            rows = self.score_import_service.parse_score_file(filename)
        except ScoreImportError as e:
            self.notify("error", "Import Error", str(e))
            return

        if not rows:
            self.notify("warning", "No Data", f"No valid score rows found in '{filename}'.")
            return

        self.destroy()
        self.on_complete(table_suffix, rows)