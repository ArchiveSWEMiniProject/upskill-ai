"""Target role selection (UP-13, REQ-F1-31 to F1-34).

A student has at most one active target role, stored on their student row, so
choosing another replaces it. Changing the role marks recommendations stale
(via M2's mark_stale) and the response summarises how many skills the role
requires, how many the student already holds and how many are still a gap.

Role and requirement rows belong to M4 and are read only, through light table
definitions (rule R2: no import of M4's models). The gap count comes from M2's
pure compute_gap(), so this summary always agrees with the roadmap.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import column, select, table
from sqlalchemy.orm import Session

from backend.gap.service import RoleSkillRequirement, compute_gap
from backend.profile.exceptions import ProfileNotFoundError, UnknownRoleError
from backend.profile.models import Student
from backend.profile.repository import StudentRepository
from backend.profile.staleness import mark_stale
from backend.skills.vector import compute_skill_vector

_role = table("career_role", column("role_id"), column("role_name"))
_requirement = table(
    "role_skill_requirement",
    column("role_id"),
    column("skill_id"),
    column("required_level"),
    column("weight"),
)
_skill = table("skill", column("skill_id"), column("skill_name"))


@dataclass(frozen=True)
class TargetRoleSummary:
    role_id: int
    role_name: str
    set_at: datetime | None
    required: int
    held: int
    gap: int


class TargetRoleService:
    def __init__(self, session: Session):
        self._session = session
        self._students = StudentRepository(session)

    def _student(self, user_id: int) -> Student:
        student = self._students.get_by_user_id(user_id)
        if student is None:
            raise ProfileNotFoundError
        return student

    def set_target_role(self, user_id: int, role_id: int) -> TargetRoleSummary:
        """Make role_id the student's one active target role. Choosing the role
        they already have changes nothing and does not mark anything stale."""
        student = self._student(user_id)
        if self._role_name(role_id) is None:
            raise UnknownRoleError
        if student.target_role_id != role_id:
            student.target_role_id = role_id
            student.target_role_set_at = datetime.now(UTC)
            self._session.flush()
            mark_stale(student.student_id)
        return self._summary(student)

    def get_target_role(self, user_id: int) -> TargetRoleSummary | None:
        """The current role with its summary, or None if none is chosen."""
        student = self._student(user_id)
        if student.target_role_id is None:
            return None
        return self._summary(student)

    def _role_name(self, role_id: int) -> str | None:
        return self._session.scalar(select(_role.c.role_name).where(_role.c.role_id == role_id))

    def _requirements(self, role_id: int) -> list[RoleSkillRequirement]:
        rows = self._session.execute(
            select(
                _requirement.c.skill_id,
                _skill.c.skill_name,
                _requirement.c.required_level,
                _requirement.c.weight,
            )
            .join(_skill, _skill.c.skill_id == _requirement.c.skill_id)
            .where(_requirement.c.role_id == role_id)
        )
        return [
            RoleSkillRequirement(role_id, skill_id, name, level, weight)
            for skill_id, name, level, weight in rows
        ]

    def _summary(self, student: Student) -> TargetRoleSummary:
        role_id = student.target_role_id
        requirements = self._requirements(role_id)
        vector = compute_skill_vector(self._session, student.student_id)
        gap = len(compute_gap(vector, requirements))
        return TargetRoleSummary(
            role_id=role_id,
            role_name=self._role_name(role_id),
            set_at=student.target_role_set_at,
            required=len(requirements),
            held=len(requirements) - gap,
            gap=gap,
        )
