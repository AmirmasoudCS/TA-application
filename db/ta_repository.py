"""
Everything about the TAs table: the lookup of grader names to stable ids,
used to stamp GraderId onto assessment rows so it's clear who entered or
last touched a given score.

This is intentionally not an authentication system - there are no
passwords and no login. It exists purely for attribution among a small
trusted team of TAs sharing the app, not for access control. See
ui/windows/ta_select_window.py for how a TA picks/creates their name.
"""
from typing import List, Optional

from db.connection import Connection
from db.models import TA
from logging_setup import get_logger

logger = get_logger("db.ta_repository")


class TARepository:
    def __init__(self, connection: Connection):
        self.conn = connection

    def create_table(self) -> None:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS TAs("
            "TaId INTEGER PRIMARY KEY AUTOINCREMENT, "
            "TaName TEXT UNIQUE NOT NULL)"
        )
        self.conn.commit()

    def get_or_create(self, ta_name: str) -> TA:
        """Returns the existing TA row for this name, or creates one.

        Matching is case-insensitive so 'Jon' and 'jon' resolve to the same
        TA instead of silently creating duplicate grader identities.
        """
        ta_name = ta_name.strip()
        existing = self.get_by_name(ta_name)
        if existing:
            return existing

        self.conn.execute(
            "INSERT INTO TAs(TaName) VALUES(?)", (ta_name,)
        )
        self.conn.commit()
        logger.info("Created new TA entry: %s", ta_name)
        return self.get_by_name(ta_name)

    def get_by_name(self, ta_name: str) -> Optional[TA]:
        cursor = self.conn.execute(
            "SELECT TaId, TaName FROM TAs WHERE TaName = ? COLLATE NOCASE",
            (ta_name.strip(),),
        )
        row = cursor.fetchone()
        return TA(ta_id=row[0], name=row[1]) if row else None

    def get_by_id(self, ta_id: int) -> Optional[TA]:
        cursor = self.conn.execute(
            "SELECT TaId, TaName FROM TAs WHERE TaId = ?", (ta_id,)
        )
        row = cursor.fetchone()
        return TA(ta_id=row[0], name=row[1]) if row else None

    def list_all(self) -> List[TA]:
        cursor = self.conn.execute("SELECT TaId, TaName FROM TAs ORDER BY TaName")
        return [TA(ta_id=row[0], name=row[1]) for row in cursor.fetchall()]