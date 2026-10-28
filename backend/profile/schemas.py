from datetime import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    HttpUrl,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    field_validator,
)

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


# --- Project entries (UP-4) --------------------------------------------------

DESCRIPTION_MAX = 2000
_http_url = TypeAdapter(HttpUrl)

ProjectTitle = CourseName  # same rule: required, at most 100 characters


class ProjectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: ProjectTitle
    description: str
    repository_url: str | None = None

    @field_validator("description")
    @classmethod
    def description_within_limit(cls, value: str) -> str:
        """Required, at most 2000 characters; the error carries the current count
        so the client can show it (REQ-F1-37)."""
        if not value.strip():
            raise ValueError("Description is required")
        if len(value) > DESCRIPTION_MAX:
            raise ValueError(
                f"Description is {len(value)} characters; the maximum is {DESCRIPTION_MAX}"
            )
        return value

    @field_validator("repository_url")
    @classmethod
    def repository_url_is_http(cls, value: str | None) -> str | None:
        """Optional; when given it must be an http(s) URL of at most 255 characters.
        Stored as entered, not rewritten."""
        if value is None or not value.strip():
            return None
        url = value.strip()
        if len(url) > 255:
            raise ValueError("Repository URL must be at most 255 characters")
        try:
            _http_url.validate_python(url)
        except ValidationError:
            raise ValueError("Repository URL must be a valid http(s) address") from None
        return url


class ProjectOut(BaseModel):
    project_id: int
    title: str
    description: str
    repository_url: str | None


# --- Resume upload (UP-6) ----------------------------------------------------


class ResumeOut(BaseModel):
    upload_id: int
    file_name: str
    file_type: str
    size_bytes: int
    status: str  # extracted | unreadable | failed
    message: str | None = None
    manual_entry: str | None = None  # where to add skills instead (REQ-F1-11)
    uploaded_at: datetime
    delete_after: datetime
    deleted: bool
