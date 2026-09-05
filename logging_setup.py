"""
Centralized logging configuration.

Import `get_logger(__name__)` anywhere in the app instead of using
bare `except: pass` or `print(...)` for error handling. This is what
replaces the old silent-failure pattern throughout the original codebase.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

from config import LOG_DIRECTORY

_LOG_FILE = os.path.join(LOG_DIRECTORY, "taapp.log")
_configured = False


def _configure_root():
    global _configured
    if _configured:
        return
    root = logging.getLogger("taapp")
    root.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure_root()
    return logging.getLogger(f"taapp.{name}")
