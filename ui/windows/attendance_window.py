"""
Attendance popup: create named sessions (e.g. "Session 1 - Asymptotic
Notations & Quiz 1 prep") and tick off which roster students were
present. See db/attendance_repository.py's module docstring for how this
is stored - presence is a row existing, absence is no row, same "row
exists = recorded" convention the rest of the app already uses for
grades.

Each checkbox commits immediately (mark_present/mark_absent) rather than
needing a separate Save button - this matches how the rest of the app
already works (a theme change, a grader switch, a grade entry all commit
right away), and avoids the risk of a TA closing this window mid-session
and losing a batch of unsaved ticks.

The checklist uses the same scrollable-canvas pattern as
ui/windows/shortcuts_window.py (ttk has no built-in scrollable frame).
"""
import tkinter as tk
from tkinter import ttk, messagebox, StringVar

from ui.widgets.popup import Popup
from ui.widgets.table_view import TableView
from ui.windows.export_window import ExportWindow
from db.attendance_repository import AttendanceRepository
from logging_setup import get_logger

logger = get_logger("ui.attendance_window")


class AttendanceWindow(Popup):
    def __init__(self, parent, theme, attendance_repository: AttendanceRepository,
                 students, course_name: str, current_ta_id):
        """students: List[Student] (db.models.Student) - the full roster,
        passed in rather than queried here so this window doesn't need a
        second repository dependency (matches AnalyticsWindow's
        list_students passthrough pattern)."""
        super().__init__(parent, "Attendance", theme, width=560, height=620,
                          resizable=True, custom_titlebar=True, modal=False)
        self.attendance = attendance_repository
        self.students = sorted(students, key=lambda s: s.name.lower())
        self.course_name = course_name
        self.current_ta_id = current_ta_id

        self.current_session_id = None
        self.present_sids = set()
        self._row_widgets = []  # (student, checkbutton, var) for filtering
        self._sessions = []

        self.content.grid_rowconfigure(4, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self._build_session_controls()
        self._build_checklist_area()

        self.center_over_parent()
        self._refresh_session_list()

    # ---- session creation / selection ----
    def _build_session_controls(self):
        new_row = ttk.Frame(self.content)
        new_row.grid(row=0, column=0, sticky="ew", padx=5, pady=(0, 5))
        new_row.grid_columnconfigure(0, weight=1)
        ttk.Label(new_row, text="New session name:").grid(row=0, column=0, sticky="w")
        self._new_session_var = StringVar()
        new_entry = ttk.Entry(new_row, textvariable=self._new_session_var, justify="center")
        new_entry.grid(row=1, column=0, sticky="ew", pady=(2, 0), padx=(0, 5))
        new_entry.bind("<Return>", lambda e: self._create_session())
        ttk.Button(new_row, text="Create Session", command=self._create_session).grid(row=1, column=1)

        pick_row = ttk.Frame(self.content)
        pick_row.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        pick_row.grid_columnconfigure(0, weight=1)
        ttk.Label(pick_row, text="Existing session:").grid(row=0, column=0, sticky="w")
        self._session_picker = ttk.Combobox(pick_row, state="readonly")
        self._session_picker.grid(row=1, column=0, sticky="ew", padx=(0, 5))
        self._session_picker.bind("<<ComboboxSelected>>", lambda e: self._load_selected_session())
        ttk.Button(pick_row, text="Export List", command=self._open_export).grid(row=1, column=1)

        self._summary_label = ttk.Label(self.content, text="Create or pick a session above to begin.")
        self._summary_label.grid(row=2, column=0, sticky="w", padx=5, pady=(5, 5))

    def _refresh_session_list(self, select_session_id=None):
        self._sessions = self.attendance.list_sessions(self.course_name)
        labels = [f"{s.session_id} - {s.name}" for s in self._sessions]
        self._session_picker["values"] = labels
        if select_session_id is not None:
            for label, s in zip(labels, self._sessions):
                if s.session_id == select_session_id:
                    self._session_picker.set(label)
                    break
            self._load_selected_session()

    def _create_session(self):
        name = self._new_session_var.get().strip()
        if not name:
            messagebox.showwarning("Input Error", "Please enter a session name.")
            return
        session_id = self.attendance.create_session(self.course_name, name, self.current_ta_id)
        self._new_session_var.set("")
        self._refresh_session_list(select_session_id=session_id)

    def _load_selected_session(self):
        label = self._session_picker.get()
        if not label:
            return
        session_id = int(label.split(" - ", 1)[0])
        self.current_session_id = session_id
        self.present_sids = self.attendance.get_present_sids(self.course_name, session_id)
        self._render_checklist()
        self._update_summary()

    def _update_summary(self):
        session = next((s for s in self._sessions if s.session_id == self.current_session_id), None)
        session_name = session.name if session else ""
        self._summary_label.config(
            text=f"'{session_name}' - Present: {len(self.present_sids)}/{len(self.students)}"
        )

    # ---- checklist ----
    def _build_checklist_area(self):
        search_row = ttk.Frame(self.content)
        search_row.grid(row=3, column=0, sticky="ew", padx=5)
        search_row.grid_columnconfigure(1, weight=1)
        ttk.Label(search_row, text="Filter: ").grid(row=0, column=0, sticky="w")
        self._filter_var = StringVar()
        filter_entry = ttk.Entry(search_row, textvariable=self._filter_var)
        filter_entry.grid(row=0, column=1, sticky="ew", padx=5)
        filter_entry.bind("<KeyRelease>", lambda e: self._apply_filter())

        list_container = ttk.Frame(self.content)
        list_container.grid(row=4, column=0, sticky="nsew", padx=5, pady=(5, 5))
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(list_container, bg=self.theme.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._list_frame = ttk.Frame(canvas)
        self._list_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=self._list_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(canvas_window, width=e.width))

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    def _render_checklist(self):
        for widget in self._list_frame.winfo_children():
            widget.destroy()
        self._row_widgets = []

        for index, student in enumerate(self.students):
            var = tk.BooleanVar(value=student.sid in self.present_sids)
            check = ttk.Checkbutton(
                self._list_frame, text=f"{student.name}  ({student.sid})",
                variable=var, command=lambda s=student, v=var: self._toggle(s, v),
            )
            check.grid(row=index, column=0, sticky="w", padx=5, pady=2)
            self._row_widgets.append((student, check, var))

        self._apply_filter()

    def _apply_filter(self):
        query = self._filter_var.get().strip().lower()
        for student, check, _ in self._row_widgets:
            visible = not query or query in student.name.lower() or query in str(student.sid)
            if visible:
                check.grid()
            else:
                check.grid_remove()

    def _toggle(self, student, var: "tk.BooleanVar"):
        if self.current_session_id is None:
            return
        if var.get():
            self.attendance.mark_present(self.course_name, self.current_session_id, student.sid, self.current_ta_id)
            self.present_sids.add(student.sid)
        else:
            self.attendance.mark_absent(self.course_name, self.current_session_id, student.sid)
            self.present_sids.discard(student.sid)
        self._update_summary()

    # ---- export ----
    def _open_export(self):
        if self.current_session_id is None:
            messagebox.showinfo("No Session Selected", "Create or pick a session first.")
            return
        ExportWindow(self, self.theme, self._on_export_chosen, course_name=self.course_name)

    def _on_export_chosen(self, format_key: str, folder: str):
        session = next((s for s in self._sessions if s.session_id == self.current_session_id), None)
        session_label = session.name if session else str(self.current_session_id)
        base_name = f"attendance_{session_label}".replace(" ", "_")

        table = TableView(self)  # not displayed - only used to reuse its export methods
        rows = [
            [student.sid, student.name, "Present" if student.sid in self.present_sids else "Absent"]
            for student in self.students
        ]
        table.render(["Sid", "Name", "Status"], rows)

        exporters = {
            "csv": [("CSV", table.export_csv)],
            "excel": [("Excel", table.export_excel)],
            "pdf": [("PDF", table.export_pdf)],
            "all": [("CSV", table.export_csv), ("Excel", table.export_excel), ("PDF", table.export_pdf)],
        }.get(format_key, [])

        written, errors = [], []
        for label, export_fn in exporters:
            try:
                path = export_fn(base_name=base_name, directory=folder)
                written.append(f"{label}: {path}")
            except Exception as e:
                logger.exception("%s export failed for attendance list", label)
                errors.append(f"{label}: {e}")

        if written:
            messagebox.showinfo("Export Complete", "Saved:\n\n" + "\n".join(written))
        if errors:
            messagebox.showerror("Some Exports Failed", "\n".join(errors))