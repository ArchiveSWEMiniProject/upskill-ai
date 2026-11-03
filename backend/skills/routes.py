from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.profile.dependencies import current_user_id
from backend.profile.exceptions import ProfileNotFoundError
from backend.profile.repository import StudentRepository
from backend.skills.exceptions import UnknownSkillError
from backend.skills.repository import StudentSkillRepository
from backend.skills.schemas import SkillDeclare, SkillOut, SkillSuggestion, UnknownSkillDetail
from backend.skills.service import SkillService
from backend.taxonomy.reader import TaxonomyReader

router = APIRouter(prefix="/api/v1/profile", tags=["skills"])

SessionDep = Annotated[Session, Depends(get_session)]


def skill_service(session: SessionDep) -> SkillService:
    return SkillService(
        StudentRepository(session), StudentSkillRepository(session), TaxonomyReader(session)
    )


@router.post(
    "/skills",
    response_model=SkillOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"model": SkillOut, "description": "Already declared; level updated or unchanged"},
        404: {"description": "The caller has no profile yet"},
        422: {"description": "Unknown skill (with suggestions) or invalid input"},
    },
)
def declare_skill(
    body: SkillDeclare,
    response: Response,
    user_id: Annotated[int, Depends(current_user_id)],
    service: Annotated[SkillService, Depends(skill_service)],
    session: SessionDep,
) -> SkillOut:
    """Declare a skill at a level (REQ-F1-04). The text is resolved to one
    canonical skill; an unknown skill is rejected with the closest matches
    (REQ-F1-05); declaring a skill again never creates a duplicate (REQ-F1-24)."""
    try:
        result = service.declare_skill(user_id, body.skill, body.level)
    except ProfileNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, error.message) from error
    except UnknownSkillError as error:
        detail = UnknownSkillDetail(
            message=f"Unknown skill: {error.raw}",
            suggestions=[SkillSuggestion(skill_id=i, skill_name=n) for i, n in error.suggestions],
        )
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail.model_dump()) from error
    session.commit()
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return SkillOut(
        skill_id=result.skill_id, skill_name=result.skill_name, level=result.level,
        source=result.source,
    )
