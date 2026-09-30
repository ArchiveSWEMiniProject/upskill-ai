from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.progress.enums import EvidenceType, VerificationStatus


class CompletionEvidence(Base):
    __tablename__ = "completion_evidence"

    evidence_id: Mapped[int] = mapped_column(primary_key=True)
    progress_id: Mapped[int] = mapped_column(ForeignKey("progress.progress_id"), index=True)
    evidence_type: Mapped[EvidenceType] = mapped_column(Enum(EvidenceType, native_enum=False))
    evidence_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, native_enum=False), default=VerificationStatus.VERIFIED
    )
