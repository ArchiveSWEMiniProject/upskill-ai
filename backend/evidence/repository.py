from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.evidence.models import CompletionEvidence


class EvidenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_progress(self, progress_id: int) -> list[CompletionEvidence]:
        return list(
            self.db.scalars(
                select(CompletionEvidence)
                .where(CompletionEvidence.progress_id == progress_id)
                .order_by(CompletionEvidence.submitted_date, CompletionEvidence.evidence_id)
            )
        )

    def get(self, evidence_id: int) -> CompletionEvidence | None:
        return self.db.get(CompletionEvidence, evidence_id)
