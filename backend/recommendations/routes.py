from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.gap.exceptions import NoProfileError, NoTargetRoleError
from backend.gap.routes import SessionDep, gap_service, student_user_id
from backend.gap.student_gap import StudentGapService
from backend.recommendations.repository import ResourceRepository
from backend.recommendations.schemas import ResourceOut, RoadmapItemOut, RoadmapOut
from backend.recommendations.service import RoadmapService

router = APIRouter(prefix="/api/v1/roadmap", tags=["roadmap"])


def resource_repository(session: SessionDep) -> ResourceRepository:
    return ResourceRepository(session)


def roadmap_service(
    gaps: Annotated[StudentGapService, Depends(gap_service)],
    resources: Annotated[ResourceRepository, Depends(resource_repository)],
) -> RoadmapService:
    return RoadmapService(gaps, resources)


@router.get(
    "",
    response_model=RoadmapOut,
    responses={
        404: {"description": "The caller has no profile yet"},
        409: {"description": "The caller has not chosen a target role"},
    },
)
def read_roadmap(
    user_id: Annotated[int, Depends(student_user_id)],
    service: Annotated[RoadmapService, Depends(roadmap_service)],
) -> RoadmapOut:
    """The caller's skill gap, most important first, with ranked approved catalogue
    resources for each gap skill (REQ-F2-05). Computed on every request."""
    try:
        roadmap = service.roadmap_for_user(user_id)
    except NoProfileError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, error.message) from error
    except NoTargetRoleError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, error.message) from error
    return RoadmapOut(
        role_id=roadmap.role_id,
        role_name=roadmap.role_name,
        items=[
            RoadmapItemOut(
                rank=entry.gap.rank,
                skill_id=entry.gap.skill_id,
                skill_name=entry.gap.skill_name,
                required_level=entry.gap.required_level,
                current_level=entry.gap.current_level,
                weight=entry.gap.weight,
                resources=[ResourceOut.model_validate(r) for r in entry.resources],
            )
            for entry in roadmap.entries
        ],
    )
