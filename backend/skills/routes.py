from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.profile.dependencies import current_user_id
from backend.profile.exceptions import ProfileNotFoundError
from backend.profile.repository import StudentRepository
from backend.skills.exceptions import (
    NotACanonicalSkillError,
    UnknownSkillError,
    UnresolvedSkillNotFoundError,
)
from backend.skills.repository import StudentSkillRepository, UnresolvedSkillRepository
from backend.skills.schemas import (
    SkillDeclare,
    SkillOut,
    SkillSuggestion,
    SkillVectorEntryOut,
    SkillVectorOut,
    UnknownSkillDetail,
    UnresolvedMap,
    UnresolvedSkillOut,
)
from backend.skills.service import SkillService
from backend.skills.vector import compute_skill_vector
from backend.taxonomy.reader import TaxonomyReader

router = APIRouter(prefix="/api/v1/profile", tags=["skills"])

SessionDep = Annotated[Session, Depends(get_session)]


def skill_service(session: SessionDep) -> SkillService:
    return SkillService(
        StudentRepository(session),
        StudentSkillRepository(session),
        TaxonomyReader(session),
        UnresolvedSkillRepository(session),
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
            unresolved_id=error.unresolved_id,
        )
        session.commit()  # keep the unresolved string even though the request fails
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail.model_dump()) from error
    session.commit()
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return SkillOut(
        skill_id=result.skill_id, skill_name=result.skill_name, level=result.level,
        source=result.source,
    )


@router.get(
    "/skill-vector",
    response_model=SkillVectorOut,
    responses={404: {"description": "The caller has no profile yet"}},
)
def read_skill_vector(
    user_id: Annotated[int, Depends(current_user_id)], session: SessionDep
) -> SkillVectorOut:
    """The caller's skill vector in the frozen contract format (REQ-F1-25, F1-27):
    one entry per skill at the highest level any source gives it (REQ-F1-28).
    Computed from the current skills on every request (REQ-F1-26)."""
    student = StudentRepository(session).get_by_user_id(user_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, ProfileNotFoundError.message)
    vector = compute_skill_vector(session, student.student_id)
    return SkillVectorOut(
        entries=[
            SkillVectorEntryOut(
                canonical_skill_id=entry.canonical_skill_id,
                canonical_skill_name=entry.canonical_skill_name,
                level=entry.level.value,
                confidence=None if entry.confidence is None else float(entry.confidence),
                source=entry.source.value,
            )
            for entry in vector
        ]
    )


# --- Unresolved skills (UP-10, REQ-F1-22) -------------------------------------


@router.get("/skills/unresolved", response_model=list[UnresolvedSkillOut])
def list_unresolved_skills(
    user_id: Annotated[int, Depends(current_user_id)],
    service: Annotated[SkillService, Depends(skill_service)],
) -> list[UnresolvedSkillOut]:
    """Skill strings we could not match, each with the closest real skills, for
    the student to map."""
    try:
        found = service.list_unresolved(user_id)
    except ProfileNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, error.message) from error
    return [
        UnresolvedSkillOut(
            unresolved_id=entry.unresolved_id,
            raw_text=entry.raw_text,
            suggestions=[SkillSuggestion(skill_id=i, skill_name=n) for i, n in suggestions],
        )
        for entry, suggestions in found
    ]


@router.post("/skills/unresolved/{unresolved_id}/map", response_model=SkillOut)
def map_unresolved_skill(
    unresolved_id: int,
    body: UnresolvedMap,
    user_id: Annotated[int, Depends(current_user_id)],
    service: Annotated[SkillService, Depends(skill_service)],
    session: SessionDep,
) -> SkillOut:
    """Map an unresolved string to a canonical skill at a level: the skill is
    declared and the string closed."""
    try:
        result = service.map_unresolved(user_id, unresolved_id, body.skill_id, body.level)
    except (ProfileNotFoundError, UnresolvedSkillNotFoundError) as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, error.message) from error
    except NotACanonicalSkillError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, error.message) from error
    session.commit()
    return SkillOut(
        skill_id=result.skill_id, skill_name=result.skill_name, level=result.level,
        source=result.source,
    )
