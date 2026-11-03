from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.skills.models import SkillChangeHistory, StudentSkill


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
