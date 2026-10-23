"""Profile use cases (UP-2). The caller's account id always comes from
authentication, never from the request, so a student can only ever reach
their own profile (REQ-F1-39)."""

from backend.profile.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from backend.profile.models import Student
from backend.profile.repository import StudentRepository


class ProfileService:
    def __init__(self, students: StudentRepository):
        self._students = students

    def create_profile(self, user_id: int, name: str, education_level: str | None) -> Student:
        if self._students.get_by_user_id(user_id) is not None:
            raise ProfileAlreadyExistsError
        return self._students.add(
            Student(user_id=user_id, name=name, education_level=education_level)
        )

    def get_profile(self, user_id: int) -> Student:
        student = self._students.get_by_user_id(user_id)
        if student is None:
            raise ProfileNotFoundError
        return student
