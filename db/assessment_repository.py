"""
Read/write access to a single assessment table's rows (Sid, Score, Comment,
GraderId, UpdatedAt) plus generic table-introspection helpers used by the
UI (columns, distinct rows, single-column value lists).

Bug fix: removeItem() used to inline `sid` directly into the SQL string
(f"... WHERE Sid = {sid}") instead of binding it as a parameter. Fixed here.

GraderId/UpdatedAt were added so it's possible to tell who entered or last
touched a given score, and when. add_or_replace_item() and update_item()
now take an optional grader_id and stamp UpdatedAt themselves - callers
don't need to worry about timestamp formatting.

Every method that mutates a grade also logs an INFO line (table, sid,
grader) so there's a plain-text audit trail in logs/taapp.log of who
added, changed, or removed a score and when - separate from the
GraderId/UpdatedAt columns themselves, since a removed row leaves no
column behind to show who removed it.
"""
from datetime import datetime
from typing import List, Optional

from db.connection import Connection
from logging_setup import get_logger

logger = get_logger("db.assessment_repository")


class AssessmentRepository:
    def __init__(self, connection: Connection):
        self.conn = connection

    def add_or_replace_item(self, table_name: str, sid: int, score, comment: str = "", grader_id: Optional[int] = None) -> None:
        comment = comment if comment != "" else "-"
        updated_at = datetime.now().isoformat(timespec="seconds")
        self.conn.execute(
            f"INSERT OR REPLACE INTO '{table_name}'(Sid, Score, Comment, GraderId, UpdatedAt) "
            f"VALUES(?, ?, ?, ?, ?)",
            (sid, score, comment, grader_id, updated_at),
        )
        self.conn.commit()
        logger.info(
            "Score set in %s: Sid=%s Score=%s GraderId=%s", table_name, sid, score, grader_id
        )

    def remove_item(self, table_name: str, sid: int, grader_id: Optional[int] = None) -> None:
        self.conn.execute(
            f"DELETE FROM '{table_name}' WHERE Sid = ?", (sid,)
        )
        self.conn.commit()
        logger.info(
            "Row removed from %s: Sid=%s GraderId=%s", table_name, sid, grader_id
        )

    def update_item(self, course_name: str, table_name: str, sid: int, new_score, new_comment: str, grader_id: Optional[int] = None) -> None:
        table = course_name + table_name
        updated_at = datetime.now().isoformat(timespec="seconds")
        self.conn.execute(
            f"UPDATE '{table}' SET Score = ?, Comment = ?, GraderId = ?, UpdatedAt = ? WHERE Sid = ?",
            (new_score, new_comment, grader_id, updated_at, sid),
        )
        self.conn.commit()
        logger.info(
            "Score updated in %s: Sid=%s Score=%s GraderId=%s", table, sid, new_score, grader_id
        )

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