"""
Handles creation/finalization of course-level and assessment-level tables.

This replaces the course-table-related methods of the old god-class
`Database`: createTable, tableExists, createAssessmentInfoTable,
getBaseGrade, finalize, finalizeTable.

Bug fixes applied here:
- finalizeTable(): fixed the "VALUSE" typo (-> "VALUES"), and stopped
  re-running CREATE TABLE inside the loop over assessment tables — the
  column list is now built once, then the table is created once.
- All table names are still interpolated (SQLite doesn't support
  parameterized identifiers), but every value (scores, ids, etc.) is
  passed as a bound parameter.
"""
from typing import List, Optional

from db.connection import Connection
from logging_setup import get_logger

logger = get_logger("db.course_repository")


class CourseRepository:
    def __init__(self, connection: Connection):
        self.conn = connection

    def create_students_table(self, course_name: str) -> None:
        table = f"{course_name}Students"
        self.conn.execute(
            f"CREATE TABLE IF NOT EXISTS '{table}'(Sid INTEGER PRIMARY KEY, SName TEXT)"
        )
        self.conn.commit()

    def create_assessment_info_table(self, course_name: str) -> None:
        table = f"{course_name}AssessmentInfo"
        self.conn.execute(
            f"CREATE TABLE IF NOT EXISTS '{table}'(tableName TEXT PRIMARY KEY, baseGrade INTEGER)"
        )
        self.conn.commit()

    def create_assessment_table(
        self,
        table_name: str,
        course_name: str,
        base_grade: Optional[float] = None,
    ) -> None:
        """Creates a per-course assessment table (e.g. Quiz1, ProblemSet2)
        and records its base grade in <course>AssessmentInfo."""
        final_table = course_name + table_name

        if table_name.endswith("Students"):
            self.create_students_table(course_name)
            return

        self.conn.execute(
            f"CREATE TABLE IF NOT EXISTS '{final_table}'("
            f"Sid INTEGER PRIMARY KEY, Score INTEGER, Comment TEXT, "
            f"FOREIGN KEY(Sid) REFERENCES '{course_name}Students'(Sid) "
            f"ON DELETE CASCADE ON UPDATE CASCADE)"
        )
        self.conn.commit()

        self.create_assessment_info_table(course_name)
        info_table = f"{course_name}AssessmentInfo"
        self.conn.execute(
            f"INSERT OR REPLACE INTO '{info_table}'(tableName, baseGrade) VALUES(?, ?)",
            (final_table, base_grade),
        )
        self.conn.commit()

    def table_exists(self, table_name: str, course_name: str) -> bool:
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (course_name + table_name,),
        )
        return cursor.fetchone() is not None

    def get_base_grade(self, course_name: str, table_name: str) -> Optional[float]:
        info_table = f"{course_name}AssessmentInfo"
        try:
            cursor = self.conn.execute(
                f"SELECT baseGrade FROM '{info_table}' WHERE tableName = ?",
                (course_name + table_name,),
            )
        except Exception:
            return None
        result = cursor.fetchone()
        return result[0] if result else None

    def _assessment_table_names(self, course_name: str) -> List[str]:
        info_table = f"{course_name}AssessmentInfo"
        try:
            cursor = self.conn.execute(f"SELECT tableName FROM '{info_table}'")
            return [row[0] for row in cursor.fetchall()]
        except Exception:
            logger.info("No AssessmentInfo table yet for course %s", course_name)
            return []

    def finalize(self, course_name: str):
        """Builds a wide table: Sid, SName, <assessment1>_Score, <assessment2>_Score, ..."""
        tables = self._assessment_table_names(course_name)

        students_table = f"{course_name}Students"
        select_clause = f"SELECT '{students_table}'.Sid, '{students_table}'.SName"
        join_clauses = ""
        for table in tables:
            select_clause += f", '{table}'.Score AS '{table}_Score'"
            join_clauses += (
                f" LEFT JOIN '{table}' ON '{students_table}'.Sid = '{table}'.Sid"
            )

        query = select_clause + f" FROM '{students_table}'" + join_clauses + ";"
        logger.debug("finalize() executing: %s", query)
        cursor = self.conn.execute(query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return columns, rows

    def finalize_into_table(self, course_name: str) -> str:
        """Persists the finalized view into a real '<course>Finalized' table.

        Rewritten from the original finalizeTable(), which had a fatal
        'VALUSE' typo and re-created the table on every loop iteration.
        """
        finalized_table = f"{course_name}Finalized"
        columns, rows = self.finalize(course_name)

        column_defs = []
        for col in columns:
            if col in ("Sid",):
                column_defs.append("Sid INTEGER PRIMARY KEY")
            elif col in ("SName",):
                column_defs.append("SName TEXT")
            else:
                column_defs.append(f"'{col}' REAL")

        self.conn.execute(f"DROP TABLE IF EXISTS '{finalized_table}'")
        self.conn.execute(
            f"CREATE TABLE '{finalized_table}'({', '.join(column_defs)})"
        )
        self.conn.commit()

        if rows:
            placeholders = ", ".join(["?"] * len(columns))
            self.conn.executemany(
                f"INSERT INTO '{finalized_table}' VALUES({placeholders})", rows
            )
            self.conn.commit()

        return finalized_table
