"""Record evidence while the caller holds the owning progress row lock."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.evidence.models import CompletionEvidence
from backend.evidence.schemas import CertificateIn, EvidenceIn, QuizIn


class EvidenceConflict(Exception):
    """A different submission already exists for the same enrolment."""


def record_evidence(session: Session, progress_id: int, data: EvidenceIn) -> CompletionEvidence:
    url = str(data.evidence_url) if isinstance(data, CertificateIn) else None
    score = data.score if isinstance(data, QuizIn) else None
    previous = session.scalar(select(CompletionEvidence).where(
        CompletionEvidence.progress_id == progress_id
    ))
    if previous is not None:
        if (previous.evidence_type, previous.evidence_url, previous.score) != (
            data.evidence_type, url, score
        ):
            raise EvidenceConflict("Different evidence has already been recorded")
        return previous
    record = CompletionEvidence(
        progress_id=progress_id, evidence_type=data.evidence_type, evidence_url=url, score=score
    )
    session.add(record)
    return record
