"""
Central configuration for the TA Application.

All paths are derived from this file's location (or, once packaged, from
the running executable's location) so the app is portable across machines
and operating systems. Nothing else in the codebase should hardcode a
filesystem path — import from here instead.

Two different "base directories" are needed once this app is packaged
with PyInstaller, not just one:

- A WRITABLE data base, for anything the app creates or modifies at
  runtime: the database, logs, settings, rosters TAs drop in, exports,
  sync files. This MUST persist between runs, so it's always next to the
  actual .exe (sys.executable) when frozen - never PyInstaller's onefile
  temp extraction folder (sys._MEIPASS), which is deleted after the app
  closes. Using _MEIPASS here would silently lose the entire database
  every time the app closes - a TA's grades would vanish on exit with no
  error, no warning, nothing. BASE_DIRECTORY below is this writable base.

- A READ-ONLY resource base, for files shipped WITH the app that are
  never modified at runtime: the bundled Vazirmatn fonts and the app
  icon. In a frozen onefile build these are only reachable at
  sys._MEIPASS (PyInstaller extracts bundled datas there each run); in a
  onedir build or when running from source, they sit right next to this
  file. RESOURCE_DIRECTORY below is this read-only base.

When running from source (not frozen), both bases are simply this file's
own directory, so nothing about normal development changes.
"""
import os
import sys


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _writable_data_base() -> str:
    if _is_frozen():
        # Next to the actual .exe - persists between runs, unlike
        # sys._MEIPASS (onefile's temp extraction folder, wiped on exit).
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _readonly_resource_base() -> str:
    if _is_frozen() and hasattr(sys, "_MEIPASS"):
        # Onefile: PyInstaller extracts bundled datas here each run.
        return sys._MEIPASS
    if _is_frozen():
        # Onedir: bundled datas sit next to the .exe, same as the
        # writable base - there's no separate temp extraction step.
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIRECTORY = _writable_data_base()
RESOURCE_DIRECTORY = _readonly_resource_base()

DB_PATH = os.path.join(BASE_DIRECTORY, "universityDB.db")

# Where class rosters (Name, Sid per line) are read FROM at course setup.
# This used to be misnamed "exports" even though it's actually input data.
ROSTER_DIRECTORY = os.path.join(BASE_DIRECTORY, "data", "rosters")

# Where CSV/Excel grade exports are written TO.
EXPORT_DIRECTORY = os.path.join(BASE_DIRECTORY, "data", "exports")

# Where CSV/Excel files of scores (e.g. exported by another TA, or from an
# autograder) are read FROM for bulk score import. Deliberately separate
# from EXPORT_DIRECTORY - mixing an input folder with an output folder is
# exactly the bug ROSTER_DIRECTORY's docstring above already describes
# fixing once for rosters; keeping score imports/exports apart avoids
# repeating it.
SCORE_IMPORT_DIRECTORY = os.path.join(BASE_DIRECTORY, "data", "score_imports")

LOG_DIRECTORY = os.path.join(BASE_DIRECTORY, "logs")

SETTINGS_DIRECTORY = os.path.join(BASE_DIRECTORY, "settings")
THEME_CONFIG_PATH = os.path.join(SETTINGS_DIRECTORY, "theme_config.txt")

# Bundled Vazirmatn font files (Persian/Arabic script support for PDF
# export - fpdf2's built-in core font only supports Latin-1 otherwise;
# see ExportService.export_to_pdf). These ship WITH the app and are never
# written to at runtime, so they come from RESOURCE_DIRECTORY, not the
# writable BASE_DIRECTORY - critical for onefile builds, where the
# writable base (next to the .exe) is a different folder entirely from
# where PyInstaller actually extracts bundled files (sys._MEIPASS).
FONTS_DIRECTORY = os.path.join(RESOURCE_DIRECTORY, "assets", "fonts")

# App icon (assets/logo/icon.ico / icon.png) - also a bundled, read-only
# resource, so it uses RESOURCE_DIRECTORY for the same reason as the
# fonts above.
LOGO_DIRECTORY = os.path.join(RESOURCE_DIRECTORY, "assets", "logo")
APP_ICON_ICO = os.path.join(LOGO_DIRECTORY, "icon.ico")
APP_ICON_PNG = os.path.join(LOGO_DIRECTORY, "icon.png")

# Default local folder for Sync Out/In (see services/sync_service.py and
# ui/windows/sync_window.py). This is just a sensible default that always
# exists on this machine - a TA can (and typically will) point Sync Out/In
# at wherever their group's actual shared location is instead (a Dropbox
# folder, a USB drive, etc.), the same way ExportWindow's folder field
# works.
SYNC_DIRECTORY = os.path.join(BASE_DIRECTORY, "data", "sync")

# Remembers which TA is using this install, so they're only asked once
# instead of every launch. Purely local attribution, not an account system
# — see db/ta_repository.py and ui/windows/ta_select_window.py.
CURRENT_TA_PATH = os.path.join(SETTINGS_DIRECTORY, "current_ta.txt")

# Credit line shown in the Esc menu footer and Settings' About section.
# Kept here so both places read from one source and can't drift apart.
APP_AUTHOR = "Amirmasoud Mohammadian"
APP_CREDIT = f"Created by {APP_AUTHOR}"

# Only the WRITABLE directories get created here. FONTS_DIRECTORY and
# LOGO_DIRECTORY are bundled read-only resources - they ship already
# populated (the Vazirmatn files, the icon), so there's nothing to create,
# and creating an empty folder over a bundled one would be meaningless at
# best and couldn't write into a onefile build's read-only extraction
# folder at worst.
for _directory in (ROSTER_DIRECTORY, EXPORT_DIRECTORY, SCORE_IMPORT_DIRECTORY,
                   SYNC_DIRECTORY, LOG_DIRECTORY, SETTINGS_DIRECTORY):
    os.makedirs(_directory, exist_ok=True)