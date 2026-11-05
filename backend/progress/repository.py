"""Reads and writes only M3 progress records."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.progress.models import Progress


class ProgressRepository:
    def __init__(self, session: Session):
        self.session = session

    def enrol(self, student_id: int, resource_id: int) -> Progress:
        # Retry/double-click safe; the DB also serializes concurrent enrolments.
        self.session.execute(
            insert(Progress)
            .values(student_id=student_id, resource_id=resource_id,
                    status="enrolled", completion_percentage=0)
            .on_conflict_do_nothing(constraint="uq_progress_student_resource")
        )
        return self.session.scalars(select(Progress).where(
            Progress.student_id == student_id, Progress.resource_id == resource_id
        )).one()
