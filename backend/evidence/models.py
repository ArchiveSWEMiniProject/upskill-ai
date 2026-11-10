"""Evidence submitted for an enrolled resource."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base

EVIDENCE_PAYLOAD_CHECK = (
    "(evidence_type = 'quiz' AND score IS NOT NULL AND score BETWEEN 0 AND 100 "
    "AND evidence_url IS NULL) OR "
    "(evidence_type = 'certificate' AND evidence_url IS NOT NULL AND score IS NULL)"
)


class CompletionEvidence(Base):
    __tablename__ = "completion_evidence"
    __table_args__ = (
        CheckConstraint(EVIDENCE_PAYLOAD_CHECK, name="ck_completion_evidence_payload"),
    )

    evidence_id: Mapped[int] = mapped_column(primary_key=True)
    progress_id: Mapped[int] = mapped_column(
        ForeignKey("progress.progress_id", ondelete="CASCADE"), unique=True
    )
    evidence_type: Mapped[str] = mapped_column(String(20))
    evidence_url: Mapped[str | None] = mapped_column(String(255))
    score: Mapped[int | None]
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    vector_applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
