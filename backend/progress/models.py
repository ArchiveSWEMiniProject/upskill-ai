"""M3-owned progress records (SRS Appendix B; architecture section 4.6)."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Progress(Base):
    __tablename__ = "progress"
    __table_args__ = (
        UniqueConstraint("student_id", "resource_id", name="uq_progress_student_resource"),
        CheckConstraint("completion_percentage BETWEEN 0 AND 100", name="ck_progress_percentage"),
        CheckConstraint(
            "status IN ('enrolled', 'in-progress', 'completed')", name="ck_progress_status"
        ),
    )

    progress_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student.student_id", ondelete="CASCADE"), index=True
    )
    resource_id: Mapped[int] = mapped_column(
        ForeignKey("learning_item.item_id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(15), default="enrolled", server_default="enrolled")
    completion_percentage: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class ProgressEvent(Base):
    """A saved state change, independent of all recommendation identities."""

    __tablename__ = "progress_event"
    __table_args__ = (
        CheckConstraint("completion_percentage BETWEEN 0 AND 100", name="ck_event_percentage"),
        CheckConstraint(
            "status IN ('enrolled', 'in-progress', 'completed')", name="ck_event_status"
        ),
    )

    event_id: Mapped[int] = mapped_column(primary_key=True)
    progress_id: Mapped[int] = mapped_column(
        ForeignKey("progress.progress_id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(15))
    completion_percentage: Mapped[int]
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
