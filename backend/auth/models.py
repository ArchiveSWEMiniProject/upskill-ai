"""Authentication models and schemas for UpSkill-AI."""

import re
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)

from backend.database import Base


class UserRole(str, Enum):
    """User roles matching the database enum."""

    STUDENT = "student"
    FACULTY_MENTOR = "faculty_mentor"
    ADMINISTRATOR = "administrator"


class UserAccount(Base):
    """SQLAlchemy model for user_account table."""

    __tablename__ = "user_account"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        SAEnum(UserRole, name="user_role", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MentorAssignment(Base):
    """SQLAlchemy model for mentor_assignment table."""

    __tablename__ = "mentor_assignment"

    assignment_id = Column(Integer, primary_key=True, index=True)
    mentor_id = Column(
        Integer,
        ForeignKey("user_account.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(
        Integer,
        unique=True,
        nullable=False,
    )
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# Pydantic Schemas


class UserResponse(BaseModel):
    """Safe user profile response without password hash."""

    user_id: int
    email: str
    role: UserRole
    is_active: bool = True

    model_config = {"from_attributes": True}


class UserContext(BaseModel):
    """Internal user context extracted from validated token or session."""

    user_id: int
    email: str
    role: UserRole
    is_active: bool = True


class LoginRequest(BaseModel):
    """User login payload. Deliberately unconstrained: a blank or over-long
    value cannot belong to any account, so it gets the same generic 401 as a
    wrong password instead of a 422 naming the field (UP-1)."""

    email: str
    password: str


_EMAIL_PATTERN = re.compile(
    r"^[a-z0-9._%+-]{1,64}@(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$"
)
PASSWORD_MIN, PASSWORD_MAX = 8, 128


class RegisterRequest(BaseModel):
    """Public sign-up (UP-1, REQ-F4-01). Always creates a student account: the
    `role` field is only accepted so that asking for another role can be
    refused explicitly (403), never granted. The student's profile, including
    their name, is created afterwards with POST /api/v1/profile (UP-2)."""

    email: str = Field(..., max_length=120)
    password: str = Field(..., min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    role: UserRole = UserRole.STUDENT

    @field_validator("email")
    @classmethod
    def email_has_valid_format(cls, value: str) -> str:
        email = value.strip().lower()
        if not _EMAIL_PATTERN.match(email):
            raise ValueError("Enter a valid email address")
        return email

    @field_validator("password")
    @classmethod
    def password_is_strong_enough(cls, value: str) -> str:
        """At least 8 characters (checked above) with a letter and a digit. The
        128-character cap bounds the cost of hashing attacker-chosen input."""
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one letter and one digit")
        return value


class TokenResponse(BaseModel):
    """JWT Token response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MenteeSummaryResponse(BaseModel):
    """Summary of an assigned mentee for faculty listing (CA-6, REQ-F4-13)."""

    student_id: int
    user_id: int
    name: str
    email: Optional[str] = None
    education_level: Optional[str] = None
    target_role_id: Optional[int] = None
    target_role_name: Optional[str] = None
    assigned_at: Optional[datetime] = None


class MenteeSkillSummary(BaseModel):
    """Summary of a mentee's skill."""

    skill_id: int
    skill_name: str
    level: str
    source: Optional[str] = None


class MenteeItemSummary(BaseModel):
    """Summary of a mentee's course or project."""

    item_id: int
    item_type: str
    title: str
    description: Optional[str] = None
    grade: Optional[str] = None
    completion_term: Optional[str] = None


class MenteeDetailResponse(BaseModel):
    """Comprehensive view of an assigned mentee (CA-6, REQ-F4-13, REQ-F1-40)."""

    student_id: int
    user_id: int
    name: str
    email: Optional[str] = None
    education_level: Optional[str] = None
    target_role_id: Optional[int] = None
    target_role_name: Optional[str] = None
    assigned_at: Optional[datetime] = None
    skills: list[MenteeSkillSummary] = Field(default_factory=list)
    profile_items: list[MenteeItemSummary] = Field(default_factory=list)

