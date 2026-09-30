from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.dashboard.models import Milestone
from backend.evidence.models import CompletionEvidence
from backend.evidence.schemas import EvidenceCreate
from backend.progress.enums import EvidenceType, ProgressStatus, VerificationStatus
from backend.progress.exceptions import (
    ConflictError,
    DependencyUnavailableError,
    InvalidInputError,
    NotFoundError,
)
from backend.progress.models import Progress
from backend.progress.ports import (
    LearningCataloguePort,
    RecommendationPort,
    SkillVectorPort,
)
from backend.progress.repository import ProgressRepository


class ProgressService:
    def __init__(
        self,
        db: Session,
        catalogue: LearningCataloguePort,
        skill_vector: SkillVectorPort,
        recommendations: RecommendationPort,
    ) -> None:
        self.db = db
        self.repo = ProgressRepository(db)
        self.catalogue = catalogue
        self.skill_vector = skill_vector
        self.recommendations = recommendations

    @staticmethod
    def _record_history(progress: Progress, action: str) -> None:
        progress.progress_history = [
            *progress.progress_history,
            {
                "action": action,
                "status": progress.status.value,
                "completion_percentage": progress.completion_percentage,
                "recorded_at": datetime.now(UTC).isoformat(),
            },
        ]

    def _item(self, resource_id: str):
        try:
            item = self.catalogue.get_learning_item(resource_id)
        except Exception as exc:
            raise DependencyUnavailableError("Learning catalogue is unavailable") from exc
        if item is None:
            raise NotFoundError("Learning resource does not exist")
        return item

    def enrol(self, student_id: str, resource_id: str) -> Progress:
        self._item(resource_id)
        if self.repo.by_resource(resource_id, student_id):
            raise ConflictError("Student is already enrolled in this resource")
        progress = self.repo.save(
            Progress(
                student_id=student_id,
                resource_id=resource_id,
                status=ProgressStatus.ENROLLED,
                completion_percentage=0,
            )
        )
        self._record_history(progress, "enrolled")
        self.db.commit()
        return progress

    def list_enrolments(self, student_id: str) -> list[Progress]:
        return self.repo.list_for_student(student_id)

    def update_progress(self, student_id: str, progress_id: int, percentage: int) -> Progress:
        if not 0 <= percentage <= 100:
            raise InvalidInputError("Completion percentage must be between 0 and 100")
        progress = self.repo.by_id(progress_id, student_id)
        if progress is None:
            raise NotFoundError("Enrolment does not exist")
        if progress.status == ProgressStatus.COMPLETED:
            raise ConflictError("Completed progress cannot be changed")
        changed = progress.completion_percentage != percentage
        progress.completion_percentage = percentage
        if percentage > 0:
            progress.status = ProgressStatus.IN_PROGRESS
        if changed:
            self._record_history(progress, "progress-updated")
        self.db.flush()
        self.db.commit()
        return progress

    def add_evidence(
        self, student_id: str, progress_id: int, data: EvidenceCreate, file_key: str | None = None
    ) -> CompletionEvidence:
        progress = self.repo.by_id(progress_id, student_id)
        if progress is None:
            raise NotFoundError("Enrolment does not exist")
        if progress.status == ProgressStatus.COMPLETED:
            raise ConflictError("Evidence cannot be added after completion")
        item = self._item(progress.resource_id)
        if item.evidence_types and data.evidence_type not in item.evidence_types:
            raise ConflictError("This evidence type is not accepted for the learning resource")
        evidence = CompletionEvidence(
            progress_id=progress.progress_id,
            evidence_type=data.evidence_type,
            evidence_url=data.evidence_url,
            file_key=file_key,
            score=data.score,
            verification_status=VerificationStatus.VERIFIED,
        )
        self.db.add(evidence)
        if data.evidence_type == EvidenceType.QUIZ:
            progress.score = data.score
        self.db.flush()
        self.db.commit()
        return evidence

    def complete(self, student_id: str, progress_id: int) -> dict:
        progress = self.repo.by_id(progress_id, student_id)
        if progress is None:
            raise NotFoundError("Enrolment does not exist")
        already_completed = progress.status == ProgressStatus.COMPLETED
        if not already_completed:
            item = self._item(progress.resource_id)
            evidence = list(
                self.db.query(CompletionEvidence)
                .filter_by(progress_id=progress_id, verification_status=VerificationStatus.VERIFIED)
                .all()
            )
            if item.evidence_required and not evidence:
                raise ConflictError("Valid completion evidence is required")
            if item.evidence_types and not any(
                e.evidence_type in item.evidence_types for e in evidence
            ):
                raise ConflictError("Valid completion evidence is required")
            progress.status = ProgressStatus.COMPLETED
            progress.completion_percentage = 100
            progress.completed_at = datetime.now(UTC)
            progress.skill_update_status = "pending"
            progress.recommendation_status = "pending"
            self._record_history(progress, "completed")
            self.db.add(Milestone(student_id=student_id, progress_id=progress_id, kind="completed"))
            self.db.commit()

        changed = progress.skill_vector_changed
        if progress.skill_update_status != "succeeded":
            item = self._item(progress.resource_id)
            if progress.skill_update_status == "unavailable" and item.skill_outcomes:
                changed = True
            try:
                for outcome in item.skill_outcomes:
                    result = self.skill_vector.apply_vector_update(
                        student_id=student_id,
                        skill_id=outcome.skill_id,
                        level=outcome.level,
                        source="completion",
                    )
                    changed = changed or result.changed
            except Exception as exc:
                progress.skill_update_status = "unavailable"
                self.db.commit()
                raise DependencyUnavailableError("Skill update could not be applied") from exc
            progress.skill_vector_changed = changed
            progress.skill_update_status = "succeeded"
            progress.recommendation_status = "pending" if changed else "unchanged"
            self.db.commit()

        if progress.skill_vector_changed and progress.recommendation_status != "recomputed":
            try:
                recompute = self.recommendations.recompute(student_id)
                progress.recommendation_status = recompute.status
                progress.roadmap_version = recompute.roadmap_version
                self.db.commit()
            except Exception as exc:
                progress.recommendation_status = "unavailable"
                self.db.commit()
                raise DependencyUnavailableError(
                    "Recommendation update could not be requested"
                ) from exc
        return {
            "progress": progress,
            "skill_vector_changed": changed,
            "recommendation_status": progress.recommendation_status,
            "roadmap_version": progress.roadmap_version,
            "already_completed": already_completed,
        }
