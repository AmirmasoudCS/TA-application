"""
Cross-assessment analytics for a course: aggregates across every
assessment table rather than the single-table queries the other
repositories focus on.

This composes CourseRepository/StudentRepository/AssessmentRepository/
TARepository rather than duplicating their table-naming logic - it reuses
CourseRepository.list_assessment_tables() to find which assessment tables
exist, and AssessmentRepository's existing column/row helpers to read
them, the same way MainWindow already does for a single table.

Scope for this first pass: assessment summaries (feeds both the Overview
tab's stats/histogram and the Completion tab's graded-vs-roster numbers)
and grader workload. Per-student lookup and an at-risk list are a planned
follow-up once these are in real use - see ui/windows/analytics_window.py.
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

    @property
    def completion_percent(self) -> float:
        if self.roster_size == 0:
            return 0.0
        return round(100 * self.graded_count / self.roster_size, 1)


@dataclass
class GraderWorkload:
    ta_name: str
    graded_count: int
    average_score_given: Optional[float]


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

    def get_assessment_summaries(self, course_name: str) -> List[AssessmentSummary]:
        """One entry per assessment: base grade, how many of the roster
        have been graded so far, and average/high/low/scores for whoever
        has been graded. Feeds both the Overview tab (stats + histogram)
        and the Completion tab (graded_count/roster_size)."""
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