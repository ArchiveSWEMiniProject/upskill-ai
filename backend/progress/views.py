"""Architecture section 5.1: POST /progress/enrol."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import UserContext, UserRole, authorize, require_role
from backend.catalogue import get_resource
from backend.database import get_session
from backend.profile import get_student_id
from backend.progress.repository import ProgressRepository
from backend.progress.schemas import EnrolIn, ProgressOut, ProgressUpdate

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
    record = ProgressRepository(session).owned(student_id, progress_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Enrolled progress record not found")
    if record.status == "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Completed progress cannot be changed")
    record.completion_percentage = body.completion_percentage
    # 100% progress does not substitute for the separate evidence-aware completion operation.
    record.status = "enrolled" if body.completion_percentage == 0 else "in-progress"
    session.commit()
    return ProgressOut.model_validate(record)
