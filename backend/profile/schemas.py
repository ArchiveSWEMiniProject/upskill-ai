from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints, field_validator

# Lengths from SRS Appendix B. Surrounding whitespace is stripped first, so a
# name of only spaces counts as empty (REQ-F1-35).
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
EducationLevel = Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)]


class ProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    education_level: EducationLevel | None = None


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    name: str
    education_level: str | None
    target_role_id: int | None
    created_at: datetime


# --- Course entries (UP-3) ---------------------------------------------------

LETTER_GRADES = frozenset("SABCDEF")


def normalise_grade(value: str) -> str:
    """A letter grade from {S, A, B, C, D, E, F} or a whole percentage 0-100
    (SRS Appendix B); anything else is invalid (REQ-F1-36)."""
    grade = value.strip().upper()
    if grade in LETTER_GRADES:
        return grade
    if grade.isdigit() and 0 <= int(grade) <= 100:
        return str(int(grade))
    raise ValueError("Grade must be one of S, A, B, C, D, E, F or a whole number from 0 to 100")


CourseName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
CourseCode = Annotated[str, StringConstraints(strip_whitespace=True, max_length=15)]
Term = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]
Grade = Annotated[str, AfterValidator(normalise_grade)]


class CourseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    course_name: CourseName
    course_code: CourseCode | None = None
    grade: Grade
    completion_term: Term

    @field_validator("course_code")
    @classmethod
    def blank_code_is_none(cls, value: str | None) -> str | None:
        return value or None


class CourseOut(BaseModel):
    course_id: int
    course_name: str
    course_code: str | None
    grade: str
    completion_term: str
