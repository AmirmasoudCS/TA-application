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
from tkinter import messagebox, ttk


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

        if modal and not custom_titlebar:
            # Real Tk grab_set() is only safe here because native-title-bar
            # windows are properly managed by the window manager for focus
            # and visibility. Chromeless (overrideredirect) windows are not
            # reliably tracked by window managers, and combining
            # overrideredirect with a modal grab caused two separate
            # freezes (histogram popup hang, and losing all input after
            # tabbing away from Settings). So overrideredirect popups never
            # take a Tk grab - see the `elif custom_titlebar` branch below.
            #
            # Only mark this transient-to-parent if the parent is actually
            # viewable (e.g. NOT the withdrawn root during initial course
            # setup) - many window managers refuse to ever map a transient
            # child of a hidden window, which made wait_visibility() below
            # hang forever with nothing appearing on screen.
            if parent.winfo_viewable():
                self.transient(parent)
            self.update_idletasks()
            self.deiconify()
            self.wait_visibility()
            self.grab_set()
        elif custom_titlebar:
            # No Tk grab. Callers that want modal-like behavior for a
            # chromeless popup (e.g. SettingsWindow) should disable the
            # parent window themselves (parent.attributes("-disabled", True))
            # and re-enable it on close, rather than relying on grab_set.
            #
            # -topmost is needed here regardless of `modal`: the main
            # window runs with -fullscreen True, which on many systems
            # keeps it stacked above ordinary windows. Without -topmost, a
            # chromeless popup (e.g. the histogram) can open successfully
            # but render invisibly behind the fullscreen main window.
            if parent.winfo_viewable():
                self.transient(parent)
            self.attributes("-topmost", True)
            self.lift()

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

    def notify(self, kind: str, title: str, message: str):
        """Shows a messagebox dialog safely from within a modal popup.

        Tk only allows one active local grab at a time. Calling
        messagebox.showwarning/showinfo/showerror directly while this
        popup holds a modal grab_set() creates a second window that also
        wants exclusive input - neither window can then receive clicks,
        which looked like the whole app freezing. This releases the grab
        first, shows the dialog, then re-acquires it if the popup is
        still open.
        """
        had_grab = self.grab_current() == self
        if had_grab:
            self.grab_release()
        try:
            if kind == "warning":
                messagebox.showwarning(title, message, parent=self)
            elif kind == "error":
                messagebox.showerror(title, message, parent=self)
            else:
                messagebox.showinfo(title, message, parent=self)
        finally:
            if had_grab and self.winfo_exists():
                self.grab_set()