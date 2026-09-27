"""
Everything about the TAs table: the lookup of grader names to stable ids,
used to stamp GraderId onto assessment rows so it's clear who entered or
last touched a given score.

This is intentionally not an authentication system - there are no
passwords and no login. It exists purely for attribution among a small
trusted team of TAs sharing the app, not for access control. See
ui/windows/ta_select_window.py for how a TA picks/creates their name.

TaId is derived from hash(name, this machine) rather than an
auto-increment counter - see _compute_ta_id()'s docstring for why, and
for the one deliberate consequence (the same person grading on two
different machines gets two different ids, one per machine). This is why
services/sync_service.py matches graders across machines by NAME, never
by this id: the id is meant to be stable and collision-resistant on one
machine, not portable across different ones.
"""
import hashlib
import uuid
from typing import List, Optional

from db.connection import Connection
from db.models import TA
from logging_setup import get_logger

logger = get_logger("db.ta_repository")


def _machine_id() -> int:
    """A reasonably stable per-machine identifier. uuid.getnode() is
    typically derived from a network interface's MAC address, so it stays
    the same across app reinstalls or a wiped/recreated TAs table on the
    same physical machine - exactly the property _compute_ta_id() needs."""
    return uuid.getnode()


class TARepository:
    def __init__(self, connection: Connection):
        self.conn = connection

    def create_table(self) -> None:
        # No AUTOINCREMENT: TaId is supplied explicitly by get_or_create()
        # via _compute_ta_id() rather than assigned by SQLite. Plain
        # "INTEGER PRIMARY KEY" still accepts any integer we provide,
        # including a large hash-derived one.
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS TAs("
            "TaId INTEGER PRIMARY KEY, "
            "TaName TEXT UNIQUE NOT NULL)"
        )
        self.conn.commit()

    @staticmethod
    def _compute_ta_id(ta_name: str) -> int:
        """Derives a TaId from (name, this machine) instead of an
        auto-increment counter: the same name typed on this same machine
        always produces the same id, even across a reinstall or a wiped
        TAs table - an auto-increment counter can't offer that, since a
        fresh counter starting from 1 again could silently collide with
        old GraderId references still sitting in assessment tables.

        Collision risk between two different real people's names is not
        a practical concern at this size: truncated to 60 bits, roughly a
        billion distinct names would be needed before there's even a 50%
        chance of ANY collision at all (the birthday bound) - nowhere
        close to how many TAs a course will ever have. get_or_create()
        still handles the (conceptually different, and actually expected)
        case where the SAME name legitimately maps back to an existing id
        - see its docstring.

        Deliberate limitation: since the machine identifier is part of
        the hash, the same person grading from two different machines
        gets two different ids, one per machine. That's fine for this
        app's model (a TA uses one machine for the semester) and is
        exactly why cross-machine sync (services/sync_service.py) matches
        graders by NAME, never by this id.
        """
        normalized = ta_name.strip().lower()
        raw = f"{normalized}|{_machine_id()}".encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        # 15 hex chars = 60 bits, comfortably inside SQLite's signed
        # 64-bit INTEGER range (max ~9.2e18) with room to spare.
        return int(digest[:15], 16)

    def get_or_create(self, ta_name: str) -> TA:
        """Returns the existing TA row for this name, or creates one.

        Matching is case-insensitive so 'Jon' and 'jon' resolve to the
        same TA instead of silently creating duplicate grader identities.

        Since TaId is now derived from the name itself (see
        _compute_ta_id), there's an edge case worth handling explicitly:
        if this TA was renamed earlier (rename() keeps the same TaId) and
        their OLD name reappears later - e.g. from an old sync file, or
        someone just typing the old name out of habit - computing the id
        for that old name lands on the exact id their renamed record
        already occupies. Rather than fail with a duplicate-primary-key
        error, that's treated as a match: the id computed from a name is
        strong evidence it's the same underlying grader identity as
        before the rename, so the existing (renamed) record is reused.
        """
        ta_name = ta_name.strip()
        existing = self.get_by_name(ta_name)
        if existing:
            return existing

        ta_id = self._compute_ta_id(ta_name)
        existing_by_id = self.get_by_id(ta_id)
        if existing_by_id:
            logger.info(
                "get_or_create('%s') matched existing TA id=%s (currently named '%s') "
                "by id - likely renamed since it was first created.",
                ta_name, existing_by_id.ta_id, existing_by_id.name,
            )
            return existing_by_id

        self.conn.execute(
            "INSERT INTO TAs(TaId, TaName) VALUES(?, ?)", (ta_id, ta_name)
        )
        self.conn.commit()
        logger.info("Created new TA entry: %s (id=%s)", ta_name, ta_id)
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

    def rename(self, ta_id: int, new_name: str) -> TA:
        """Renames an existing TA in place (e.g. fixing a typo), keeping
        the same TaId so past GraderId references on assessment rows
        still resolve correctly. Raises ValueError if new_name is already
        used by a different TA."""
        new_name = new_name.strip()
        conflict = self.get_by_name(new_name)
        if conflict and conflict.ta_id != ta_id:
            raise ValueError(f"'{new_name}' is already used by another TA.")

        self.conn.execute(
            "UPDATE TAs SET TaName = ? WHERE TaId = ?", (new_name, ta_id)
        )
        self.conn.commit()
        logger.info("Renamed TA %d to %s", ta_id, new_name)
        return self.get_by_id(ta_id)

    def list_all(self) -> List[TA]:
        cursor = self.conn.execute("SELECT TaId, TaName FROM TAs ORDER BY TaName")
        return [TA(ta_id=row[0], name=row[1]) for row in cursor.fetchall()]