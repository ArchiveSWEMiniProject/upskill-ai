from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.progress.models import Progress


class ProgressRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def by_id(self, progress_id: int, student_id: str) -> Progress | None:
        return self.db.scalar(
            select(Progress).where(
                Progress.progress_id == progress_id, Progress.student_id == student_id
            )
        )

    def by_resource(self, resource_id: str, student_id: str) -> Progress | None:
        return self.db.scalar(
            select(Progress).where(
                Progress.resource_id == resource_id, Progress.student_id == student_id
            )
        )

    def list_for_student(self, student_id: str) -> list[Progress]:
        return list(
            self.db.scalars(
                select(Progress)
                .where(Progress.student_id == student_id)
                .order_by(Progress.created_at, Progress.progress_id)
            )
        )

    def save(self, progress: Progress) -> Progress:
        self.db.add(progress)
        self.db.flush()
        return progress
