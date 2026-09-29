"""
Keyboard shortcuts reference popup, opened from the Esc menu.

The shortcut list below is kept as one small constant right next to where
it's rendered, rather than scattered comments at each .bind() call site in
main_window.py - if a shortcut is ever added, removed, or rebound there,
this list needs a matching one-line update here too, and having both in
one obvious place makes that easy to remember to do.
"""
from tkinter import ttk

from ui.widgets.popup import Popup

# (key combo, what it does) - the five global bindings from MainWindow's
# root.bind() calls, plus the one convention (Enter) that applies broadly
# across text fields and dialogs rather than being a single specific bind.
SHORTCUTS = [
    ("Ctrl+N", "Focus the Student ID field (Add Students)"),
    ("Ctrl+F", "Focus the Search by ID field"),
    ("Ctrl+O", "Focus the Table to present field"),
    ("Ctrl+U", "Open the Update window for the selected row"),
    ("Esc", "Open or close this menu"),
    ("Enter", "Confirm the focused field or dialog (submits, same as clicking the main button)"),
]


class ShortcutsWindow(Popup):
    def __init__(self, parent, theme):
        super().__init__(parent, "Keyboard Shortcuts", theme, width=420, height=320,
                          custom_titlebar=True, modal=False)
        self.content.grid_columnconfigure(0, weight=0)
        self.content.grid_columnconfigure(1, weight=1)

        ttk.Label(self.content, text="Shortcut", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=(5, 20), pady=(0, 8)
        )
        ttk.Label(self.content, text="Action", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=1, sticky="w", pady=(0, 8)
        )

        for index, (combo, description) in enumerate(SHORTCUTS, start=1):
            ttk.Label(self.content, text=combo, style="sidStyle.TLabel").grid(
                row=index, column=0, sticky="w", padx=(5, 20), pady=3
            )
            ttk.Label(self.content, text=description, wraplength=260, justify="left").grid(
                row=index, column=1, sticky="w", pady=3
            )

        self.center_over_parent()