from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.progress.enums import ProgressStatus


class EnrolmentCreate(BaseModel):
    resource_id: str = Field(min_length=1, max_length=64)


class ProgressUpdate(BaseModel):
    completion_percentage: int = Field(ge=0, le=100)


class ProgressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    progress_id: int
    student_id: str
    resource_id: str
    status: ProgressStatus
    completion_percentage: int
    score: int | None
    skill_update_status: str
    skill_vector_changed: bool
    progress_history: list[dict]
    recommendation_status: str
    roadmap_version: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class CompletionRead(BaseModel):
    progress: ProgressRead
    skill_vector_changed: bool
    recommendation_status: str
    roadmap_version: str | None
    already_completed: bool = False
