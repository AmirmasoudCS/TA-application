"""
Composition root for the DB layer. Owns one Connection and hands out the
three repositories. This replaces the old monolithic `Database` class from
teacherAssistantAppDB.py — same idea (one thing to construct with a db
path) but delegates actual query logic to focused repository classes.
"""
from db.connection import Connection
from db.course_repository import CourseRepository
from db.student_repository import StudentRepository
from db.assessment_repository import AssessmentRepository


class Database:
    def __init__(self, db_path: str):
        self.connection = Connection(db_path)
        self.courses = CourseRepository(self.connection)
        self.students = StudentRepository(self.connection)
        self.assessments = AssessmentRepository(self.connection)

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
