"""Architecture section 5.1: POST /progress/enrol."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import UserContext, UserRole, authorize, require_role
from backend.catalogue import get_resource
from backend.dashboard.schemas import ProgressDashboard
from backend.dashboard.service import GapSummaryReader, get_gap_summary_reader, read_dashboard
from backend.database import get_session
from backend.evidence.repository import EvidenceConflict, record_evidence
from backend.profile import get_student_id
from backend.progress.completion import EvidenceRequirement, get_completion_policy
from backend.progress.repository import ProgressRepository
from backend.progress.roadmap_refresh import (
    RoadmapInvalidator,
    get_roadmap_invalidator,
    request_roadmap_refresh,
)
from backend.progress.schemas import CompleteIn, EnrolIn, ProgressOut, ProgressUpdate
from backend.progress.vector_update import (
    SkillVectorWriter,
    apply_completion_vector,
    get_skill_vector_writer,
)

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])
SessionDep = Annotated[Session, Depends(get_session)]


def current_student(
    user: Annotated[UserContext, Depends(require_role(UserRole.STUDENT))],
    session: SessionDep,
) -> int:
    if not authorize(user, "progress:update", {"user_id": user.user_id}, db=session):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    student_id = get_student_id(user.user_id, session)
    if student_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Create a student profile first")
    return student_id


StudentId = Annotated[int, Depends(current_student)]


@router.get("/dashboard", response_model=ProgressDashboard)
def dashboard(
    student_id: StudentId, session: SessionDep,
    gap_reader: Annotated[GapSummaryReader | None, Depends(get_gap_summary_reader)],
) -> ProgressDashboard:
    return read_dashboard(student_id, session, gap_reader)


@router.post("/enrol", response_model=ProgressOut, status_code=status.HTTP_201_CREATED)
def enrol(body: EnrolIn, student_id: StudentId, session: SessionDep) -> ProgressOut:
    if get_resource(body.resource_id, session) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approved resource not found")
    record = ProgressRepository(session).enrol(student_id, body.resource_id)
    session.commit()
    return ProgressOut.model_validate(record)


@router.patch("/{progress_id}", response_model=ProgressOut)
def update_progress(
    progress_id: int, body: ProgressUpdate, student_id: StudentId, session: SessionDep
) -> ProgressOut:
    progress = ProgressRepository(session)
    record = progress.owned(student_id, progress_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Enrolled progress record not found")
    if record.status == "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Completed progress cannot be changed")
    new_status = "enrolled" if body.completion_percentage == 0 else "in-progress"
    if (record.status, record.completion_percentage) != (new_status, body.completion_percentage):
        record.completion_percentage = body.completion_percentage
        # 100% progress remains distinct from the evidence-aware completion operation.
        record.status = new_status
        progress.record_event(record)
    session.commit()
    return ProgressOut.model_validate(record)


@router.post("/{progress_id}/complete", response_model=ProgressOut)
def complete_progress(
    progress_id: int, body: CompleteIn, student_id: StudentId, session: SessionDep,
    policy: Annotated[EvidenceRequirement, Depends(get_completion_policy)],
    vector_writer: Annotated[SkillVectorWriter | None, Depends(get_skill_vector_writer)],
    invalidate: Annotated[RoadmapInvalidator | None, Depends(get_roadmap_invalidator)],
) -> ProgressOut:
    progress = ProgressRepository(session)
    record = progress.owned(student_id, progress_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Enrolled progress record not found")
    if get_resource(record.resource_id, session) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approved resource not found")
    if record.status != "completed":
        requirement = policy(record.resource_id)
        if requirement is None:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Completion is unavailable until this resource's "
                "evidence requirements are confirmed.",
            )
        if requirement and body.evidence is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Submit valid completion evidence before completing this resource.",
            )
        record.status = "completed"
        record.completion_percentage = 100
        progress.record_event(record)
    if body.evidence is not None:
        try:
            evidence = record_evidence(session, record.progress_id, body.evidence)
        except EvidenceConflict as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
        changed = apply_completion_vector(session, record, evidence, vector_writer)
        request_roadmap_refresh(student_id, session, evidence, changed, invalidate)
    session.commit()
    return ProgressOut.model_validate(record)
