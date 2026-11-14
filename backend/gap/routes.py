from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.auth.models import UserContext
from backend.auth.permissions import authorize
from backend.database import get_session
from backend.gap.exceptions import NoProfileError, NoTargetRoleError
from backend.gap.repository import GapRepository
from backend.gap.schemas import GapItemOut, GapOut
from backend.gap.student_gap import StudentGapService
from backend.shared.skill_vector import SkillVector
from backend.skills.vector import get_skill_vector

router = APIRouter(prefix="/api/v1/roadmap", tags=["roadmap"])

SessionDep = Annotated[Session, Depends(get_session)]


def student_user_id(user: Annotated[UserContext, Depends(get_current_user)]) -> int:
    """The caller's user id, if M4's authorize() lets them read their own gap."""
    if not authorize(user, "gap:read", resource={"user_id": user.user_id}):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only students have a skill gap")
    return user.user_id


def vector_provider(session: SessionDep) -> Callable[[int], SkillVector]:
    """M1's get_skill_vector(), bound to this request's session (REQ-F1-27)."""

    def vector_for(student_id: int) -> SkillVector:
        return get_skill_vector(student_id, session)

    return vector_for


VectorFor = Annotated[Callable[[int], SkillVector], Depends(vector_provider)]


def gap_service(session: SessionDep, vector_for: VectorFor) -> StudentGapService:
    return StudentGapService(GapRepository(session), vector_for)


@router.get(
    "/gap",
    response_model=GapOut,
    responses={
        404: {"description": "The caller has no profile yet"},
        409: {"description": "The caller has not chosen a target role"},
    },
)
def read_gap(
    user_id: Annotated[int, Depends(student_user_id)],
    service: Annotated[StudentGapService, Depends(gap_service)],
) -> GapOut:
    """The caller's skill gap against their target role, most important first
    (REQ-F2-02 to F2-04). Computed from the current skill vector on every request."""
    try:
        gap = service.gap_for_user(user_id)
    except NoProfileError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, error.message) from error
    except NoTargetRoleError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, error.message) from error
    return GapOut(
        role_id=gap.role_id,
        role_name=gap.role_name,
        items=[
            GapItemOut(
                rank=item.rank,
                skill_id=item.skill_id,
                skill_name=item.skill_name,
                required_level=item.required_level,
                current_level=item.current_level,
                weight=item.weight,
            )
            for item in gap.items
        ],
    )
