from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Integer, String, UniqueConstraint, func
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.progress.enums import ProgressStatus


class Progress(Base):
    __tablename__ = "progress"
    __table_args__ = (
        UniqueConstraint("student_id", "resource_id", name="uq_progress_student_resource"),
    )

    progress_id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[str] = mapped_column(String(64), index=True)
    resource_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[ProgressStatus] = mapped_column(
        Enum(ProgressStatus, native_enum=False), default=ProgressStatus.ENROLLED
    )
    completion_percentage: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skill_update_status: Mapped[str] = mapped_column(String(32), default="not-requested")
    skill_vector_changed: Mapped[bool] = mapped_column(default=False)
    progress_history: Mapped[list[dict]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    recommendation_status: Mapped[str] = mapped_column(String(32), default="not-requested")
    roadmap_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
