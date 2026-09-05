"""
Two-step popup flow for choosing/creating a course: course name, then which
roster file to import students from.

Extracted from TAapp.py's openCourseWindow()/openFilenameWindow(). Key
behavior change: instead of letting the user type an arbitrary filename
that then gets guessed-at as a path (the root of the original roster/export
mixup), this now lists the actual files available in
config.ROSTER_DIRECTORY via RosterImportService, with a manual-entry
fallback for anyone who wants to type a name that doesn't exist yet.
"""
from tkinter import StringVar
from tkinter import ttk

from ui.widgets.popup import Popup
from services.roster_import_service import RosterImportService, SUPPORTED_EXTENSIONS


class CourseNameStep(Popup):
    def __init__(self, parent, theme, on_next):
        """on_next: callable(course_name: str) -> None"""
        super().__init__(parent, "Enter Course Name", theme, width=300, height=200, custom_titlebar=False)
        self.on_next = on_next
        self.content.grid_columnconfigure(0, weight=1)

        ttk.Label(self.content, text="Enter Course: ").grid(row=0, column=0, pady=10)
        self._course_var = StringVar()
        entry = ttk.Entry(self.content, textvariable=self._course_var, width=30)
        entry.grid(row=1, column=0, pady=5, padx=10)
        entry.focus_set()

        submit_btn = ttk.Button(self.content, text="Submit", command=self._submit, width=10)
        submit_btn.grid(row=2, column=0, pady=10)
        self.bind("<Return>", lambda e=None: submit_btn.invoke())
        self.center_over_parent()

    def _submit(self):
        course_name = self._course_var.get().upper().strip()
        if not course_name:
            self.notify("warning", "Input Error", "Please enter a course name.")
            return
        self.destroy()
        self.on_next(course_name)


class RosterSelectStep(Popup):
    def __init__(self, parent, theme, course_name: str, on_complete,
                 roster_service: RosterImportService = None):
        """on_complete: callable(course_name: str, roster_filename: str) -> None"""
        super().__init__(parent, "Select Roster", theme, width=320, height=220, custom_titlebar=False)
        self.on_complete = on_complete
        self.course_name = course_name
        self.roster_service = roster_service or RosterImportService()
        self.content.grid_columnconfigure(0, weight=1)

        self.notify("info", "Confirmation", f"Course : {course_name}")

        ttk.Label(self.content, text="Choose a roster file: ").grid(row=0, column=0, pady=(10, 2))
        available = self.roster_service.list_rosters()
        self._filename_var = StringVar()

        if available:
            combo = ttk.Combobox(self.content, textvariable=self._filename_var,
                                  values=available, width=27, state="readonly")
            combo.grid(row=1, column=0, pady=5, padx=10)
            combo.current(0)
        else:
            ttk.Label(self.content, text="(no rosters found in data/rosters)").grid(row=1, column=0)

        formats = "/".join(ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS)
        ttk.Label(self.content, text=f"Or type a filename ({formats}): ").grid(row=2, column=0, pady=(10, 2))
        entry = ttk.Entry(self.content, textvariable=self._filename_var, width=30)
        entry.grid(row=3, column=0, pady=5, padx=10)

        submit_btn = ttk.Button(self.content, text="Submit", command=self._submit, width=10)
        submit_btn.grid(row=4, column=0, pady=10)
        self.bind("<Return>", lambda e=None: submit_btn.invoke())
        self.center_over_parent()

    def _submit(self):
        filename = self._filename_var.get().strip()
        if not filename:
            self.notify("warning", "Input Error", "Please enter a file name.")
            return
        if not filename.lower().endswith(SUPPORTED_EXTENSIONS):
            formats = ", ".join(SUPPORTED_EXTENSIONS)
            self.notify(
                "warning", "Unsupported File Type",
                f"Roster file must end in one of: {formats}",
            )
            return
        self.destroy()
        self.on_complete(self.course_name, filename)


def start_course_setup(parent, theme, on_complete, roster_service: RosterImportService = None):
    """Convenience entry point: chains CourseNameStep -> RosterSelectStep."""
    def after_course_name(course_name):
        RosterSelectStep(parent, theme, course_name, on_complete, roster_service)

    CourseNameStep(parent, theme, after_course_name)