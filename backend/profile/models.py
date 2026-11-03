"""M1 models. They map onto tables created by the UA-5 migration; see
docs/M1-SCHEMA.md. Only M1 writes these tables (architecture rule R4).

Foreign keys to other modules' tables (user_account, career_role) are left
to the database: declaring them here would require importing M4's models,
which rule R2 forbids.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Student(Base):
    __tablename__ = "student"
    # Read server-set columns (ids, timestamps) back in the INSERT ... RETURNING.
    __mapper_args__ = {"eager_defaults": True}

    student_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String(60))
    education_level: Mapped[str | None] = mapped_column(String(30))
    target_role_id: Mapped[int | None] = mapped_column(Integer)
    target_role_set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProfileItem(Base):
    """A course or project entry (REQ-F1-02, F1-03). The table's check
    constraint enforces the per-type mandatory fields as a final guard."""

    __tablename__ = "profile_item"
    __mapper_args__ = {"eager_defaults": True}

    profile_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(Integer)
    item_type: Mapped[str] = mapped_column(
        ENUM("course", "project", name="profile_item_type", create_type=False)
    )
    title: Mapped[str] = mapped_column(String(100))
    course_code: Mapped[str | None] = mapped_column(String(15))
    grade: Mapped[str | None] = mapped_column(String(3))
    completion_term: Mapped[str | None] = mapped_column(String(10))
    description: Mapped[str | None] = mapped_column(String(2000))
    repository_url: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
