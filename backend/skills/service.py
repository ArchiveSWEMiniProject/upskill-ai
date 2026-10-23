"""Manually declared skills (UP-5), normalised to the taxonomy (UP-9).

Whatever the student types is resolved to exactly one canonical skill
(REQ-F1-19 to F1-21). A skill is stored once per source, so declaring the same
skill again, under any spelling, updates it instead of duplicating it
(REQ-F1-24). Every real change is written to the history (REQ-F1-07).
"""

from dataclasses import dataclass
from typing import Protocol

from backend.profile.exceptions import ProfileNotFoundError
from backend.skills.exceptions import UnknownSkillError
from backend.skills.models import StudentSkill
from backend.taxonomy.resolver import SkillResolver

MANUAL = "manual"


class Students(Protocol):
    def get_by_user_id(self, user_id: int): ...


class Skills(Protocol):
    def get(self, student_id: int, skill_id: int, source: str) -> StudentSkill | None: ...
    def add(self, entry: StudentSkill) -> bool: ...
    def record_change(self, student_id, skill_id, previous, new, source) -> None: ...


class Taxonomy(Protocol):
    def names(self) -> dict[int, str]: ...
    def resolver(self) -> SkillResolver: ...


@dataclass(frozen=True)
class DeclaredSkill:
    skill_id: int
    skill_name: str
    level: str
    source: str
    created: bool
    changed: bool


class SkillService:
    def __init__(self, students: Students, skills: Skills, taxonomy: Taxonomy):
        self._students = students
        self._skills = skills
        self._taxonomy = taxonomy

    def declare_skill(self, user_id: int, raw_skill: str, level: str) -> DeclaredSkill:
        student = self._students.get_by_user_id(user_id)
        if student is None:
            raise ProfileNotFoundError
        skill_id = self._resolve(raw_skill)
        name = self._taxonomy.names()[skill_id]

        existing = self._skills.get(student.student_id, skill_id, MANUAL)
        if existing is None:
            entry = StudentSkill(
                student_id=student.student_id, skill_id=skill_id, source=MANUAL, level=level
            )
            if self._skills.add(entry):
                self._skills.record_change(student.student_id, skill_id, None, level, MANUAL)
                return DeclaredSkill(skill_id, name, level, MANUAL, created=True, changed=True)
            # Another request inserted it first; fall through and update that row.
            existing = self._skills.get(student.student_id, skill_id, MANUAL)

        if existing.level == level:
            return DeclaredSkill(skill_id, name, level, MANUAL, created=False, changed=False)
        previous, existing.level = existing.level, level
        self._skills.record_change(student.student_id, skill_id, previous, level, MANUAL)
        return DeclaredSkill(skill_id, name, level, MANUAL, created=False, changed=True)

    def _resolve(self, raw_skill: str) -> int:
        resolver = self._taxonomy.resolver()
        skill_id = resolver.resolve(raw_skill)
        if skill_id is None:
            names = self._taxonomy.names()
            raise UnknownSkillError(
                raw_skill, [(sid, names[sid]) for sid in resolver.suggest(raw_skill)]
            )
        return skill_id
