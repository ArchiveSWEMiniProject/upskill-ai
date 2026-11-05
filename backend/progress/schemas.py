"""Request/response fields from SRS Appendix B."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EnrolIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_id: int = Field(gt=0, strict=True)


class ProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    progress_id: int
    resource_id: int
    status: Literal["enrolled", "in-progress", "completed"]
    completion_percentage: int
