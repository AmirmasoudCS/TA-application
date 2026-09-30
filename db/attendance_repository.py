"""
Attendance tracking: a TA creates a named session (e.g. a recitation or
problem session) and marks which roster students were present.

Modeled as two shared tables per course - Sessions and Attendance -
rather than one physical table per session the way assessments work
(db/course_repository.py). A semester can accumulate far more attendance
sessions than graded assessments, and a session doesn't need per-session
structure like a base grade, so one growing Attendance table (SessionId,
Sid) is a better fit than dozens of near-identical per-session tables.

Presence is stored the same way a grade is: a row existing means
"present", no row means "absent" - marking someone present is an
INSERT OR REPLACE, marking them absent is a DELETE. This mirrors exactly
how AssessmentRepository.add_or_replace_item/remove_item already work,
keeping the "row exists = recorded, no row = not recorded" convention
consistent across the whole app instead of inventing a different one
just for attendance.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Set

from db.connection import Connection
from db.ta_repository import TARepository
from logging_setup import get_logger

logger = get_logger("db.attendance_repository")


@dataclass
class Session:
    session_id: int
    name: str
    created_at: Optional[str]
    created_by_name: str


class AttendanceRepository:
    def __init__(self, connection: Connection, tas: TARepository):
        self.conn = connection
        self.tas = tas  # resolves CreatedBy/MarkedBy ids to names for display

    def create_tables(self, course_name: str) -> None:
        sessions_table = f"{course_name}Sessions"
        attendance_table = f"{course_name}Attendance"
        self.conn.execute(
            f"CREATE TABLE IF NOT EXISTS '{sessions_table}'("
            f"SessionId INTEGER PRIMARY KEY AUTOINCREMENT, "
            f"SessionName TEXT NOT NULL, CreatedAt TEXT, CreatedBy INTEGER)"
        )
        self.conn.execute(
            f"CREATE TABLE IF NOT EXISTS '{attendance_table}'("
            f"SessionId INTEGER NOT NULL, Sid INTEGER NOT NULL, "
            f"MarkedBy INTEGER, MarkedAt TEXT, "
            f"PRIMARY KEY (SessionId, Sid), "
            f"FOREIGN KEY(SessionId) REFERENCES '{sessions_table}'(SessionId) ON DELETE CASCADE, "
            f"FOREIGN KEY(Sid) REFERENCES '{course_name}Students'(Sid) ON DELETE CASCADE)"
        )
        self.conn.commit()

    def create_session(self, course_name: str, session_name: str, created_by: Optional[int]) -> int:
        self.create_tables(course_name)
        sessions_table = f"{course_name}Sessions"
        created_at = datetime.now().isoformat(timespec="seconds")
        cursor = self.conn.execute(
            f"INSERT INTO '{sessions_table}'(SessionName, CreatedAt, CreatedBy) VALUES(?, ?, ?)",
            (session_name, created_at, created_by),
        )
        self.conn.commit()
        session_id = cursor.lastrowid
        logger.info("Created attendance session '%s' (id=%s) for %s", session_name, session_id, course_name)
        return session_id

    def list_sessions(self, course_name: str) -> List[Session]:
        self.create_tables(course_name)
        sessions_table = f"{course_name}Sessions"
        cursor = self.conn.execute(
            f"SELECT SessionId, SessionName, CreatedAt, CreatedBy FROM '{sessions_table}' ORDER BY SessionId"
        )
        sessions = []
        for session_id, name, created_at, created_by in cursor.fetchall():
            ta = self.tas.get_by_id(created_by) if created_by is not None else None
            sessions.append(Session(
                session_id=session_id, name=name, created_at=created_at,
                created_by_name=ta.name if ta else "---",
            ))
        return sessions

    def get_present_sids(self, course_name: str, session_id: int) -> Set[int]:
        attendance_table = f"{course_name}Attendance"
        cursor = self.conn.execute(
            f"SELECT Sid FROM '{attendance_table}' WHERE SessionId = ?", (session_id,)
        )
        return {row[0] for row in cursor.fetchall()}

    def mark_present(self, course_name: str, session_id: int, sid: int, marked_by: Optional[int]) -> None:
        attendance_table = f"{course_name}Attendance"
        marked_at = datetime.now().isoformat(timespec="seconds")
        self.conn.execute(
            f"INSERT OR REPLACE INTO '{attendance_table}'(SessionId, Sid, MarkedBy, MarkedAt) VALUES(?, ?, ?, ?)",
            (session_id, sid, marked_by, marked_at),
        )
        self.conn.commit()
        logger.info("Marked Sid %s present for session %s in %s", sid, session_id, course_name)

    def mark_absent(self, course_name: str, session_id: int, sid: int) -> None:
        attendance_table = f"{course_name}Attendance"
        self.conn.execute(
            f"DELETE FROM '{attendance_table}' WHERE SessionId = ? AND Sid = ?", (session_id, sid)
        )
        self.conn.commit()
        logger.info("Marked Sid %s absent for session %s in %s", sid, session_id, course_name)