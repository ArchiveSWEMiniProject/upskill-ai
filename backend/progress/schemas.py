"""Request/response fields from SRS Appendix B."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.evidence.schemas import EvidenceIn


class EnrolIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_id: int = Field(gt=0, strict=True)


class ProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    progress_id: int
    resource_id: int
    status: Literal["enrolled", "in-progress", "completed"]
    completion_percentage: int


class ProgressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    completion_percentage: int = Field(ge=0, le=100, strict=True)


class CompleteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence: EvidenceIn | None = None
