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
from backend.profile.staleness import mark_stale
from backend.shared.skill_vector import (
    InvalidSkillVectorError,
    Level,
    ProfileNotFoundError,
    SkillVector,
    SkillVectorEntry,
    Source,
)
from backend.skills.models import StudentSkill
from backend.skills.repository import StudentSkillRepository

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


# --- UP-12: accepting skill vector updates (REQ-F1-29, F1-30, ADR-04) ---------


@dataclass(frozen=True)
class VectorUpdate(SkillVector):
    """What apply_vector_update() returns: the student's vector after the call
    (the frozen contract's SkillVector) plus whether the call changed it."""

    changed: bool = False


def apply_vector_update(
    student_id: int,
    skill_id: int,
    level: Level | str,
    source: Source | str = Source.completion,
    session: Session | None = None,
) -> VectorUpdate:
    """M1's published interface for M3 (docs/CONTRACTS.md; ADR-04: M1 is the
    only writer of the skill vector).

    The skill's level is raised only if `level` is higher than the level the
    student currently holds from any source (REQ-F1-29). An equal or lower
    level is a no-op: nothing is written and nothing is raised (TC-F1-11).
    A raise is stored as the `source` row for that skill, written to
    skill_change_history, and marks recommendations stale (REQ-F1-30).

    Pass the caller's session to apply the update inside its transaction (it
    is flushed, not committed). Without one, a short-lived session is used and
    committed. Raises ProfileNotFoundError for an unknown student and
    InvalidSkillVectorError for an unknown skill, level or source.
    """
    if session is not None:
        return _apply(session, student_id, skill_id, level, source)
    own = get_session()
    db = next(own)
    try:
        result = _apply(db, student_id, skill_id, level, source)
        db.commit()
        return result
    finally:
        own.close()


def _apply(session: Session, student_id, skill_id, level, source) -> VectorUpdate:
    incoming = Level(_coerce(Level, level, "level"))
    source = Source(_coerce(Source, source, "source"))
    # Lock the student's row so two updates for the same student apply one
    # after the other and neither can lose the other's level (ADR-04).
    student = session.get(Student, student_id, with_for_update=True)
    if student is None:
        raise ProfileNotFoundError(student_id)
    if session.scalar(select(_skill.c.skill_id).where(_skill.c.skill_id == skill_id)) is None:
        raise InvalidSkillVectorError(f"skill {skill_id!r} is not in the taxonomy")

    held = compute_skill_vector(session, student_id).get(skill_id)
    if held is not None and incoming <= held.level:
        return VectorUpdate(compute_skill_vector(session, student_id).entries, changed=False)

    skills = StudentSkillRepository(session)
    row = skills.get(student_id, skill_id, source.value)
    previous = None if row is None else row.level
    if row is None:
        row = StudentSkill(
            student_id=student_id, skill_id=skill_id, source=source.value, level=incoming.value
        )
        session.add(row)
    else:
        row.level = incoming.value
    session.flush()
    skills.record_change(student_id, skill_id, previous, incoming.value, source.value)
    mark_stale(student_id)
    return VectorUpdate(compute_skill_vector(session, student_id).entries, changed=True)


def _coerce(enum_type, value, field: str):
    try:
        return enum_type(value)
    except ValueError:
        allowed = ", ".join(member.value for member in enum_type)
        raise InvalidSkillVectorError(
            f"{field} must be one of: {allowed} (got {value!r})"
        ) from None
