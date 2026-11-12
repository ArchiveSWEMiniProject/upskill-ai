"""A student's skill gap against their target role (RM-3, REQ-F2-02 to F2-04).

This is where M2 meets the rest of the system: it loads the student's target role
and that role's requirements, asks M1 for the student's skill vector, and hands
them to the pure compute_gap(). The vector arrives as a function, so the logic
can be tested without a database or M1.
"""

from collections.abc import Callable
from dataclasses import dataclass

from backend.gap.exceptions import NoProfileError, NoTargetRoleError
from backend.gap.repository import GapRepository
from backend.gap.service import GapItem, compute_gap
from backend.shared.skill_vector import SkillVector


@dataclass(frozen=True)
class StudentGap:
    role_id: int
    role_name: str
    items: list[GapItem]


class StudentGapService:
    def __init__(self, repository: GapRepository, vector_for: Callable[[int], SkillVector]):
        self._repository = repository
        self._vector_for = vector_for

    def gap_for_user(self, user_id: int) -> StudentGap:
        student = self._repository.student_for_user(user_id)
        if student is None:
            raise NoProfileError
        if student.target_role_id is None:
            raise NoTargetRoleError
        role_name = self._repository.role_name(student.target_role_id)
        if role_name is None:
            raise NoTargetRoleError
        requirements = self._repository.requirements(student.target_role_id)
        vector = self._vector_for(student.student_id)
        return StudentGap(
            role_id=student.target_role_id,
            role_name=role_name,
            items=compute_gap(vector, requirements),
        )
