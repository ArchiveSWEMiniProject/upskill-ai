"""Request dependencies for M1 routes.

`current_user_id` is a stand-in until M4 delivers login and JWT verification
(UP-1, CA-2). It is disabled unless UPSKILL_DEV_AUTH=1, so a deployment that
forgets to replace it rejects every request instead of trusting a header.
"""

import os
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.profile.repository import StudentRepository
from backend.profile.service import ProfileService

DEV_AUTH_ENV = "UPSKILL_DEV_AUTH"


def current_user_id(
    x_user_id: Annotated[int | None, Header(gt=0)] = None,
) -> int:
    if os.environ.get(DEV_AUTH_ENV) != "1" or x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return x_user_id


def profile_service(session: Annotated[Session, Depends(get_session)]) -> ProfileService:
    return ProfileService(StudentRepository(session))
