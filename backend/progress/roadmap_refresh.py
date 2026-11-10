"""M3's handoff to M2's published mark_stale operation."""

from typing import Protocol

from sqlalchemy.orm import Session

from backend.evidence.models import CompletionEvidence


class RoadmapInvalidator(Protocol):
    def __call__(self, student_id: int, *, session: Session) -> None:
        """Mark the roadmap stale in the same transaction as the evidence update."""
        ...


def get_roadmap_invalidator() -> RoadmapInvalidator | None:
    """RM-7 has yet to publish the operation and refresh-on-read behavior."""
    return None


def request_roadmap_refresh(
    student_id: int, session: Session, evidence: CompletionEvidence,
    vector_changed: bool, invalidate: RoadmapInvalidator | None,
) -> None:
    if vector_changed:
        evidence.roadmap_refresh_pending = True
    if evidence.roadmap_refresh_pending and invalidate is not None:
        invalidate(student_id, session=session)
        evidence.roadmap_refresh_pending = False
