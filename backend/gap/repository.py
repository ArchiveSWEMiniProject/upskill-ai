"""Read-only queries behind the student's gap (RM-3).

Other modules' tables are read through lightweight table constructs, never by
importing their models (rule R2), as backend/skills/vector.py does for `skill`.
"""

from dataclasses import dataclass

from sqlalchemy import column, select, table
from sqlalchemy.orm import Session

from backend.gap.service import RoleSkillRequirement

_student = table("student", column("student_id"), column("user_id"), column("target_role_id"))
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
class StudentTarget:
    student_id: int
    target_role_id: int | None


class GapRepository:
    def __init__(self, session: Session):
        self._session = session

    def student_for_user(self, user_id: int) -> StudentTarget | None:
        row = self._session.execute(
            select(_student.c.student_id, _student.c.target_role_id).where(
                _student.c.user_id == user_id
            )
        ).first()
        return None if row is None else StudentTarget(row.student_id, row.target_role_id)

    def role_name(self, role_id: int) -> str | None:
        return self._session.execute(
            select(_role.c.role_name).where(_role.c.role_id == role_id)
        ).scalar()

    def requirements(self, role_id: int) -> list[RoleSkillRequirement]:
        query = (
            select(
                _requirement.c.skill_id,
                _skill.c.skill_name,
                _requirement.c.required_level,
                _requirement.c.weight,
            )
            .select_from(_requirement)
            .join(_skill, _skill.c.skill_id == _requirement.c.skill_id)
            .where(_requirement.c.role_id == role_id)
        )
        return [
            RoleSkillRequirement(
                role_id=role_id,
                skill_id=row.skill_id,
                skill_name=row.skill_name,
                required_level=row.required_level,
                weight=row.weight,
            )
            for row in self._session.execute(query)
        ]
