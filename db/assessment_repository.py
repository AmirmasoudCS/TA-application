"""
Read/write access to a single assessment table's rows (Sid, Score, Comment)
plus generic table-introspection helpers used by the UI (columns, distinct
rows, single-column value lists).

Bug fix: removeItem() used to inline `sid` directly into the SQL string
(f"... WHERE Sid = {sid}") instead of binding it as a parameter. Fixed here.
"""
from typing import List, Optional

from db.connection import Connection
from logging_setup import get_logger

logger = get_logger("db.assessment_repository")


class AssessmentRepository:
    def __init__(self, connection: Connection):
        self.conn = connection

    def add_or_replace_item(self, table_name: str, sid: int, score, comment: str = "") -> None:
        comment = comment if comment != "" else "-"
        self.conn.execute(
            f"INSERT OR REPLACE INTO '{table_name}'(Sid, Score, Comment) VALUES(?, ?, ?)",
            (sid, score, comment),
        )
        self.conn.commit()

    def remove_item(self, table_name: str, sid: int) -> None:
        self.conn.execute(
            f"DELETE FROM '{table_name}' WHERE Sid = ?", (sid,)
        )
        self.conn.commit()

    def update_item(self, course_name: str, table_name: str, sid: int, new_score, new_comment: str) -> None:
        table = course_name + table_name
        self.conn.execute(
            f"UPDATE '{table}' SET Score = ?, Comment = ? WHERE Sid = ?",
            (new_score, new_comment, sid),
        )
        self.conn.commit()

    def get_columns(self, table_name: str) -> List[str]:
        cursor = self.conn.execute(f"PRAGMA table_info('{table_name}')")
        return [row[1] for row in cursor.fetchall()]

    def get_rows(self, table_name: str) -> List[tuple]:
        cursor = self.conn.execute(f"SELECT DISTINCT * FROM '{table_name}'")
        return cursor.fetchall()

    def get_column_values(self, table_name: str, column_name: str) -> List:
        # Column identifiers must use double quotes, not single quotes —
        # single-quoted "'{column_name}'" is a *string literal* in SQLite,
        # which would silently return the literal column name as the
        # "value" for every row instead of the actual data.
        cursor = self.conn.execute(f'SELECT "{column_name}" FROM \'{table_name}\'')
        return [row[0] for row in cursor.fetchall()]

    def search_by_sid_prefix(self, table_name: str, prefix: str) -> List[tuple]:
        if not prefix:
            return self.get_rows(table_name)
        cursor = self.conn.execute(
            f"SELECT * FROM '{table_name}' WHERE Sid LIKE ?", (prefix + "%",)
        )
        return cursor.fetchall()
