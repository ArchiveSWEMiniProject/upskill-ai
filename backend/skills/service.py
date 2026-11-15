"""Manually declared skills (UP-5), normalised to the taxonomy (UP-9).

Whatever the student types is resolved to exactly one canonical skill
(REQ-F1-19 to F1-21). A skill is stored once per source, so declaring the same
skill again, under any spelling, updates it instead of duplicating it
(REQ-F1-24). Every real change is written to the history (REQ-F1-07).
"""

from dataclasses import dataclass
from typing import Protocol

from backend.profile.exceptions import ProfileNotFoundError
from backend.skills.exceptions import (
    NotACanonicalSkillError,
    UnknownSkillError,
    UnresolvedSkillNotFoundError,
)
from backend.skills.models import StudentSkill, UnresolvedSkill
from backend.taxonomy.resolver import SkillResolver, normalise

MANUAL = "manual"


class Students(Protocol):
    def get_by_user_id(self, user_id: int): ...


class Skills(Protocol):
    def get(self, student_id: int, skill_id: int, source: str) -> StudentSkill | None: ...
    def add(self, entry: StudentSkill) -> bool: ...
    def record_change(self, student_id, skill_id, previous, new, source) -> None: ...


class Unresolved(Protocol):
    def record(self, student_id: int, raw: str, normalised: str) -> UnresolvedSkill: ...
    def list_open(self, student_id: int) -> list[UnresolvedSkill]: ...
    def get(self, student_id: int, unresolved_id: int) -> UnresolvedSkill | None: ...


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
    def __init__(
        self,
        students: Students,
        skills: Skills,
        taxonomy: Taxonomy,
        unresolved: Unresolved | None = None,
    ):
        self._students = students
        self._skills = skills
        self._taxonomy = taxonomy
        self._unresolved = unresolved

    def declare_skill(self, user_id: int, raw_skill: str, level: str) -> DeclaredSkill:
        student = self._student(user_id)
        skill_id = self._resolve(raw_skill, student.student_id)
        name = self._taxonomy.names()[skill_id]
        return self._store(student.student_id, skill_id, name, level)

    def _store(self, student_id: int, skill_id: int, name: str, level: str) -> DeclaredSkill:
        existing = self._skills.get(student_id, skill_id, MANUAL)
        if existing is None:
            entry = StudentSkill(
                student_id=student_id, skill_id=skill_id, source=MANUAL, level=level
            )
            if self._skills.add(entry):
                self._skills.record_change(student_id, skill_id, None, level, MANUAL)
                return DeclaredSkill(skill_id, name, level, MANUAL, created=True, changed=True)
            # Another request inserted it first; fall through and update that row.
            existing = self._skills.get(student_id, skill_id, MANUAL)

        if existing.level == level:
            return DeclaredSkill(skill_id, name, level, MANUAL, created=False, changed=False)
        previous, existing.level = existing.level, level
        self._skills.record_change(student_id, skill_id, previous, level, MANUAL)
        return DeclaredSkill(skill_id, name, level, MANUAL, created=False, changed=True)

    def _resolve(self, raw_skill: str, student_id: int) -> int:
        resolver = self._taxonomy.resolver()
        skill_id = resolver.resolve(raw_skill)
        if skill_id is None:
            names = self._taxonomy.names()
            unresolved_id = None
            if self._unresolved is not None:  # REQ-F1-22: keep what we could not match
                entry = self._unresolved.record(student_id, raw_skill, normalise(raw_skill))
                unresolved_id = entry.unresolved_id
            raise UnknownSkillError(
                raw_skill,
                [(sid, names[sid]) for sid in resolver.suggest(raw_skill)],
                unresolved_id,
            )
        return skill_id

    # --- Unresolved skills (UP-10) -------------------------------------------

    def list_unresolved(self, user_id: int) -> list[tuple[UnresolvedSkill, list[tuple[int, str]]]]:
        """The caller's open unresolved strings, each with its closest canonical
        skills, so the student can be asked to map them (REQ-F1-22)."""
        student = self._student(user_id)
        resolver = self._taxonomy.resolver()
        names = self._taxonomy.names()
        return [
            (entry, [(sid, names[sid]) for sid in resolver.suggest(entry.raw_text)])
            for entry in self._unresolved.list_open(student.student_id)
        ]

    def map_unresolved(
        self, user_id: int, unresolved_id: int, skill_id: int, level: str
    ) -> DeclaredSkill:
        """The student picks the canonical skill an unresolved string meant: the
        skill is declared at that level and the string is closed (REQ-F1-22)."""
        student = self._student(user_id)
        entry = self._unresolved.get(student.student_id, unresolved_id)
        if entry is None or entry.status != "open":
            raise UnresolvedSkillNotFoundError
        name = self._taxonomy.names().get(skill_id)
        if name is None:
            raise NotACanonicalSkillError
        declared = self._store(student.student_id, skill_id, name, level)
        entry.status = "mapped"
        entry.mapped_skill_id = skill_id
        return declared

    def _student(self, user_id: int):
        student = self._students.get_by_user_id(user_id)
        if student is None:
            raise ProfileNotFoundError
        return student
