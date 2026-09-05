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

LOG_DIRECTORY = os.path.join(BASE_DIRECTORY, "logs")

SETTINGS_DIRECTORY = os.path.join(BASE_DIRECTORY, "settings")
THEME_CONFIG_PATH = os.path.join(SETTINGS_DIRECTORY, "theme_config.txt")

for _directory in (ROSTER_DIRECTORY, EXPORT_DIRECTORY, LOG_DIRECTORY, SETTINGS_DIRECTORY):
    os.makedirs(_directory, exist_ok=True)
