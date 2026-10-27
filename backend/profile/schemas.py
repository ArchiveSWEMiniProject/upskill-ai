from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

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
