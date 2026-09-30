from pydantic import BaseModel

from backend.progress.schemas import ProgressRead


class DashboardProgress(ProgressRead):
    evidence_status: str


class DashboardRead(BaseModel):
    enrolments: list[DashboardProgress]
    completed_count: int
    active_count: int
    progress_percent: float
    milestones: list[dict]
    gaps_closed: int | None = None
    total_gaps: int | None = None
    gaps_status: str = "pending-m2-integration"
    streak_days: int | None = None
    streak_status: str = "criteria-not-defined-in-source-documents"
