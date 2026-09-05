"""
Lightweight domain models. Kept as plain dataclasses — no ORM — since the
app's SQL access pattern (dynamic table-per-course-per-assessment) doesn't
map cleanly onto a traditional ORM without a much bigger rewrite.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Student:
    sid: int
    name: str


@dataclass
class ScoreEntry:
    sid: int
    score: Optional[float]
    comment: str = "-"


@dataclass
class AssessmentInfo:
    table_name: str
    base_grade: Optional[float]
