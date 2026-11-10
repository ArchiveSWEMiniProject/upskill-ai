"""Reads and writes only M3 progress records."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.progress.models import Progress, ProgressEvent


class ProgressRepository:
    def __init__(self, session: Session):
        self.session = session

    def owned(self, student_id: int, progress_id: int) -> Progress | None:
        """Lock the caller's record for one atomic progress/completion change."""
        return self.session.scalars(select(Progress).where(
            Progress.student_id == student_id, Progress.progress_id == progress_id
        ).with_for_update()).one_or_none()

    def enrol(self, student_id: int, resource_id: int) -> Progress:
        # Retry/double-click safe; the DB also serializes concurrent enrolments.
        inserted = self.session.scalar(
            insert(Progress)
            .values(student_id=student_id, resource_id=resource_id,
                    status="enrolled", completion_percentage=0)
            .on_conflict_do_nothing(constraint="uq_progress_student_resource")
            .returning(Progress.progress_id)
        )
        record = self.session.scalars(select(Progress).where(
            Progress.student_id == student_id, Progress.resource_id == resource_id
        )).one()
        if inserted is not None:
            self.record_event(record)
        return record

    def record_event(self, record: Progress) -> None:
        self.session.add(ProgressEvent(
            progress_id=record.progress_id,
            status=record.status,
            completion_percentage=record.completion_percentage,
        ))
