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
