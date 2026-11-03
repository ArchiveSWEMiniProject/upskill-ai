"""The student's skill vector (UP-11, REQ-F1-25 to F1-28).

The vector is derived from student_skill every time it is asked for, never
stored as its own copy (docs/M1-SCHEMA.md), so every add, edit or removal of a
skill is reflected the next time anyone reads it (REQ-F1-26).

student_skill keeps one row per skill and source. The vector has one entry per
skill: the highest level wins (REQ-F1-28), and the winning row supplies the
entry's source and confidence. Every contributing row stays in student_skill,
so all sources remain recorded. When two sources give the same level, the one
backed by stronger evidence wins: completion, then resume, then course, then
manual (a deterministic rule, so the same rows always give the same vector).

get_skill_vector() is the published interface M2 calls (docs/CONTRACTS.md,
"Internal module interfaces"); it returns the frozen contract types from
backend/shared/skill_vector.py.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import column, select, table
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.profile.models import Student
from backend.shared.skill_vector import (
    Level,
    ProfileNotFoundError,
    SkillVector,
    SkillVectorEntry,
    Source,
)
from backend.skills.models import StudentSkill

# Ties on level go to the source with the stronger evidence.
SOURCE_PRECEDENCE = {Source.completion: 3, Source.resume: 2, Source.course: 1, Source.manual: 0}

# M4's taxonomy table, read only (rule R2: no import of M4's models).
_skill = table("skill", column("skill_id"), column("skill_name"))


@dataclass(frozen=True)
class SkillRow:
    """One student_skill row with its canonical skill name."""

    skill_id: int
    skill_name: str
    source: str
    level: str
    confidence: Decimal | None


def _strength(row: SkillRow) -> tuple[int, int]:
    return Level(row.level).rank, SOURCE_PRECEDENCE[Source(row.source)]


def build_vector(rows: Iterable[SkillRow]) -> SkillVector:
    """Collapse per-source rows into one entry per skill (REQ-F1-28)."""
    winners: dict[int, SkillRow] = {}
    for row in rows:
        current = winners.get(row.skill_id)
        if current is None or _strength(row) > _strength(current):
            winners[row.skill_id] = row
    return SkillVector(
        tuple(
            SkillVectorEntry(
                canonical_skill_id=row.skill_id,
                canonical_skill_name=row.skill_name,
                level=row.level,
                confidence=row.confidence,
                source=row.source,
            )
            for row in winners.values()
        )
    )


def _student_rows(session: Session, student_id: int) -> list[SkillRow]:
    query = (
        select(
            StudentSkill.skill_id,
            _skill.c.skill_name,
            StudentSkill.source,
            StudentSkill.level,
            StudentSkill.confidence,
        )
        .join(_skill, _skill.c.skill_id == StudentSkill.skill_id)
        .where(StudentSkill.student_id == student_id)
    )
    return [SkillRow(*row) for row in session.execute(query)]


def compute_skill_vector(session: Session, student_id: int) -> SkillVector:
    """The vector for an existing student id; raises ProfileNotFoundError if
    there is no such profile (a vector is never returned partial or guessed)."""
    if session.get(Student, student_id) is None:
        raise ProfileNotFoundError(student_id)
    return build_vector(_student_rows(session, student_id))


def get_skill_vector(student_id: int, session: Session | None = None) -> SkillVector:
    """M1's published interface for M2 (REQ-F1-27). Pass the caller's session
    to read inside its transaction; without one, a short-lived session is used."""
    if session is not None:
        return compute_skill_vector(session, student_id)
    own = get_session()
    try:
        return compute_skill_vector(next(own), student_id)
    finally:
        own.close()
