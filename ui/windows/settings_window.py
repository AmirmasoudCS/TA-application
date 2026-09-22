"""
Settings popup: theme picker + "change course" form + "change grader" form.

Extracted from TAapp.py's openSettingsMenu(). Theme switching, course
changes, and grader changes are all delegated to callbacks so this window
has no direct dependency on Database or the rest of the app's globals -
except for TARepository, which it needs directly to list/rename TAs for
the grader section (same trusted-team, no-auth model as
db/ta_repository.py's docstring explains).
"""
from tkinter import StringVar
from tkinter import ttk

from ui.widgets.popup import Popup
from db.ta_repository import TARepository

_THEME_LABELS = [
    ("default", "Default (Purple)"),
    ("dark", "Dark"),
    ("blue", "Blue"),
    ("green", "Green"),
    ("red", "Red"),
    ("yellow", "Yellow"),
    ("pink", "Pink"),
    ("jigari", "Jigari"),
]


class SettingsWindow(Popup):
    def __init__(self, parent, theme, on_theme_change, on_change_course,
                 ta_repository: TARepository = None, current_ta_name: str = None,
                 on_ta_changed=None):
        """
        on_theme_change: callable(theme_name: str) -> None
        on_change_course: callable(course_name: str, filename: str) -> None
        ta_repository: needed to list/rename TAs for the grader section.
            If omitted, the grader section is skipped.
        current_ta_name: shown as the currently active grader.
        on_ta_changed: callable(ta_id: int, ta_name: str) -> None, called
            when the user switches to a different TA.
        """
        super().__init__(parent, "Settings", theme, custom_titlebar=True)
        self.on_theme_change = on_theme_change
        self.on_change_course = on_change_course
        self.ta_repository = ta_repository
        self.current_ta_name = current_ta_name
        self.on_ta_changed = on_ta_changed

        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_columnconfigure(1, weight=1)
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))

        self._build_theme_section()
        self._build_course_section()
        if self.ta_repository is not None:
            self._build_grader_section()

        ttk.Button(self.content, text="Close Settings", command=self.close).grid(
            row=7, column=0, columnspan=2, padx=5, pady=5
        )

        self.center_over_parent()
        try:
            parent.attributes("-disabled", True)
        except Exception:
            pass

    def _build_theme_section(self):
        theme_frame = ttk.LabelFrame(
            self.content, text="Theme Color", padding=5, style="Settings.TLabelframe"
        )
        theme_frame.grid(padx=10, pady=10, row=0, column=0, columnspan=2)
        theme_frame.columnconfigure(0, weight=1)
        theme_frame.columnconfigure(1, weight=1)

        for index, (theme_key, label) in enumerate(_THEME_LABELS):
            row, col = divmod(index, 2)
            btn = ttk.Button(
                theme_frame, text=label,
                command=lambda k=theme_key: self.on_theme_change(k),
            )
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")

    def _build_course_section(self):
        course_frame = ttk.LabelFrame(
            self.content, text="Change Course", padding=10, style="Settings.TLabelframe"
        )
        course_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        ttk.Label(course_frame, text="Enter new course name: ").grid(row=0, column=0, sticky="w", pady=3)
        new_course_var = StringVar()
        course_entry = ttk.Entry(course_frame, textvariable=new_course_var, width=30)
        course_entry.grid(row=1, column=0, pady=3)

        ttk.Label(course_frame, text="Enter filename: ").grid(row=2, column=0, sticky="w", pady=3)
        new_filename_var = StringVar()
        filename_entry = ttk.Entry(course_frame, textvariable=new_filename_var, width=30)
        filename_entry.grid(row=3, column=0, pady=3)

        course_entry.bind("<Return>", lambda e=None: filename_entry.focus_set())

        def apply_new_course():
            name = new_course_var.get().upper()
            filename = new_filename_var.get().upper()
            if not name or not filename:
                self.notify("warning", "Missing Input", "Please fill both course name and filename.")
                return
            self.destroy()
            self.on_change_course(name, filename)

        apply_btn = ttk.Button(course_frame, text="Apply New Course", command=apply_new_course)
        apply_btn.grid(row=4, column=0, columnspan=2, pady=10)
        filename_entry.bind("<Return>", lambda e=None: apply_btn.invoke())

    def _build_grader_section(self):
        """Lets a TA switch to a different existing grader (e.g. sharing a
        lab machine), add a brand new one, or rename an existing entry
        (e.g. fixing a misspelled name) without losing that TA's history -
        renaming keeps the same TaId, so past GraderId references still
        resolve to the corrected name.

        Feedback here is an inline label, not self.notify()'s messagebox.
        This window disables the main root while open (see __init__), and
        stacking a second modal dialog on top of that disabled root is the
        same class of Tk/Windows freeze popup.py's docstring already warns
        about elsewhere in this app - so this section avoids it entirely
        instead of fighting it.
        """
        grader_frame = ttk.LabelFrame(
            self.content, text="Grader", padding=10, style="Settings.TLabelframe"
        )
        grader_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        grader_frame.columnconfigure(0, weight=1)

        ttk.Label(grader_frame, text=f"Currently grading as: {self.current_ta_name}").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        ttk.Label(grader_frame, text="Switch to: ").grid(row=1, column=0, sticky="w", pady=3)
        names = [ta.name for ta in self.ta_repository.list_all()]
        switch_var = StringVar()
        switch_combo = ttk.Combobox(grader_frame, textvariable=switch_var, values=names, width=25, state="readonly")
        switch_combo.grid(row=2, column=0, pady=3, sticky="w")
        if names:
            switch_combo.current(0)

        status_label = ttk.Label(grader_frame, text="")
        status_label.grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 0))

        def show_status(message: str):
            status_label.config(text=message)

        def switch_ta():
            chosen = switch_var.get().strip()
            if not chosen:
                show_status("Please choose a grader to switch to.")
                return
            ta = self.ta_repository.get_or_create(chosen)
            if self.on_ta_changed:
                self.on_ta_changed(ta.ta_id, ta.name)
            self.current_ta_name = ta.name
            show_status(f"Now grading as {ta.name}.")

        ttk.Button(grader_frame, text="Switch Grader", command=switch_ta).grid(
            row=2, column=1, padx=5, pady=3, sticky="w"
        )

        ttk.Label(grader_frame, text="Add new grader: ").grid(row=3, column=0, sticky="w", pady=(10, 3))
        new_ta_var = StringVar()
        new_ta_entry = ttk.Entry(grader_frame, textvariable=new_ta_var, width=27)
        new_ta_entry.grid(row=4, column=0, pady=3, sticky="w")

        def add_ta():
            name = new_ta_var.get().strip()
            if not name:
                show_status("Please enter a name.")
                return
            ta = self.ta_repository.get_or_create(name)
            switch_combo.configure(values=[t.name for t in self.ta_repository.list_all()])
            switch_var.set(ta.name)
            new_ta_var.set("")
            show_status(f"'{ta.name}' added. Use Switch Grader to grade as them.")

        ttk.Button(grader_frame, text="Add", command=add_ta).grid(row=4, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(grader_frame, text="Rename selected grader to: ").grid(row=5, column=0, sticky="w", pady=(10, 3))
        rename_var = StringVar()
        rename_entry = ttk.Entry(grader_frame, textvariable=rename_var, width=27)
        rename_entry.grid(row=6, column=0, pady=3, sticky="w")

        def rename_ta():
            selected = switch_var.get().strip()
            new_name = rename_var.get().strip()
            if not selected or not new_name:
                show_status("Please select a grader above and enter a new name.")
                return
            ta = self.ta_repository.get_by_name(selected)
            if not ta:
                show_status(f"Could not find grader '{selected}'.")
                return
            try:
                renamed = self.ta_repository.rename(ta.ta_id, new_name)
            except ValueError as e:
                show_status(str(e))
                return
            switch_combo.configure(values=[t.name for t in self.ta_repository.list_all()])
            switch_var.set(renamed.name)
            rename_var.set("")
            if selected == self.current_ta_name and self.on_ta_changed:
                self.on_ta_changed(renamed.ta_id, renamed.name)
                self.current_ta_name = renamed.name
            show_status(f"'{selected}' renamed to '{renamed.name}'.")

        ttk.Button(grader_frame, text="Rename", command=rename_ta).grid(row=6, column=1, padx=5, pady=3, sticky="w")

    def close(self):
        try:
            self.parent.attributes("-disabled", False)
        except Exception:
            pass
        super().close()