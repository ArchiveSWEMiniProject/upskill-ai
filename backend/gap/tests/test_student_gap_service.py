"""RM-3: the student's gap use case, with no database (a fake repository)."""

import pytest

from backend.gap.exceptions import NoProfileError, NoTargetRoleError
from backend.gap.repository import StudentTarget
from backend.gap.service import GapItem, RoleSkillRequirement
from backend.gap.student_gap import StudentGapService
from backend.shared.skill_vector import Level, SkillVector, SkillVectorEntry

USER_ID = 11
STUDENT_ID = 7  # deliberately different from USER_ID
ROLE_ID = 3
PYTHON = 1
SQL = 2

REQUIREMENTS = [
    RoleSkillRequirement(ROLE_ID, PYTHON, "Python", Level.intermediate, weight=5),
    RoleSkillRequirement(ROLE_ID, SQL, "SQL Basics", Level.beginner, weight=3),
]


class FakeRepository:
    """Stands in for GapRepository."""

    def __init__(self, student, role_name="Backend Developer", requirements=()):
        self._student = student
        self._role_name = role_name
        self._requirements = list(requirements)

    def student_for_user(self, user_id):
        return self._student

    def role_name(self, role_id):
        return self._role_name

    def requirements(self, role_id):
        return list(self._requirements)


def build_service(student, vector=None, **repository_options):
    calls = []

    def vector_for(student_id):
        calls.append(student_id)
        return vector if vector is not None else SkillVector()

    return StudentGapService(FakeRepository(student, **repository_options), vector_for), calls


def entry(skill_id, name, level):
    return SkillVectorEntry(skill_id, name, level, confidence=0.8, source="manual")


def test_no_profile_raises():
    service, calls = build_service(student=None)
    with pytest.raises(NoProfileError):
        service.gap_for_user(USER_ID)
    assert calls == []


def test_profile_without_a_target_role_raises():
    service, calls = build_service(student=StudentTarget(STUDENT_ID, None))
    with pytest.raises(NoTargetRoleError):
        service.gap_for_user(USER_ID)
    assert calls == []  # the skill vector is not even requested


def test_a_target_role_that_no_longer_exists_raises():
    service, _ = build_service(student=StudentTarget(STUDENT_ID, ROLE_ID), role_name=None)
    with pytest.raises(NoTargetRoleError):
        service.gap_for_user(USER_ID)


def test_gap_is_computed_for_the_target_role():
    vector = SkillVector((entry(PYTHON, "Python", Level.beginner),))
    service, calls = build_service(
        student=StudentTarget(STUDENT_ID, ROLE_ID), vector=vector, requirements=REQUIREMENTS
    )

    result = service.gap_for_user(USER_ID)

    assert (result.role_id, result.role_name) == (ROLE_ID, "Backend Developer")
    assert result.items == [
        GapItem(
            PYTHON, "Python", Level.intermediate,
            current_level=Level.beginner, weight=5, rank=1
        ),
        GapItem(SQL, "SQL Basics", Level.beginner, current_level=None, weight=3, rank=2),
    ]
    assert calls == [STUDENT_ID]  # the vector is read for the student id, not the user id


def test_gap_is_empty_when_every_requirement_is_met():
    vector = SkillVector(
        (entry(PYTHON, "Python", Level.advanced), entry(SQL, "SQL Basics", Level.beginner))
    )
    service, _ = build_service(
        student=StudentTarget(STUDENT_ID, ROLE_ID), vector=vector, requirements=REQUIREMENTS
    )

    assert service.gap_for_user(USER_ID).items == []
