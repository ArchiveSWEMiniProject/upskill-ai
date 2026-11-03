"""Request dependencies for M1 routes.

Identity comes from M4: the bearer token is verified by get_current_user, and
the permission decision is M4's central authorize() (CA-1), so M1 holds no
role logic of its own. A student may only manage their own profile; faculty
read mentees through M4's faculty views, never through these routes.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.auth.models import UserContext
from backend.auth.permissions import authorize
from backend.database import get_session
from backend.profile.repository import StudentRepository
from backend.profile.service import ProfileService


def current_user_id(user: Annotated[UserContext, Depends(get_current_user)]) -> int:
    """The caller's user id, if they may manage their own student profile."""
    if not authorize(user, "student:update", resource={"user_id": user.user_id}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can manage a student profile",
        )
    return user.user_id


def profile_service(session: Annotated[Session, Depends(get_session)]) -> ProfileService:
    return ProfileService(StudentRepository(session))
