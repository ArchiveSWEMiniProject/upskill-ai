"""M1 skill tables (created by the UA-5 migration; see docs/M1-SCHEMA.md).

student_skill holds one row per student, skill and source; the skill vector
is derived from it (UP-11). skill_change_history is append-only (REQ-F1-07).
Only M1 writes either table (architecture rule R4).
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, func
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base

LEVELS = ("beginner", "intermediate", "advanced")
SOURCES = ("manual", "course", "resume", "completion")

# The Postgres enum types already exist (UA-5); never create them from here.
LevelType = ENUM(*LEVELS, name="skill_level", create_type=False)
SourceType = ENUM(*SOURCES, name="skill_source", create_type=False)


class StudentSkill(Base):
    __tablename__ = "student_skill"
    __mapper_args__ = {"eager_defaults": True}

    student_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    skill_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(SourceType, primary_key=True)
    level: Mapped[str] = mapped_column(LevelType)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SkillChangeHistory(Base):
    __tablename__ = "skill_change_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(Integer)
    skill_id: Mapped[int] = mapped_column(Integer)
    previous_level: Mapped[str | None] = mapped_column(LevelType)
    new_level: Mapped[str | None] = mapped_column(LevelType)
    source: Mapped[str] = mapped_column(SourceType)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
