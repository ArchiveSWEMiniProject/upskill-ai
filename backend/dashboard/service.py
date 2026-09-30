from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.dashboard.models import Milestone
from backend.dashboard.schemas import DashboardProgress, DashboardRead
from backend.evidence.models import CompletionEvidence
from backend.progress.enums import ProgressStatus, VerificationStatus
from backend.progress.repository import ProgressRepository


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, student_id: str) -> DashboardRead:
        records = ProgressRepository(self.db).list_for_student(student_id)
        evidence_by_progress: dict[int, list[CompletionEvidence]] = {}
        if records:
            evidence_rows = self.db.scalars(
                select(CompletionEvidence).where(
                    CompletionEvidence.progress_id.in_([p.progress_id for p in records])
                )
            ).all()
            for evidence in evidence_rows:
                evidence_by_progress.setdefault(evidence.progress_id, []).append(evidence)
        completed = sum(p.status == ProgressStatus.COMPLETED for p in records)
        percent = sum(p.completion_percentage for p in records) / len(records) if records else 0.0
        milestones = self.db.scalars(
            select(Milestone)
            .where(Milestone.student_id == student_id)
            .order_by(Milestone.achieved_at.desc())
        ).all()
        return DashboardRead(
            enrolments=[
                DashboardProgress(
                    **{
                        field: getattr(progress, field)
                        for field in (
                            "progress_id",
                            "student_id",
                            "resource_id",
                            "status",
                            "completion_percentage",
                            "score",
                            "skill_update_status",
                            "skill_vector_changed",
                            "progress_history",
                            "recommendation_status",
                            "roadmap_version",
                            "created_at",
                            "updated_at",
                            "completed_at",
                        )
                    },
                    evidence_status=(
                        "verified"
                        if any(
                            e.verification_status == VerificationStatus.VERIFIED
                            for e in evidence_by_progress.get(progress.progress_id, [])
                        )
                        else "pending"
                        if evidence_by_progress.get(progress.progress_id)
                        else "not-submitted"
                    ),
                )
                for progress in records
            ],
            completed_count=completed,
            active_count=len(records) - completed,
            progress_percent=round(percent, 2),
            milestones=[
                {
                    "milestone_id": m.milestone_id,
                    "progress_id": m.progress_id,
                    "kind": m.kind,
                    "achieved_at": m.achieved_at,
                }
                for m in milestones
            ],
        )
