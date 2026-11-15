from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.skills.models import SkillChangeHistory, StudentSkill, UnresolvedSkill


class StudentSkillRepository:
    def __init__(self, session: Session):
        self._session = session

    def get(self, student_id: int, skill_id: int, source: str) -> StudentSkill | None:
        return self._session.get(StudentSkill, (student_id, skill_id, source))

    def add(self, entry: StudentSkill) -> bool:
        """Insert in a savepoint. Returns False if the row already exists (a
        concurrent request got there first), leaving the transaction usable."""
        try:
            with self._session.begin_nested():
                self._session.add(entry)
        except IntegrityError as error:
            # Rolling back the savepoint already removed `entry` from the session.
            if "pk_student_skill" in str(error.orig):
                return False
            raise
        return True

    def record_change(
        self, student_id: int, skill_id: int, previous: str | None, new: str | None, source: str
    ) -> None:
        self._session.add(
            SkillChangeHistory(
                student_id=student_id,
                skill_id=skill_id,
                previous_level=previous,
                new_level=new,
                source=source,
            )
        )
        self._session.flush()


class UnresolvedSkillRepository:
    """Always scoped to one student: someone else's entry looks like no entry."""

    def __init__(self, session: Session):
        self._session = session

    def record(self, student_id: int, raw: str, normalised: str) -> UnresolvedSkill:
        """Store the string, or return the open entry already holding the same
        text, so asking twice for the same unknown skill never duplicates it."""
        existing = self._session.scalars(
            select(UnresolvedSkill).where(
                UnresolvedSkill.student_id == student_id,
                UnresolvedSkill.normalised_text == normalised,
                UnresolvedSkill.status == "open",
            )
        ).first()
        if existing is not None:
            return existing
        entry = UnresolvedSkill(
            student_id=student_id, raw_text=raw, normalised_text=normalised, status="open"
        )
        self._session.add(entry)
        self._session.flush()
        return entry

    def list_open(self, student_id: int) -> list[UnresolvedSkill]:
        return list(
            self._session.scalars(
                select(UnresolvedSkill)
                .where(UnresolvedSkill.student_id == student_id, UnresolvedSkill.status == "open")
                .order_by(UnresolvedSkill.unresolved_id)
            )
        )

    def get(self, student_id: int, unresolved_id: int) -> UnresolvedSkill | None:
        return self._session.scalars(
            select(UnresolvedSkill).where(
                UnresolvedSkill.student_id == student_id,
                UnresolvedSkill.unresolved_id == unresolved_id,
            )
        ).first()
