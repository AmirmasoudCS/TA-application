"""
Central configuration for the TA Application.

All paths are derived from this file's location so the app is portable
across machines and operating systems. Nothing else in the codebase
should hardcode a filesystem path — import from here instead.
"""
import os

BASE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

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

# Remembers which TA is using this install, so they're only asked once
# instead of every launch. Purely local attribution, not an account system
# — see db/ta_repository.py and ui/windows/ta_select_window.py.
CURRENT_TA_PATH = os.path.join(SETTINGS_DIRECTORY, "current_ta.txt")

for _directory in (ROSTER_DIRECTORY, EXPORT_DIRECTORY, SCORE_IMPORT_DIRECTORY, LOG_DIRECTORY, SETTINGS_DIRECTORY):
    os.makedirs(_directory, exist_ok=True)