"""
Grade statistics and the score -> calculated-percentage conversion.

Extracted from what used to be inline logic in TAapp.py's showGradeStats()
and the "Calculated" column logic scattered across selectTable() and
filterTreeView().
"""
from dataclasses import dataclass
from typing import List, Optional, Sequence


@dataclass
class GradeStats:
    average: float
    highest: float
    lowest: float
    base_grade: Optional[float] = None

    def as_text(self) -> str:
        if self.base_grade:
            return (
                f"Base Grade: {self.base_grade} | "
                f"Average: {self.average:.2f} | "
                f"Highest: {self.highest:.2f} | "
                f"Lowest: {self.lowest:.2f}"
            )
        return f"Average {self.average:.2f} | Highest: {self.highest:.2f} | Lowest: {self.lowest:.2f}"


class StatsService:
    @staticmethod
    def compute(scores: Sequence, base_grade: Optional[float] = None) -> Optional[GradeStats]:
        numeric_scores: List[float] = [s for s in scores if isinstance(s, (int, float))]
        if not numeric_scores:
            return None
        return GradeStats(
            average=sum(numeric_scores) / len(numeric_scores),
            highest=max(numeric_scores),
            lowest=min(numeric_scores),
            base_grade=base_grade,
        )

    @staticmethod
    def calculated_score(score, base_grade: Optional[float]):
        """Mirrors the old inline `round((score/100)*baseGrade, 2)` logic."""
        if base_grade and isinstance(score, (int, float)):
            return round((score / 100) * base_grade, 2)
        return ""
