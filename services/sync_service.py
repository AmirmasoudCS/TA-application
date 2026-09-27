"""
File-based sync between TAs' separate local databases, for a group with
no shared server or live network connection (see the app's earlier design
discussions on why a live shared SQLite/Postgres database isn't viable
here: offline grading is a hard requirement, and no one has server
infrastructure to run).

The model: each TA's own local database is the source of truth on their
own machine. "Sync Out" (export_course) writes a single JSON snapshot of
a course's roster and every graded score to a file. "Sync In" (list_sync_
files + import_file) reads other TAs' snapshot files and merges them into
the local database.

Conflict resolution is last-write-wins by UpdatedAt, per (assessment,
Sid) cell - see _incoming_is_newer()'s docstring for the exact rule and
its one known edge case (a true timestamp tie). This works cleanly
because every graded row already carries GraderId/UpdatedAt (see
db/assessment_repository.py).

Grader identity across machines: a TaId is a local auto-increment integer
- "Alice" might be TaId 1 on her machine and TaId 3 on someone else's. So
sync files carry grader NAMES, not raw ids, and import_file() resolves
each name to a local TaId via TARepository.get_or_create() - the same
pattern services/score_import_service.py already uses for a file's
"Grader" column.

Known limitation, stated plainly rather than glossed over: this only
syncs additions and updates, never deletions. If a TA removes a score
locally, a sync file simply won't mention that Sid for that assessment -
which looks identical to "never graded" to anyone importing it, so the
deletion never propagates to other TAs' copies. Properly fixing that
would need a real changelog of operations (including explicit tombstones
for removals), not just a snapshot of current state, which is a
meaningfully bigger design than this first version.
"""
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from logging_setup import get_logger

logger = get_logger("services.sync")

SYNC_FORMAT_VERSION = 1


@dataclass
class SyncFileInfo:
    filepath: str
    course_name: str
    exported_by: str
    exported_at: str
    student_count: int
    assessment_count: int


@dataclass
class SyncImportResult:
    applied: int = 0
    skipped_older: int = 0
    students_added: int = 0
    assessments_created: int = 0
    errors: List[str] = field(default_factory=list)


