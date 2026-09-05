"""
Theming for the app, ported from the original configure_styles.py.

Fix applied: saveTheme/loadTheme used to hardcode a relative,
Windows-style path ("settings\\theme_config.txt") which broke on
non-Windows systems and depended on the current working directory.
Now uses config.THEME_CONFIG_PATH, which is always an absolute path
derived from config.BASE_DIRECTORY.
"""
from tkinter import ttk

from config import THEME_CONFIG_PATH
from logging_setup import get_logger

logger = get_logger("ui.theme")

_THEME_BUILDERS = {}  # populated at bottom of file via decorator


def _theme(name):
    def register(func):
        _THEME_BUILDERS[name] = func
        return func
    return register


class Theme:
    def __init__(self):
        self.BG = None
        self.CARD = None
        self.PURPLE = None
        self.PURPLE_HOVER = None
        self.PURPLE_DARK = None
        self.FG = None
        self.TEXT_LIGHT = None
        self.BORDER = None
        self.FIELD_BG = None
        self.MENU_BTN = None
        self.MENU_BTN_HOVER = None
        self.MENU_BTN_PRESS = None
        self.DISABLED = None
        self.WHITE = None
        self.SETTINGS_BTN = None
        self.style = None
        self.current_name = "default"
        self.theme_default()

    # ---- persistence ----
    def save_theme(self, theme_name: str) -> None:
        try:
            with open(THEME_CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(theme_name)
            self.current_name = theme_name
        except OSError:
            logger.exception("Failed to save theme preference to %s", THEME_CONFIG_PATH)

    def load_theme(self) -> None:
        theme_name = "default"
        try:
            with open(THEME_CONFIG_PATH, "r", encoding="utf-8") as f:
                theme_name = f.read().strip() or "default"
        except FileNotFoundError:
            logger.info("No theme_config.txt found yet, defaulting to 'default'.")
        except OSError:
            logger.exception("Failed to read theme preference from %s", THEME_CONFIG_PATH)

        builder = _THEME_BUILDERS.get(theme_name, _THEME_BUILDERS["default"])
        builder(self)
        self.current_name = theme_name

    def set_theme(self, theme_name: str) -> None:
        builder = _THEME_BUILDERS.get(theme_name)
        if builder is None:
            logger.warning("Unknown theme '%s', ignoring.", theme_name)
            return
        builder(self)
        self.current_name = theme_name

    # ---- palettes ----
    @_theme("default")
    def theme_default(self):
        self.BG = "#f2e5ff"
        self.CARD = "#e8e0f5"
        self.PURPLE = "#7c3aed"
        self.PURPLE_HOVER = "#6d28d9"
        self.PURPLE_DARK = "#5b21b6"
        self.FG = "#2d1b69"
        self.MENU_LABEL = "black"
        self.TEXT_LIGHT = "#ffffff"
        self.BORDER = "#d6ccf5"
        self.FIELD_BG = "#ffffff"
        self.SCROLL_BG = "#f2ebff"
        self.SCROLL_THUMB = "#c4a6ff"
        self.SCROLL_THUMB_HOVER = "#b491ff"
        self.MENU_BTN = "#6d28d9"
        self.MENU_BTN_HOVER = "#5b21b6"
        self.MENU_BTN_PRESS = "#4a1a94"
        self.DISABLED = "#c7c7c7"
        self.WHITE = "#ffffff"
        self.SETTINGS_BTN = "#e6d6ff"
        self.TREE_BG = "#3f3a4a"
        self.TREE_FG = "#ffffff"

    @_theme("dark")
    def theme_dark(self):
        self.BG = "#0f0f14"
        self.CARD = "#1a1a21"
        self.PURPLE = "black"
        self.MENU_LABEL = "#ffffff"
        self.PURPLE_HOVER = "#1f1f1f"
        self.PURPLE_DARK = "#2a2a2a"
        self.FG = "#e6e6e6"
        self.TEXT_LIGHT = "#ffffff"
        self.BORDER = "#2a2a32"
        self.FIELD_BG = "#2a2a33"
        self.MENU_BTN = "black"
        self.MENU_BTN_HOVER = "#181818"
        self.MENU_BTN_PRESS = "#2a2a2a"
        self.DISABLED = "#c7c7c7"
        self.WHITE = "#ffffff"
        self.SETTINGS_BTN = "#181818"
        self.SCROLL_BG = "#0f0f14"
        self.SCROLL_THUMB = "#3a3a45"
        self.SCROLL_THUMB_HOVER = "#4d4d57"
        self.TREE_BG = "#2b2b2b"
        self.TREE_FG = "#ffffff"

    @_theme("blue")
    def theme_blue(self):
        self.BG = "#e8f1ff"
        self.CARD = "#dce9ff"
        self.PURPLE = "#2563eb"
        self.MENU_LABEL = "black"
        self.SCROLL_BG = "#0f0f14"
        self.SCROLL_THUMB = "#3e3e49"
        self.SCROLL_THUMB_HOVER = "#555563"
        self.PURPLE_HOVER = "#1d4ed8"
        self.PURPLE_DARK = "#1e40af"
        self.FG = "#0f172a"
        self.TEXT_LIGHT = "#ffffff"
        self.BORDER = "#bcd3ff"
        self.FIELD_BG = "#f8fbff"
        self.MENU_BTN = "#505ee6"
        self.MENU_BTN_HOVER = "#4755cc"
        self.MENU_BTN_PRESS = "#39449a"
        self.DISABLED = "#777777"
        self.WHITE = "#ffffff"
        self.SETTINGS_BTN = "#181818"
        self.TREE_BG = "#26262d"
        self.TREE_FG = "#f0f0f0"

    @_theme("green")
    def theme_green(self):
        self.BG = "#e8fff2"
        self.CARD = "#d9f7e8"
        self.PURPLE = "#16a34a"
        self.MENU_LABEL = "black"
        self.PURPLE_HOVER = "#15803d"
        self.PURPLE_DARK = "#166534"
        self.FG = "#064e3b"
        self.TEXT_LIGHT = "#ffffff"
        self.BORDER = "#b7e4c7"
        self.FIELD_BG = "#ffffff"
        self.SCROLL_BG = "#e9faef"
        self.SCROLL_THUMB = "#9ae6b4"
        self.SCROLL_THUMB_HOVER = "#68d391"
        self.MENU_BTN = "#12833d"
        self.MENU_BTN_HOVER = "#116a32"
        self.MENU_BTN_PRESS = "#0f4f28"
        self.DISABLED = "#c7c7c7"
        self.WHITE = "#ffffff"
        self.SETTINGS_BTN = "#dbfce7"
        self.TREE_BG = "#2f4a3a"
        self.TREE_FG = "#ffffff"

    @_theme("red")
    def theme_red(self):
        self.BG = "#ffe8e8"
        self.CARD = "#ffdada"
        self.PURPLE = "#dc2626"
        self.MENU_LABEL = "black"
        self.PURPLE_HOVER = "#b91c1c"
        self.PURPLE_DARK = "#7f1d1d"
        self.FG = "#3f0d0d"
        self.SCROLL_BG = "#ffeaea"
        self.SCROLL_THUMB = "#f87171"
        self.SCROLL_THUMB_HOVER = "#ef4444"
        self.TEXT_LIGHT = "#ffffff"
        self.BORDER = "#ffb4b4"
        self.FIELD_BG = "#ffffff"
        self.MENU_BTN = "#b31f1f"
        self.MENU_BTN_HOVER = "#991818"
        self.MENU_BTN_PRESS = "#621515"
        self.DISABLED = "#c7c7c7"
        self.WHITE = "#ffffff"
        self.SETTINGS_BTN = "#ffdcdc"
        self.TREE_BG = "#4a2f2f"
        self.TREE_FG = "#ffffff"

    @_theme("yellow")
    def theme_yellow(self):
        self.BG = "#fff9db"
        self.CARD = "#fff3bf"
        self.PURPLE = "#eab308"
        self.MENU_LABEL = "black"
        self.PURPLE_HOVER = "#ca8a04"
        self.PURPLE_DARK = "#a16207"
        self.FG = "#3f2f00"
        self.TEXT_LIGHT = "#ffffff"
        self.BORDER = "#ffe066"
        self.FIELD_BG = "#ffffff"
        self.MENU_BTN = "#c89b06"
        self.SCROLL_BG = "#fff9e6"
        self.SCROLL_THUMB = "#fde047"
        self.SCROLL_THUMB_HOVER = "#facc15"
        self.MENU_BTN_HOVER = "#a46f03"
        self.MENU_BTN_PRESS = "#805304"
        self.DISABLED = "#c7c7c7"
        self.WHITE = "#ffffff"
        self.SETTINGS_BTN = "#fff3cc"
        self.TREE_BG = "#4a472f"
        self.TREE_FG = "#ffffff"

    @_theme("pink")
    def theme_pink(self):
        self.BG = "#ffe4f0"
        self.CARD = "#ffd6e8"
        self.PURPLE = "#ec4899"
        self.PURPLE_HOVER = "#db2777"
        self.PURPLE_DARK = "#9d174d"
        self.MENU_LABEL = "black"
        self.FG = "#4a044e"
        self.TEXT_LIGHT = "#ffffff"
        self.BORDER = "#ffb3d6"
        self.FIELD_BG = "#ffffff"
        self.MENU_BTN = "#d23e88"
        self.MENU_BTN_HOVER = "#b42164"
        self.MENU_BTN_PRESS = "#7f1238"
        self.SCROLL_BG = "#ffeaf3"
        self.SCROLL_THUMB = "#f9a8d4"
        self.SCROLL_THUMB_HOVER = "#f472b6"
        self.DISABLED = "#c7c7c7"
        self.WHITE = "#ffffff"
        self.SETTINGS_BTN = "#ffd9eb"
        self.TREE_BG = "#4a2f3f"
        self.TREE_FG = "#ffffff"

    @_theme("jigari")
    def theme_jigari(self):
        self.BG = "#1a0f12"
        self.CARD = "#26161a"
        self.PURPLE = "#7a1e2c"
        self.PURPLE_HOVER = "#8f2433"
        self.PURPLE_DARK = "#5c1621"
        self.MENU_LABEL = "#ffffff"
        self.FG = "#f5eaea"
        self.TEXT_LIGHT = "#ffffff"
        self.BORDER = "#3a2026"
        self.FIELD_BG = "#2a1a1f"
        self.SCROLL_BG = "#1a0f12"
        self.SCROLL_THUMB = "#5a1c26"
        self.SCROLL_THUMB_HOVER = "#7a1e2c"
        self.MENU_BTN = "#6a1a27"
        self.MENU_BTN_HOVER = "#8f2433"
        self.MENU_BTN_PRESS = "#4a121b"
        self.DISABLED = "#777777"
        self.WHITE = "#ffffff"
        self.SETTINGS_BTN = "#2a1a1f"
        self.TREE_BG = "#241419"
        self.TREE_FG = "#ffffff"

    # ---- ttk wiring ----
    def apply(self, window) -> None:
        self.style = ttk.Style(window)
        self.style.theme_use("clam")

        window.configure(bg=self.BG)

        self.style.configure(
            "TLabel", background=self.BG, foreground=self.FG,
            font=("Segoe UI", 12, "bold"),
        )
        self.style.configure(
            "TEntry", padding=6, borderwidth=1, relief="solid",
            fieldbackground=self.FIELD_BG, font=("Inter", 12),
            foreground=self.FG, background=self.FIELD_BG,
            bordercolor=self.BORDER, lightcolor=self.PURPLE, darkcolor=self.PURPLE,
        )
        self.style.map(
            "TEntry",
            fieldbackground=[("disabled", self.CARD), ("!disabled", self.FIELD_BG)],
            foreground=[("disabled", "#777777"), ("!disabled", self.FG)],
            bordercolor=[("focus", self.PURPLE), ("!focus", self.BORDER)],
            lightcolor=[("focus", self.PURPLE), ("!focus", self.BORDER)],
            darkcolor=[("focus", self.PURPLE), ("!focus", self.BORDER)],
        )
        self.style.configure(
            "TButton", background=self.PURPLE, foreground=self.TEXT_LIGHT,
            font=("Segoe UI", 10, "bold"), padding=7,
            bordercolor=self.BORDER, relief="solid", borderwidth=0,
        )
        self.style.map(
            "TButton",
            background=[("active", self.PURPLE_HOVER), ("pressed", self.PURPLE_DARK), ("!disabled", self.PURPLE)],
            foreground=[("disabled", self.DISABLED)],
        )
        self.style.configure("TFrame", background=self.BG)
        self.style.configure(
            "TLabelframe", background=self.CARD, foreground=self.FG,
            borderwidth=1, relief="solid", bordercolor=self.BORDER,
        )
        self.style.configure(
            "TLabelframe.Label", background=self.CARD, foreground=self.FG,
            font=("Segoe UI", 11, "bold"),
        )
        for orientation in ("Vertical", "Horizontal"):
            self.style.configure(
                f"{orientation}.TScrollbar", background=self.SCROLL_BG,
                troughcolor=self.SCROLL_BG, bordercolor=self.BORDER,
                arrowcolor=self.TEXT_LIGHT,
            )
            self.style.map(
                f"{orientation}.TScrollbar",
                background=[("active", self.SCROLL_THUMB_HOVER), ("!active", self.SCROLL_THUMB)],
            )
        self.style.configure(
            "TScrollbar", background=self.PURPLE, troughcolor=self.BG,
            borderwidth=0, arrowcolor=self.TEXT_LIGHT,
        )
        self.style.configure(
            "Treeview", background=self.TREE_BG, foreground=self.TREE_FG,
            fieldbackground=self.TREE_BG, rowheight=26, font=("Segoe UI", 10),
        )
        self.style.map(
            "Treeview",
            background=[("selected", self.PURPLE)],
            foreground=[("selected", self.TEXT_LIGHT)],
        )
        self.style.configure(
            "Treeview.Heading", background=self.PURPLE, foreground=self.TEXT_LIGHT,
            relief="flat", font=("Segoe UI", 10, "bold"), borderwidth=0, padding=5,
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", self.PURPLE_HOVER), ("pressed", self.PURPLE_DARK)],
        )
        self.style.configure("Settings.TLabelframe", background=self.BG)
        self.style.configure("Settings.TLabelframe.Label", background=self.BG, foreground=self.FG)
        self.style.configure(
            "MenuLabel.TLabel", background=self.PURPLE, foreground=self.MENU_LABEL,
            font=("Segoe UI", 14, "bold"),
        )
        self.style.configure(
            "MenuButtons.TButton", foreground=self.TEXT_LIGHT,
            font=("Segoe UI", 10, "bold"), borderwidth=0, padding=6,
            relief="flat", anchor="center",
        )
        self.style.map(
            "MenuButtons.TButton",
            background=[("active", self.MENU_BTN_HOVER), ("pressed", self.MENU_BTN_PRESS), ("!disabled", self.MENU_BTN)],
            foreground=[("active", self.TEXT_LIGHT), ("!disabled", self.TEXT_LIGHT)],
            relief=[("pressed", "flat"), ("active", "raised")],
        )
        self.style.configure("sidStyle.TLabel", foreground=self.FG, background=self.FIELD_BG)
        self.style.layout("Treeview.Heading", [
            ("Treeheading.cell", {"sticky": "nswe"}),
            ("Treeheading.border", {"sticky": "nswe", "children": [
                ("Treeheading.padding", {"sticky": "nswe", "children": [
                    ("Treeheading.image", {"side": "right", "sticky": ""}),
                    ("Treeheading.text", {"sticky": "we"}),
                ]}),
            ]}),
        ])
