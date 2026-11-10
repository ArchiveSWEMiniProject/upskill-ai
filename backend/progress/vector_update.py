"""Send validated completion evidence through M1's vector writer boundary."""

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.orm import Session

from backend.catalogue import get_resource_skill_levels
from backend.evidence.models import CompletionEvidence
from backend.progress.models import Progress
from backend.shared.skill_vector import Level, SkillVector, Source
from backend.skills.vector import get_skill_vector


class SkillVectorWriter(Protocol):
    def __call__(
        self, student_id: int, skill_id: int, level: Level, source: Source, *, session: Session
    ) -> SkillVector:
        """Apply a raise through M1 in the caller's transaction, without committing."""
        ...


def get_skill_vector_writer() -> SkillVectorWriter | None:
    """UP-12 has yet to publish the writer. Leave validated evidence pending."""
    return None


def apply_completion_vector(
    session: Session, progress: Progress, evidence: CompletionEvidence,
    writer: SkillVectorWriter | None,
) -> bool:
    """Apply a pending submission once and report whether the effective vector changed."""
    if writer is None or evidence.vector_applied_at is not None:
        return False
    tags = get_resource_skill_levels(progress.resource_id, session)
    if not tags:
        return False
    before = after = get_skill_vector(progress.student_id, session)
    for skill_id, level in tags.items():
        after = writer(progress.student_id, skill_id, level, Source.completion, session=session)
    evidence.vector_applied_at = datetime.now(UTC)
    return after != before
