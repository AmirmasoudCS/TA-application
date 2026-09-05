"""
Popup asking for an optional comment when a score is added.

Extracted from TAapp.py's openCommentWindow(). Decoupled from global state:
takes the student's name/sid/score directly and calls back with the
comment text on submit, rather than reaching into module-level Database
and StringVar globals.
"""
from tkinter import StringVar
from tkinter import ttk

from ui.widgets.popup import Popup


class CommentWindow(Popup):
    def __init__(self, parent, theme, student_name: str, on_submit):
        """on_submit: callable(comment_text: str) -> None"""
        super().__init__(parent, "Add Comment", theme, width=350, height=200, custom_titlebar=False)
        self.on_submit = on_submit
        self._comment_var = StringVar()

        ttk.Label(self.content, text=f"Any comment for '{student_name}' score?").pack(pady=10)
        entry = ttk.Entry(self.content, textvariable=self._comment_var, width=40)
        entry.pack(pady=10)
        entry.focus_set()

        submit_btn = ttk.Button(self.content, text="Submit", command=self._submit)
        submit_btn.pack(pady=10)

        self.bind("<Return>", lambda e=None: submit_btn.invoke())
        self.center_over_parent()

    def _submit(self):
        comment = self._comment_var.get()
        self.destroy()
        self.on_submit(comment)
