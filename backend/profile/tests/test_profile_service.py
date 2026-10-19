"""ProfileService logic with an in-memory repository (no database)."""

import pytest

from backend.profile.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from backend.profile.models import Student
from backend.profile.service import ProfileService


class FakeStudents:
    def __init__(self):
        self.rows: dict[int, Student] = {}

    def get_by_user_id(self, user_id: int) -> Student | None:
        return self.rows.get(user_id)

    def add(self, student: Student) -> Student:
        student.student_id = len(self.rows) + 1
        self.rows[student.user_id] = student
        return student


@pytest.fixture
def service():
    return ProfileService(FakeStudents())


def test_create_links_profile_to_account(service):
    student = service.create_profile(user_id=5, name="Asha", education_level="UG")
    assert (student.user_id, student.name, student.education_level) == (5, "Asha", "UG")


def test_second_create_for_same_account_is_rejected(service):
    service.create_profile(user_id=5, name="Asha", education_level=None)
    with pytest.raises(ProfileAlreadyExistsError):
        service.create_profile(user_id=5, name="Asha again", education_level=None)


def test_get_returns_the_accounts_profile(service):
    created = service.create_profile(user_id=5, name="Asha", education_level=None)
    assert service.get_profile(5) is created


def test_get_without_profile_raises(service):
    with pytest.raises(ProfileNotFoundError):
        service.get_profile(5)


def test_error_messages_match_the_test_plan():
    assert ProfileAlreadyExistsError.message == "Profile already exists"
    assert ProfileNotFoundError.message == "Profile not found"