class SyncService:
    def __init__(self, database, sync_directory: str):
        """database: the app's Database composition root (db/database.py),
        used directly rather than injecting each repository separately -
        sync touches courses/students/assessments/tas together often
        enough that this reads more clearly than five constructor args."""
        self.db = database
        self.sync_directory = sync_directory
        os.makedirs(self.sync_directory, exist_ok=True)

    # ---- Sync Out ----
    def export_course(self, course_name: str, exported_by: str, directory: Optional[str] = None) -> str:
        """Writes the current state of a course (full roster + every
        graded score across every assessment) to a single JSON file."""
        target_dir = directory or self.sync_directory
        os.makedirs(target_dir, exist_ok=True)

        students_payload = [
            {"sid": s.sid, "name": s.name} for s in self.db.students.get_all(course_name)
        ]

        assessments_payload = []
        for suffix in self.db.courses.list_assessment_suffixes(course_name):
            full_table = course_name + suffix
            base_grade = self.db.courses.get_base_grade(course_name, suffix)

            try:
                columns = [c.lower() for c in self.db.assessments.get_columns(full_table)]
                rows_raw = self.db.assessments.get_rows(full_table)
            except Exception:
                logger.warning("Could not read %s for sync export, skipping it", full_table)
                continue

            sid_i = columns.index("sid") if "sid" in columns else None
            score_i = columns.index("score") if "score" in columns else None
            comment_i = columns.index("comment") if "comment" in columns else None
            grader_i = columns.index("graderid") if "graderid" in columns else None
            updated_i = columns.index("updatedat") if "updatedat" in columns else None
            if sid_i is None:
                continue

            rows_payload = []
            for row in rows_raw:
                grader_id = row[grader_i] if grader_i is not None else None
                ta = self.db.tas.get_by_id(grader_id) if grader_id is not None else None
                rows_payload.append({
                    "sid": row[sid_i],
                    "score": row[score_i] if score_i is not None else None,
                    "comment": row[comment_i] if comment_i is not None else "-",
                    "grader_name": ta.name if ta else None,
                    "updated_at": row[updated_i] if updated_i is not None else None,
                })

            assessments_payload.append({
                "table_suffix": suffix,
                "base_grade": base_grade,
                "rows": rows_payload,
            })

        payload = {
            "sync_format_version": SYNC_FORMAT_VERSION,
            "course_name": course_name,
            "exported_by": exported_by,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "students": students_payload,
            "assessments": assessments_payload,
        }

        safe_ta_name = "".join(c for c in exported_by if c.isalnum() or c in ("-", "_")) or "TA"
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"sync_{course_name}_{safe_ta_name}_{timestamp}.json"
        filepath = os.path.join(target_dir, filename)

        # ensure_ascii=False: names with non-Latin characters (e.g.
        # Persian, already a real case elsewhere in this app - see
        # ExportService) stay human-readable in the file instead of
        # turning into \uXXXX escapes.
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        logger.info(
            "Sync Out: exported course %s (by %s) to %s (%d students, %d assessments)",
            course_name, exported_by, filepath, len(students_payload), len(assessments_payload),
        )
        return filepath

    # ---- Sync In ----
    def list_sync_files(self, course_name: str, directory: Optional[str] = None) -> List[SyncFileInfo]:
        """Scans a folder for sync files relevant to this course, without
        importing anything yet - lets the TA see what's there first."""
        target_dir = directory or self.sync_directory
        if not os.path.isdir(target_dir):
            return []

        infos = []
        for filename in sorted(os.listdir(target_dir)):
            if not filename.lower().endswith(".json"):
                continue
            filepath = os.path.join(target_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            except Exception:
                logger.warning("Could not read potential sync file %s, skipping", filepath)
                continue

            if payload.get("sync_format_version") != SYNC_FORMAT_VERSION:
                continue
            if payload.get("course_name") != course_name:
                continue

            infos.append(SyncFileInfo(
                filepath=filepath,
                course_name=payload.get("course_name", ""),
                exported_by=payload.get("exported_by", "Unknown"),
                exported_at=payload.get("exported_at", ""),
                student_count=len(payload.get("students", [])),
                assessment_count=len(payload.get("assessments", [])),
            ))
        return infos

    def import_file(self, filepath: str) -> SyncImportResult:
        """Merges one sync file into the local database. Never raises for
        recoverable problems (a bad file, a bad row) - those go into
        result.errors so the caller can show a summary instead of a
        half-explained crash; only truly unexpected trouble propagates."""
        result = SyncImportResult()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            result.errors.append(f"Could not read {filepath}: {e}")
            return result

        if payload.get("sync_format_version") != SYNC_FORMAT_VERSION:
            result.errors.append(f"{filepath}: unrecognized sync file version")
            return result

        course_name = payload.get("course_name")
        if not course_name:
            result.errors.append(f"{filepath}: missing course name")
            return result

        # Idempotent - safe even if this course's Students table already
        # exists locally, and necessary if a TA is syncing into a course
        # they haven't set up on this machine yet.
        self.db.courses.create_students_table(course_name)

        self._import_students(course_name, payload.get("students", []), result)
        self._import_assessments(course_name, payload.get("assessments", []), result)

        logger.info(
            "Sync In from %s: applied=%d skipped_older=%d students_added=%d "
            "assessments_created=%d errors=%d",
            filepath, result.applied, result.skipped_older, result.students_added,
            result.assessments_created, len(result.errors),
        )
        return result

    def _import_students(self, course_name: str, incoming_students: list, result: SyncImportResult) -> None:
        candidates = [
            (s["name"], s["sid"]) for s in incoming_students
            if isinstance(s, dict) and "sid" in s and "name" in s
        ]
        if not candidates:
            return
        existing_sids = {s.sid for s in self.db.students.get_all(course_name)}
        new_students = [(name, sid) for name, sid in candidates if sid not in existing_sids]
        if new_students:
            self.db.students.insert_students(course_name, new_students)
            result.students_added = len(new_students)

    def _import_assessments(self, course_name: str, incoming_assessments: list, result: SyncImportResult) -> None:
        local_suffixes = set(self.db.courses.list_assessment_suffixes(course_name))

        for assessment in incoming_assessments:
            suffix = assessment.get("table_suffix")
            if not suffix:
                continue
            base_grade = assessment.get("base_grade")

            if suffix not in local_suffixes:
                self.db.courses.create_assessment_table(suffix, course_name, base_grade)
                local_suffixes.add(suffix)
                result.assessments_created += 1
            else:
                local_base = self.db.courses.get_base_grade(course_name, suffix)
                if local_base != base_grade:
                    logger.warning(
                        "Sync: local base grade for %s%s is %s but the incoming file says %s - "
                        "keeping the local value. Base grades aren't merged, only scores; "
                        "fix a mismatched base grade manually if this matters.",
                        course_name, suffix, local_base, base_grade,
                    )

            self._import_assessment_rows(course_name, suffix, assessment.get("rows", []), result)

    def _import_assessment_rows(self, course_name: str, suffix: str, incoming_rows: list,
                                 result: SyncImportResult) -> None:
        full_table = course_name + suffix
        try:
            columns = [c.lower() for c in self.db.assessments.get_columns(full_table)]
            local_rows = {str(r[columns.index("sid")]): r for r in self.db.assessments.get_rows(full_table)}
        except Exception as e:
            result.errors.append(f"{suffix}: could not read local table ({e})")
            return

        updated_i = columns.index("updatedat") if "updatedat" in columns else None

        for row in incoming_rows:
            sid = row.get("sid")
            if sid is None:
                continue

            incoming_updated_at = row.get("updated_at")
            local_row = local_rows.get(str(sid))
            local_updated_at = local_row[updated_i] if (local_row is not None and updated_i is not None) else None

            if local_row is not None and not self._incoming_is_newer(incoming_updated_at, local_updated_at):
                result.skipped_older += 1
                continue

            grader_name = row.get("grader_name")
            grader_id = self.db.tas.get_or_create(grader_name).ta_id if grader_name else None

            try:
                self.db.assessments.add_or_replace_item(
                    full_table, sid, row.get("score"), row.get("comment") or "-",
                    grader_id=grader_id, updated_at=incoming_updated_at,
                )
                result.applied += 1
            except Exception as e:
                result.errors.append(f"{suffix} Sid {sid}: {e}")

    @staticmethod
    def _incoming_is_newer(incoming_updated_at: Optional[str], local_updated_at: Optional[str]) -> bool:
        """Last-write-wins by UpdatedAt (ISO timestamps sort correctly as
        plain strings). A missing timestamp (a row graded before the
        UpdatedAt column existed) counts as infinitely old, so any real
        timestamp beats it.

        A true tie - identical timestamps, or both missing - keeps the
        local value rather than overwriting it with an identical-looking
        one. This is deterministic and never crashes, but has one honest
        edge case: if two TAs' clocks produce the exact same timestamp for
        two different values on the same cell, whichever machine already
        had a value keeps it regardless of which file is imported where -
        so two machines can, in that rare case, stay different from each
        other even after both have synced. Sub-second timestamp
        collisions between different TAs are expected to be rare enough
        in practice not to be worth a more complex resolution scheme.
        """
        if incoming_updated_at is None:
            return False
        if local_updated_at is None:
            return True
        return incoming_updated_at > local_updated_at