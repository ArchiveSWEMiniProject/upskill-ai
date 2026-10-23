from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.profile.dependencies import current_user_id, profile_service
from backend.profile.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from backend.profile.schemas import ProfileCreate, ProfileOut
from backend.profile.service import ProfileService

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])

UserId = Annotated[int, Depends(current_user_id)]
Service = Annotated[ProfileService, Depends(profile_service)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProfileOut)
def create_profile(
    body: ProfileCreate,
    user_id: UserId,
    service: Service,
    session: Annotated[Session, Depends(get_session)],
) -> ProfileOut:
    """Create the caller's profile; an account may have exactly one (REQ-F1-01)."""
    try:
        student = service.create_profile(user_id, body.name, body.education_level)
    except ProfileAlreadyExistsError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, error.message) from error
    session.commit()
    return ProfileOut.model_validate(student)


@router.get("", response_model=ProfileOut)
def get_profile(user_id: UserId, service: Service) -> ProfileOut:
    """Return the caller's own profile; there is no way to name another one (REQ-F1-39)."""
    try:
        return ProfileOut.model_validate(service.get_profile(user_id))
    except ProfileNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, error.message) from error
