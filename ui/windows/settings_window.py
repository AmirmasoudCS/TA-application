"""
Settings popup: theme picker + "change course" form.

Extracted from TAapp.py's openSettingsMenu(). Theme switching and course
changes are both delegated to callbacks so this window has no direct
dependency on Database or the rest of the app's globals.
"""
from tkinter import StringVar
from tkinter import messagebox, ttk

from ui.widgets.popup import Popup

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
    def __init__(self, parent, theme, on_theme_change, on_change_course):
        """
        on_theme_change: callable(theme_name: str) -> None
        on_change_course: callable(course_name: str, filename: str) -> None
        """
        super().__init__(parent, "Settings", theme, custom_titlebar=False)
        self.on_theme_change = on_theme_change
        self.on_change_course = on_change_course

        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_columnconfigure(1, weight=1)
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))

        self._build_theme_section()
        self._build_course_section()

        ttk.Button(self.content, text="Close Settings", command=self.close).grid(
            row=5, column=0, columnspan=2, padx=5, pady=5
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
                messagebox.showwarning("Missing Input", "Please fill both course name and filename.")
                return
            self.destroy()
            self.on_change_course(name, filename)

        apply_btn = ttk.Button(course_frame, text="Apply New Course", command=apply_new_course)
        apply_btn.grid(row=4, column=0, columnspan=2, pady=10)
        filename_entry.bind("<Return>", lambda e=None: apply_btn.invoke())

    def close(self):
        try:
            self.parent.attributes("-disabled", False)
        except Exception:
            pass
        super().close()
