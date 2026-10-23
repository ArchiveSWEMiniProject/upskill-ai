from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.profile.exceptions import ProfileAlreadyExistsError
from backend.profile.models import Student


class StudentRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_by_user_id(self, user_id: int) -> Student | None:
        return self._session.scalars(select(Student).where(Student.user_id == user_id)).first()

    def add(self, student: Student) -> Student:
        """Insert and flush. The unique constraint on user_id is the final guard
        against two concurrent creates for the same account. The insert runs in a
        savepoint, so a failure undoes only this insert, not the caller's other
        work in the same transaction."""
        try:
            with self._session.begin_nested():
                self._session.add(student)
        except IntegrityError as error:
            if "uq_student_user_id" in str(error.orig):
                raise ProfileAlreadyExistsError from error
            raise
        return student
