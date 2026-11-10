"""Read models for the student's progress dashboard."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.progress.schemas import ProgressOut

NonNegativeCount = Annotated[int, Field(ge=0, strict=True)]


class GapSummary(BaseModel):
    closed: NonNegativeCount
    total: NonNegativeCount

    @model_validator(mode="after")
    def validate_counts(self) -> "GapSummary":
        if self.closed > self.total:
            raise ValueError("Closed gaps cannot exceed the original gap count")
        return self


class ProgressSnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: str
    completion_percentage: int
    occurred_at: datetime


class ResourceProgress(ProgressOut):
    title: str | None
    history: list[ProgressSnapshot]


class Milestone(BaseModel):
    label: str
    achieved_at: datetime | None


class ProgressDashboard(BaseModel):
    resources: list[ResourceProgress]
    completed_count: int
    current_streak_days: int
    milestones: list[Milestone]
    gap_summary: GapSummary | None
    gap_closure_proportion: float | None
