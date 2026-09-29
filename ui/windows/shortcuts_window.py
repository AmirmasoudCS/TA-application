"""
Keyboard shortcuts reference popup, opened from the Esc menu.

The shortcut list below is kept as one small constant right next to where
it's rendered, rather than scattered comments at each .bind() call site in
main_window.py - if a shortcut is ever added, removed, or rebound there,
this list needs a matching one-line update here too, and having both in
one obvious place makes that easy to remember to do.

The list is rendered inside a scrollable canvas rather than directly in
self.content: ttk has no built-in scrollable frame, so a plain tk.Canvas
plus an inner ttk.Frame is the standard way to get one. This matters once
the shortcut list grows past what fits in the window's fixed height.
"""
import tkinter as tk
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
                          resizable=True, custom_titlebar=True, modal=False)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(self.content, bg=theme.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        list_frame = ttk.Frame(canvas)
        list_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=list_frame, anchor="nw")
        # Keep the inner frame's width matched to the canvas's, so wrapped
        # text in the Action column reflows correctly if the (resizable)
        # window is widened rather than staying clipped to the original width.
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(canvas_window, width=e.width))

        # Mousewheel scrolling, but only bound while the cursor is over
        # this canvas - bind_all() unconditionally would leak a global
        # binding that keeps affecting other windows after this one closes.
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        list_frame.grid_columnconfigure(0, weight=0)
        list_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(list_frame, text="Shortcut", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=(5, 20), pady=(0, 8)
        )
        ttk.Label(list_frame, text="Action", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=1, sticky="w", pady=(0, 8)
        )

        for index, (combo, description) in enumerate(SHORTCUTS, start=1):
            ttk.Label(list_frame, text=combo, style="sidStyle.TLabel").grid(
                row=index, column=0, sticky="w", padx=(5, 20), pady=3
            )
            ttk.Label(list_frame, text=description, wraplength=260, justify="left").grid(
                row=index, column=1, sticky="w", pady=3
            )

        self.center_over_parent()