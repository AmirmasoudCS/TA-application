"""
Thin wrapper around sqlite3 connection/cursor.

Fixes from the original teacherAssistantAppDB.Database:
- No hardcoded machine-specific path. The path passed in (from config.DB_PATH)
  is used as-is.
- Explicit close() instead of relying on __del__ (which is not guaranteed to
  run in CPython at interpreter shutdown).
- Foreign keys turned on once at connection time, not per-call.
- Centralized query execution with logging instead of silent failures.
"""
import sqlite3

from logging_setup import get_logger

logger = get_logger("db.connection")


class Connection:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.con = sqlite3.connect(db_path)
        self.con.execute("PRAGMA foreign_keys = ON;")
        self.cursor = self.con.cursor()

    def execute(self, query: str, params: tuple = ()):
        try:
            self.cursor.execute(query, params)
            return self.cursor
        except sqlite3.Error:
            logger.exception("Query failed: %s | params=%s", query, params)
            raise

    def executemany(self, query: str, seq_of_params):
        try:
            self.cursor.executemany(query, seq_of_params)
            return self.cursor
        except sqlite3.Error:
            logger.exception("Batch query failed: %s", query)
            raise

    def commit(self):
        self.con.commit()

    def close(self):
        try:
            self.cursor.close()
        finally:
            self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
