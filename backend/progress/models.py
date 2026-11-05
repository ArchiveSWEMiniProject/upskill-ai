"""M3-owned progress records (SRS Appendix B; architecture section 4.6)."""

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
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
