"""
Reads class-roster .txt files (one "Name... Sid" per line) from
config.ROSTER_DIRECTORY and parses them into (name, sid) tuples ready for
StudentRepository.insert_students().

This is the fix for the original bug: the files under what used to be
called "exports/" (e.g. exports/DSA4042s.txt) are rosters used to populate
a course's student list, not actual exports. They now live under
config.ROSTER_DIRECTORY (data/rosters/), and real exports (CSV/Excel of
grades) go to config.EXPORT_DIRECTORY (data/exports/) via export_service.py.
"""
import os
from typing import List, Tuple

from config import ROSTER_DIRECTORY
from logging_setup import get_logger

logger = get_logger("services.roster_import")


class RosterImportError(Exception):
    pass


class RosterImportService:
    def __init__(self, roster_directory: str = ROSTER_DIRECTORY):
        self.roster_directory = roster_directory

    def list_rosters(self) -> List[str]:
        """Filenames available to pick from at course setup."""
        if not os.path.isdir(self.roster_directory):
            return []
        return sorted(
            f for f in os.listdir(self.roster_directory) if f.lower().endswith(".txt")
        )

    def parse_roster_file(self, filename: str) -> List[Tuple[str, int]]:
        full_path = os.path.join(self.roster_directory, filename)
        if not os.path.isfile(full_path):
            raise RosterImportError(f"Roster file not found: {full_path}")

        students: List[Tuple[str, int]] = []
        with open(full_path, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                parts = line.strip().split()
                if len(parts) < 2:
                    logger.warning(
                        "Skipping malformed roster line %d in %s: %r",
                        line_number, filename, line.strip(),
                    )
                    continue
                *name_parts, sid_str = parts
                name = " ".join(name_parts)
                try:
                    sid = int(sid_str)
                except ValueError:
                    logger.warning(
                        "Skipping roster line %d in %s: last token %r is not a valid Sid",
                        line_number, filename, sid_str,
                    )
                    continue
                students.append((name, sid))

        if not students:
            logger.warning("No valid student rows found in roster file %s", filename)

        return students
