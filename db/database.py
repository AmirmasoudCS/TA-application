"""
Composition root for the DB layer. Owns one Connection and hands out the
six repositories. This replaces the old monolithic `Database` class from
teacherAssistantAppDB.py — same idea (one thing to construct with a db
path) but delegates actual query logic to focused repository classes.
"""
from db.connection import Connection
from db.course_repository import CourseRepository
from db.student_repository import StudentRepository
from db.assessment_repository import AssessmentRepository
from db.ta_repository import TARepository
from db.analytics_repository import AnalyticsRepository
from db.attendance_repository import AttendanceRepository


class Database:
    def __init__(self, db_path: str):
        self.connection = Connection(db_path)
        self.courses = CourseRepository(self.connection)
        self.students = StudentRepository(self.connection)
        self.assessments = AssessmentRepository(self.connection)
        self.tas = TARepository(self.connection)
        self.tas.create_table()
        # Constructed last since they compose the repositories above
        # rather than talking to the database directly.
        self.analytics = AnalyticsRepository(
            self.connection, self.courses, self.students, self.assessments, self.tas
        )
        self.attendance = AttendanceRepository(self.connection, self.tas)

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()