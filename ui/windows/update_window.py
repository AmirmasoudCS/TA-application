"""
Popup for editing an existing row's score/comment.

Extracted from TAapp.py's openUpdateWindow(). The original read the
currently-selected Treeview row directly; this version takes the values
already selected (sid, score, comment) and reports back via callback,
keeping DB/table-refresh logic in the controller.
"""
from tkinter import StringVar
from tkinter import ttk

from ui.widgets.popup import Popup


class UpdateWindow(Popup):
    def __init__(self, parent, theme, sid, score, comment, on_save):
        """on_save: callable(sid, new_score: str, new_comment: str) -> None"""
        super().__init__(parent, "Update Record", theme, custom_titlebar=False)
        self.on_save = on_save
        self.sid = sid

        ttk.Label(self.content, text="ID").pack(pady=(10, 2))
        ttk.Label(self.content, text=str(sid), anchor="center", width=30,
                  style="sidStyle.TLabel").pack(pady=5)

        ttk.Label(self.content, text="Score").pack(pady=(10, 2))
        self._score_var = StringVar(value=score)
        score_entry = ttk.Entry(self.content, textvariable=self._score_var, width=40)
        score_entry.pack(pady=10, ipady=4)
        score_entry.focus_set()
        score_entry.icursor("end")

        ttk.Label(self.content, text="Comment").pack(pady=(10, 2))
        self._comment_var = StringVar(value=comment)
        ttk.Entry(self.content, textvariable=self._comment_var, width=30).pack(pady=5)

        save_btn = ttk.Button(self.content, text="Save Update", command=self._save)
        save_btn.pack(pady=15)
        self.bind("<Return>", lambda e=None: save_btn.invoke())
        self.center_over_parent()

    def _save(self):
        new_score = self._score_var.get()
        new_comment = self._comment_var.get()
        self.destroy()
        self.on_save(self.sid, new_score, new_comment)
