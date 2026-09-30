from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Milestone(Base):
    __tablename__ = "milestone"
    __table_args__ = (UniqueConstraint("progress_id", "kind", name="uq_milestone_progress_kind"),)

    milestone_id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[str] = mapped_column(String(64), index=True)
    progress_id: Mapped[int] = mapped_column(ForeignKey("progress.progress_id"), index=True)
    kind: Mapped[str] = mapped_column(String(32), default="completed")
    achieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Notification(Base):
    __tablename__ = "notification"

    notification_id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[str] = mapped_column(String(64), index=True)
    progress_id: Mapped[int | None] = mapped_column(
        ForeignKey("progress.progress_id"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="recorded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
