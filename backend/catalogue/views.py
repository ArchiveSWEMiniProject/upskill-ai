"""Catalogue API endpoints for UpSkill-AI (Module 4).

Implements:
- REQ-F4-05: Administrator catalogue CRUD (TC-F4-04, TC-F4-05)
- REQ-F4-07 & REQ-F4-08: Field validation and canonical skill enforcement (TC-F4-07, TC-F4-08)
- REQ-F4-09 & REQ-F4-10: Search across title, description, skill tags and filters (TC-F4-09)
- REQ-F4-11 & REQ-F4-12: Moderation state and student visibility filtering (TC-F4-10)
- NFR-PERF-04: Paginated catalogue result sets
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, joinedload

from backend.auth.dependencies import get_current_user
from backend.auth.models import UserContext, UserRole
from backend.auth.permissions import authorize
from backend.catalogue.models import (
    LearningItem,
    LearningItemSkill,
    LearningItemType,
    ModerationState,
    Skill,
    SkillLevel,
)
from backend.catalogue.schemas import (
    LearningItemCreate,
    LearningItemModerate,
    LearningItemResponse,
    SkillTagResponse,
)
from backend.catalogue.validators import resolve_canonical_skill
from backend.database import get_db

catalogue_router = APIRouter(prefix="/api/v1/catalogue", tags=["catalogue"])


def _format_item_response(item: LearningItem) -> LearningItemResponse:
    """Format SQLAlchemy LearningItem into LearningItemResponse."""
    skill_tags = []
    if item.skills:
        for s in item.skills:
            skill_name = s.skill.skill_name if s.skill else f"Skill {s.skill_id}"
            skill_tags.append(
                SkillTagResponse(
                    skill_id=s.skill_id,
                    skill_name=skill_name,
                    coverage_level=s.coverage_level,
                )
            )
    return LearningItemResponse(
        item_id=item.item_id,
        title=item.title,
        description=item.description,
        item_type=item.item_type,
        level=item.level,
        duration=item.duration,
        source_url=item.source_url,
        source=item.source,
        moderation_state=item.moderation_state,
        skill_tags=skill_tags,
    )


@catalogue_router.post(
    "",
    response_model=LearningItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new catalogue learning resource (Administrator only)",
)
def create_catalogue_item(
    item_in: LearningItemCreate,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LearningItemResponse:
    """Create a new catalogue resource.

    Complies with:
    - TC-F4-04: Student calling this endpoint is rejected with 403 Forbidden.
    - TC-F4-07: Required fields validated.
    - TC-F4-08: Skill tags must correspond to canonical skills in taxonomy.
    """
    if not authorize(current_user, "catalogue:create", db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: only administrators can create catalogue resources",
        )

    # Validate each skill tag against canonical taxonomy (TC-F4-08)
    resolved_skills = []
    for tag in item_in.skill_tags:
        skill_id, _ = resolve_canonical_skill(tag, db)
        resolved_skills.append((skill_id, tag.coverage_level))

    new_item = LearningItem(
        title=item_in.title.strip(),
        description=item_in.description.strip(),
        item_type=item_in.item_type,
        level=item_in.level,
        duration=item_in.duration.strip() if item_in.duration else None,
        source_url=str(item_in.source_url).strip(),
        source=item_in.source.strip() if item_in.source else None,
        moderation_state=item_in.moderation_state,
    )
    db.add(new_item)
    db.flush()

    for skill_id, coverage_level in resolved_skills:
        item_skill = LearningItemSkill(
            item_id=new_item.item_id,
            skill_id=skill_id,
            coverage_level=coverage_level,
        )
        db.add(item_skill)

    db.commit()
    db.refresh(new_item)

    loaded_item = (
        db.query(LearningItem)
        .options(joinedload(LearningItem.skills).joinedload(LearningItemSkill.skill))
        .filter(LearningItem.item_id == new_item.item_id)
        .first()
    )
    return _format_item_response(loaded_item)


@catalogue_router.patch(
    "/{item_id}/moderate",
    response_model=LearningItemResponse,
    summary="Moderate a catalogue resource (Administrator only)",
)
def moderate_catalogue_item(
    item_id: int,
    mod_in: LearningItemModerate,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LearningItemResponse:
    """Update moderation state of a catalogue resource.

    Complies with:
    - TC-F4-05: Faculty mentor calling this endpoint is rejected with 403 Forbidden.
    """
    if not authorize(current_user, "catalogue:moderate", db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: only administrators can moderate catalogue resources",
        )

    item = (
        db.query(LearningItem)
        .options(joinedload(LearningItem.skills).joinedload(LearningItemSkill.skill))
        .filter(LearningItem.item_id == item_id)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with ID {item_id} not found",
        )

    item.moderation_state = mod_in.moderation_state
    db.commit()
    db.refresh(item)
    return _format_item_response(item)


@catalogue_router.get(
    "/{item_id}",
    response_model=LearningItemResponse,
    summary="Get a single catalogue resource by ID",
)
def get_catalogue_item(
    item_id: int,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LearningItemResponse:
    """Fetch a single catalogue item by ID.
    Non-administrators can only view approved items (REQ-F4-12, TC-F4-10).
    """
    item = (
        db.query(LearningItem)
        .options(joinedload(LearningItem.skills).joinedload(LearningItemSkill.skill))
        .filter(LearningItem.item_id == item_id)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with ID {item_id} not found",
        )

    if (
        current_user.role != UserRole.ADMINISTRATOR
        and item.moderation_state != ModerationState.APPROVED
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with ID {item_id} not found",
        )

    return _format_item_response(item)


@catalogue_router.get(
    "",
    response_model=list[LearningItemResponse],
    summary="Search, filter, and paginate catalogue resources",
)
def list_catalogue_items(
    response: Response,
    q: Optional[str] = Query(
        None,
        description="Search term matching title, description, or tagged skill names (TC-F4-09)",
    ),
    skill_id: Optional[int] = Query(None, description="Filter by canonical skill ID"),
    skill: Optional[str] = Query(None, description="Filter by canonical skill name"),
    level: Optional[SkillLevel] = Query(None, description="Filter by difficulty level"),
    item_type: Optional[LearningItemType] = Query(None, description="Filter by resource type"),
    duration: Optional[str] = Query(None, description="Filter by duration string"),
    limit: int = Query(50, ge=1, le=100, description="Page limit (NFR-PERF-04)"),
    offset: int = Query(0, ge=0, description="Page offset (NFR-PERF-04)"),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LearningItemResponse]:
    """List catalogue resources with search and attribute filters.

    Complies with:
    - TC-F4-09: Search matches title, description, and skill tags.
    - TC-F4-10: Inactive resources do not appear in normal student search results (REQ-F4-12).
    - NFR-PERF-04: Bounded paginated queries with limit and offset.
    """
    query = db.query(LearningItem).options(
        joinedload(LearningItem.skills).joinedload(LearningItemSkill.skill)
    )

    # Students and faculty see only approved resources (REQ-F4-12, TC-F4-10)
    if current_user.role != UserRole.ADMINISTRATOR:
        query = query.filter(LearningItem.moderation_state == ModerationState.APPROVED)

    # Search across title, description, and tagged skill names (TC-F4-09)
    if q:
        search_term = f"%{q.strip()}%"
        skill_item_ids = (
            db.query(LearningItemSkill.item_id)
            .join(Skill, Skill.skill_id == LearningItemSkill.skill_id)
            .filter(Skill.skill_name.ilike(search_term))
        )
        query = query.filter(
            (LearningItem.title.ilike(search_term))
            | (LearningItem.description.ilike(search_term))
            | (LearningItem.item_id.in_(skill_item_ids))
        )

    # Attribute filters
    if level:
        query = query.filter(LearningItem.level == level)

    if item_type:
        query = query.filter(LearningItem.item_type == item_type)

    if duration:
        query = query.filter(LearningItem.duration.ilike(f"%{duration.strip()}%"))

    if skill_id is not None:
        query = query.join(LearningItem.skills).filter(LearningItemSkill.skill_id == skill_id)

    if skill:
        skill_name_term = f"%{skill.strip()}%"
        skill_match = (
            db.query(LearningItemSkill.item_id)
            .join(Skill, Skill.skill_id == LearningItemSkill.skill_id)
            .filter(Skill.skill_name.ilike(skill_name_term))
            .subquery()
        )
        query = query.filter(LearningItem.item_id.in_(skill_match))

    total = query.distinct().count()

    # Bounded pagination (NFR-PERF-04)
    items = query.distinct().order_by(LearningItem.item_id).offset(offset).limit(limit).all()

    # Attach pagination headers
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)

    return [_format_item_response(item) for item in items]
