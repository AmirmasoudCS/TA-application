"""
Popup asking "Who are you?" so scores can be attributed to a TA.

Modeled on ui/windows/course_setup_window.py's CourseNameStep: a single
popup that either picks an existing TA from a dropdown or lets the user
type a new name. This is purely for attribution (GraderId on assessment
rows), not authentication - see db/ta_repository.py's docstring.

The chosen name is persisted to config.CURRENT_TA_PATH so a TA is only
asked once per install rather than on every launch. See MainWindow for
how that file is read/written.
"""
from tkinter import StringVar
from tkinter import ttk

from ui.widgets.popup import Popup
from db.ta_repository import TARepository


class TASelectWindow(Popup):
    def __init__(self, parent, theme, ta_repository: TARepository, on_complete):
        """on_complete: callable(ta_id: int, ta_name: str) -> None"""
        super().__init__(parent, "Who's grading?", theme, width=300, height=220, custom_titlebar=False)
        self.on_complete = on_complete
        self.ta_repository = ta_repository
        self.content.grid_columnconfigure(0, weight=1)

        ttk.Label(self.content, text="Select your name:").grid(row=0, column=0, pady=(10, 2))
        existing = self.ta_repository.list_all()
        self._name_var = StringVar()

        if existing:
            names = [ta.name for ta in existing]
            combo = ttk.Combobox(self.content, textvariable=self._name_var,
                                  values=names, width=27, state="readonly")
            combo.grid(row=1, column=0, pady=5, padx=10)
            combo.current(0)
        else:
            ttk.Label(self.content, text="(no TAs registered yet)").grid(row=1, column=0)

        ttk.Label(self.content, text="Or type a new name:").grid(row=2, column=0, pady=(10, 2))
        entry = ttk.Entry(self.content, textvariable=self._name_var, width=30)
        entry.grid(row=3, column=0, pady=5, padx=10)
        entry.focus_set()

        submit_btn = ttk.Button(self.content, text="Continue", command=self._submit, width=10)
        submit_btn.grid(row=4, column=0, pady=10)
        self.bind("<Return>", lambda e=None: submit_btn.invoke())
        self.center_over_parent()

    def _submit(self):
        name = self._name_var.get().strip()
        if not name:
            self.notify("warning", "Input Error", "Please select or type your name.")
            return
        ta = self.ta_repository.get_or_create(name)
        self.destroy()
        self.on_complete(ta.ta_id, ta.name)