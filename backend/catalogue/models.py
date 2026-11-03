"""SQLAlchemy models for the resource catalogue (Module 4).

Complies with:
- CONTRACTS.md §2, §3
- REQ-F4-06: Resource types (course, certification, project_idea)
- REQ-F4-07: Required resource fields
- REQ-F4-11: Moderation states (pending, approved, inactive)
"""

from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class LearningItemType(str, Enum):
    """Resource types supported by the catalogue (REQ-F4-06)."""

    COURSE = "course"
    CERTIFICATION = "certification"
    PROJECT_IDEA = "project_idea"


class SkillLevel(str, Enum):
    """Three-level ordered taxonomy level."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ModerationState(str, Enum):
    """Administrative moderation states (REQ-F4-11)."""

    PENDING = "pending"
    APPROVED = "approved"
    INACTIVE = "inactive"


class CareerRole(Base):
    """SQLAlchemy model for career_role table."""

    __tablename__ = "career_role"

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(60), unique=True, nullable=False)
    description = Column(Text, nullable=True)


class Skill(Base):
    """SQLAlchemy model for canonical skill taxonomy."""

    __tablename__ = "skill"

    skill_id = Column(Integer, primary_key=True, autoincrement=True)
    skill_name = Column(String(60), unique=True, nullable=False, index=True)
    category = Column(String(60), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SkillAlias(Base):
    """SQLAlchemy model for skill aliases."""

    __tablename__ = "skill_alias"

    alias_id = Column(Integer, primary_key=True, autoincrement=True)
    skill_id = Column(
        Integer,
        ForeignKey("skill.skill_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias_text = Column(String(120), unique=True, nullable=False)


class LearningItem(Base):
    """SQLAlchemy model for catalogue learning resources."""

    __tablename__ = "learning_item"

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(150), nullable=False)
    description = Column(String(1000), nullable=False)
    item_type = Column(
        SAEnum(
            LearningItemType,
            name="learning_item_type",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    level = Column(
        SAEnum(SkillLevel, name="skill_level", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    duration = Column(String(30), nullable=True)
    source_url = Column(String(255), nullable=False)
    source = Column(String(60), nullable=True)
    moderation_state = Column(
        SAEnum(
            ModerationState,
            name="moderation_state",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        server_default="pending",
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    skills = relationship(
        "LearningItemSkill",
        back_populates="learning_item",
        cascade="all, delete-orphan",
    )


class LearningItemSkill(Base):
    """Join table associating learning items with skills (coverage level)."""

    __tablename__ = "learning_item_skill"

    item_id = Column(
        Integer,
        ForeignKey("learning_item.item_id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id = Column(
        Integer,
        ForeignKey("skill.skill_id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    coverage_level = Column(
        SAEnum(SkillLevel, name="skill_level", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    learning_item = relationship("LearningItem", back_populates="skills")
    skill = relationship("Skill")
