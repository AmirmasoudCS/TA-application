"""
Cross-assessment analytics for a course: aggregates across every
assessment table rather than the single-table queries the other
repositories focus on.

This composes CourseRepository/StudentRepository/AssessmentRepository/
TARepository rather than duplicating their table-naming logic - it reuses
CourseRepository.list_assessment_tables() to find which assessment tables
exist, and AssessmentRepository's existing column/row helpers to read
them, the same way MainWindow already does for a single table.

Assessments can have different base grades (a 10-point quiz vs. a
50-point problem set), so raw Score isn't directly comparable across
them. Everywhere a comparison across assessments is needed (grader
consistency, a student's progress chart), this uses the "normalized"
score instead: the base-grade-adjusted Calculated value
(StatsService.calculated_score) when a base grade is set, or the raw
score otherwise. AssessmentSummary.normalized_scores/normalized_average
and StudentAssessmentRecord.normalized carry this.

Scope: assessment summaries (Overview + Completion), grader workload, and
per-student lookup. An at-risk list is a planned follow-up, reusing
get_student_summary() for each roster student.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from db.connection import Connection
from db.course_repository import CourseRepository
from db.student_repository import StudentRepository
from db.assessment_repository import AssessmentRepository
from db.ta_repository import TARepository
from services.stats_service import StatsService
from logging_setup import get_logger

logger = get_logger("db.analytics_repository")


@dataclass
class AssessmentSummary:
    table_suffix: str
    base_grade: Optional[float]
    graded_count: int
    roster_size: int
    average: Optional[float]
    highest: Optional[float]
    lowest: Optional[float]
    scores: List[float] = field(default_factory=list)
    normalized_scores: List[float] = field(default_factory=list)

    @property
    def completion_percent(self) -> float:
        if self.roster_size == 0:
            return 0.0
        return round(100 * self.graded_count / self.roster_size, 1)

    @property
    def normalized_average(self) -> Optional[float]:
        if not self.normalized_scores:
            return None
        return round(sum(self.normalized_scores) / len(self.normalized_scores), 2)


@dataclass
class GraderWorkload:
    ta_name: str
    graded_count: int
    average_score_given: Optional[float]


@dataclass
class StudentAssessmentRecord:
    table_suffix: str
    score: Optional[float]
    calculated: Optional[float]
    comment: str
    grader_name: str
    updated_at: Optional[str]
    base_grade: Optional[float]
    normalized: Optional[float]  # same scale as AssessmentSummary.normalized_average
    class_normalized_average: Optional[float]

    @property
    def vs_class_average(self) -> Optional[float]:
        if self.normalized is None or self.class_normalized_average is None:
            return None
        return round(self.normalized - self.class_normalized_average, 2)


@dataclass
class StudentSummary:
    sid: int
    name: str
    records: List[StudentAssessmentRecord]
    average: Optional[float]  # average of `normalized` across records
    assessments_graded: int
    assessments_total: int


class AnalyticsRepository:
    def __init__(self, connection: Connection, courses: CourseRepository,
                 students: StudentRepository, assessments: AssessmentRepository,
                 tas: TARepository):
        self.conn = connection
        self.courses = courses
        self.students = students
        self.assessments = assessments
        self.tas = tas

    def _assessment_suffixes(self, course_name: str) -> List[str]:
        """Strips the course prefix off each full table name, the same
        way MainWindow._finalize_course cleans up column names - so
        callers work with the short names TAs actually type ("Quiz1"),
        not the internal 'COURSEQuiz1' form."""
        full_names = self.courses.list_assessment_tables(course_name)
        return [
            name[len(course_name):] if name.startswith(course_name) else name
            for name in full_names
        ]

    @staticmethod
    def _normalize(score, base_grade: Optional[float]) -> Optional[float]:
        """Converts a raw score to the same 0-100-ish scale as every other
        assessment, so scores from a 10-point quiz and a 50-point problem
        set can be compared/averaged together. Falls back to the raw
        score when there's no base grade to convert against."""
        if not isinstance(score, (int, float)):
            return None
        if base_grade is None:
            return score
        calculated = StatsService.calculated_score(score, base_grade)
        return calculated if isinstance(calculated, (int, float)) else None

    def get_assessment_summaries(self, course_name: str) -> List[AssessmentSummary]:
        """One entry per assessment: base grade, how many of the roster
        have been graded so far, and average/high/low/scores for whoever
        has been graded. Feeds the Overview tab (stats + histogram), the
        Completion tab (graded_count/roster_size), and Student Lookup's
        "vs. class average" comparison (via normalized_average)."""
        roster_size = len(self.students.get_all(course_name))
        summaries = []
        for suffix in self._assessment_suffixes(course_name):
            full_table = course_name + suffix
            base_grade = self.courses.get_base_grade(course_name, suffix)
            try:
                scores_raw = self.assessments.get_column_values(full_table, "Score")
            except Exception:
                logger.warning("Could not read scores from %s for analytics", full_table)
                continue
            numeric_scores = [s for s in scores_raw if isinstance(s, (int, float))]
            normalized_scores = [
                n for n in (self._normalize(s, base_grade) for s in numeric_scores) if n is not None
            ]
            stats = StatsService.compute(numeric_scores, base_grade)
            summaries.append(AssessmentSummary(
                table_suffix=suffix,
                base_grade=base_grade,
                graded_count=len(scores_raw),
                roster_size=roster_size,
                average=stats.average if stats else None,
                highest=stats.highest if stats else None,
                lowest=stats.lowest if stats else None,
                scores=numeric_scores,
                normalized_scores=normalized_scores,
            ))
        return summaries

    def get_grader_workload(self, course_name: str) -> List[GraderWorkload]:
        """How many items each TA has graded across every assessment in
        the course, and their average score given - a consistency check
        across TAs (e.g. one TA's average given is notably lower than the
        rest), not a performance evaluation of any individual TA."""
        totals: Dict[Optional[int], List] = {}
        for suffix in self._assessment_suffixes(course_name):
            full_table = course_name + suffix
            try:
                columns = [c.lower() for c in self.assessments.get_columns(full_table)]
                rows = self.assessments.get_rows(full_table)
            except Exception:
                logger.warning("Could not read %s for grader workload", full_table)
                continue
            if "graderid" not in columns or "score" not in columns:
                continue
            grader_index = columns.index("graderid")
            score_index = columns.index("score")
            for row in rows:
                grader_id = row[grader_index]
                totals.setdefault(grader_id, []).append(row[score_index])

        workloads = []
        for grader_id, scores in totals.items():
            ta = self.tas.get_by_id(grader_id) if grader_id is not None else None
            name = ta.name if ta else "Unknown"
            numeric = [s for s in scores if isinstance(s, (int, float))]
            average = round(sum(numeric) / len(numeric), 2) if numeric else None
            workloads.append(GraderWorkload(ta_name=name, graded_count=len(scores), average_score_given=average))

        workloads.sort(key=lambda w: w.graded_count, reverse=True)
        return workloads

    def list_students(self, course_name: str):
        """Passthrough to StudentRepository.get_all() - lets callers like
        AnalyticsWindow's Student Lookup search dropdown depend on just
        AnalyticsRepository, rather than needing a second repository."""
        return self.students.get_all(course_name)

    def get_student_summary(self, course_name: str, sid: int) -> Optional[StudentSummary]:
        """Every assessment a given student has been graded on: their
        score, the grader, when, and how they compare to the class
        average on that same assessment (on the normalized scale). Only
        includes assessments where this student actually has a row - an
        assessment they haven't been graded on yet is simply absent,
        rather than shown as a zero.

        Returns None if the Sid isn't on this course's roster at all, so
        the caller can tell "not found" apart from "found, but not graded
        on anything yet" (which returns an empty records list).
        """
        name = self.students.get_name(sid, course_name)
        if name is None:
            return None

        class_summaries = {s.table_suffix: s for s in self.get_assessment_summaries(course_name)}
        assessment_suffixes = self._assessment_suffixes(course_name)

        records: List[StudentAssessmentRecord] = []
        for suffix in assessment_suffixes:
            full_table = course_name + suffix
            try:
                columns = [c.lower() for c in self.assessments.get_columns(full_table)]
                candidates = self.assessments.search_by_sid_prefix(full_table, str(sid))
            except Exception:
                logger.warning("Could not read %s for student summary (sid=%s)", full_table, sid)
                continue

            sid_index = columns.index("sid") if "sid" in columns else None
            row = next((r for r in candidates if sid_index is not None and str(r[sid_index]) == str(sid)), None)
            if row is None:
                continue  # not graded on this assessment yet

            score = row[columns.index("score")] if "score" in columns else None
            comment = row[columns.index("comment")] if "comment" in columns else ""
            grader_id = row[columns.index("graderid")] if "graderid" in columns else None
            updated_at = row[columns.index("updatedat")] if "updatedat" in columns else None
            ta = self.tas.get_by_id(grader_id) if grader_id is not None else None

            base_grade = self.courses.get_base_grade(course_name, suffix)
            calculated = StatsService.calculated_score(score, base_grade) if base_grade is not None else None
            calculated = calculated if isinstance(calculated, (int, float)) else None
            normalized = self._normalize(score, base_grade)

            class_summary = class_summaries.get(suffix)

            records.append(StudentAssessmentRecord(
                table_suffix=suffix,
                score=score,
                calculated=calculated,
                comment=comment or "-",
                grader_name=ta.name if ta else "---",
                updated_at=updated_at,
                base_grade=base_grade,
                normalized=normalized,
                class_normalized_average=class_summary.normalized_average if class_summary else None,
            ))

        numeric_normalized = [r.normalized for r in records if r.normalized is not None]
        average = round(sum(numeric_normalized) / len(numeric_normalized), 2) if numeric_normalized else None

        return StudentSummary(
            sid=sid, name=name, records=records, average=average,
            assessments_graded=len(records), assessments_total=len(assessment_suffixes),
        )