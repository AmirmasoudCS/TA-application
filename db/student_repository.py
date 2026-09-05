"""
Everything about the <course>Students table.

Note: reading a roster .txt file and inserting it is now split across two
layers on purpose:
  - StudentRepository.insert_students(...) — pure DB write, takes already
    parsed (name, sid) tuples.
  - services.roster_import_service.RosterImportService — reads/parses the
    roster .txt file from config.ROSTER_DIRECTORY.

This is the fix for the "exports actually reads rosters" bug: the old
Database.populateStudents() did both file-path resolution (using a
hardcoded, wrong directory) AND DB insertion in one method. Splitting them
means the roster directory is defined in exactly one place (config.py).
"""
from typing import List, Optional, Sequence, Tuple

from db.connection import Connection
from db.models import Student
from logging_setup import get_logger

logger = get_logger("db.student_repository")


class StudentRepository:
    def __init__(self, connection: Connection):
        self.conn = connection

    def insert_students(self, course_name: str, students: Sequence[Tuple[str, int]]) -> int:
        """students: sequence of (name, sid) tuples. Returns number inserted."""
        if not students:
            logger.warning("insert_students called with no students for %s", course_name)
            return 0
        table = f"{course_name}Students"
        query = f'INSERT OR IGNORE INTO "{table}"(SName, Sid) VALUES(?, ?)'
        self.conn.executemany(query, students)
        self.conn.commit()
        logger.info("Inserted %d students into %s", len(students), table)
        return len(students)

    def get_name(self, sid: int, course_name: str) -> Optional[str]:
        table = f"{course_name}Students"
        cursor = self.conn.execute(
            f"SELECT SName FROM '{table}' WHERE Sid = ?", (sid,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def get_all(self, course_name: str) -> List[Student]:
        table = f"{course_name}Students"
        cursor = self.conn.execute(f"SELECT Sid, SName FROM '{table}'")
        return [Student(sid=row[0], name=row[1]) for row in cursor.fetchall()]
