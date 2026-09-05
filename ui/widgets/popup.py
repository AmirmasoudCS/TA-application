"""
Reusable base class for the app's custom (chrome-less) popup windows.

The original TAapp.py hand-rolled this pattern separately in
createTitleBar(), askBaseGrade(), openUpdateWindow(), openCourseWindow(),
openFilenameWindow(), openCommentWindow(), openSettingsMenu(), and the
histogram popup in showHistogram() — same drag-to-move title bar, same
centering-over-parent logic, copy-pasted each time. This class factors
that out once.

Subclasses/callers:
- override `build_content(content_frame)` to add widgets, OR
- just use `Popup` directly and call `.content` to add widgets themselves.
"""
from tkinter import Toplevel
from tkinter import ttk


class Popup(Toplevel):
    def __init__(self, parent, title: str, theme, width: int = None, height: int = None,
                 resizable: bool = False, modal: bool = True, custom_titlebar: bool = True):
        super().__init__(parent)
        self.parent = parent
        self.theme = theme
        self._drag_x = 0
        self._drag_y = 0

        if custom_titlebar:
            self.overrideredirect(True)
        else:
            self.title(title)

        if width and height:
            self.geometry(f"{width}x{height}")
        if not resizable:
            self.resizable(False, False)

        self.configure(bg=theme.BG)
        self.grid_columnconfigure(0, weight=1)

        self.title_bar = None
        if custom_titlebar:
            self.title_bar = self._build_titlebar(title)

        self.content = ttk.Frame(self)
        self.content.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.grid_rowconfigure(1, weight=1)

        if modal:
            self.transient(parent)
            # grab_set() can hang/error if called before the window is
            # actually mapped/visible (this is what caused the histogram
            # popup to freeze the whole app). Force it to draw first.
            self.update_idletasks()
            self.deiconify()
            self.wait_visibility()
            self.grab_set()

    def _build_titlebar(self, title: str):
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        label = ttk.Label(bar, text=title)
        label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        close_btn = ttk.Button(bar, text="\u2715", width=3, command=self.close)
        close_btn.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        for widget in (bar, label):
            widget.bind("<Button-1>", self._start_move)
            widget.bind("<B1-Motion>", self._do_move)

        return bar

    def _start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_move(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.geometry(f"+{x}+{y}")

    def center_over_parent(self):
        self.parent.update_idletasks()
        self.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        w = self.winfo_width()
        h = self.winfo_height()
        x = parent_x + (parent_w // 2) - (w // 2)
        y = parent_y + (parent_h // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")

    def close(self):
        try:
            if self.master.winfo_exists():
                self.master.attributes("-disabled", False)
        except Exception:
            pass
        self.destroy()
        try:
            self.master.focus_force()
        except Exception:
            pass