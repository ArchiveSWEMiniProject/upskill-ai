"""Pydantic schemas and input validators for the resource catalogue (Module 4).

Complies with:
- REQ-F4-06: Resource types (course, certification, project_idea)
- REQ-F4-07: Required resource fields
- REQ-F4-08: Validation of required catalogue fields (TC-F4-07)
- BR-01: At least one canonical skill tag required
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from backend.catalogue.models import LearningItemType, ModerationState, SkillLevel


class SkillTagInput(BaseModel):
    """Input representation of a skill tag attached to a resource."""

    skill_id: Optional[int] = None
    skill_name: Optional[str] = None
    coverage_level: SkillLevel = SkillLevel.BEGINNER

    @field_validator("skill_name")
    @classmethod
    def clean_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class LearningItemCreate(BaseModel):
    """Payload to create a new catalogue learning resource."""

    title: str = Field(..., min_length=3, max_length=150, description="Title of the resource")
    description: str = Field(
        ..., min_length=10, max_length=1000, description="Description of the resource"
    )
    item_type: LearningItemType = Field(..., description="course, certification, or project_idea")
    level: SkillLevel = Field(..., description="beginner, intermediate, or advanced")
    duration: Optional[str] = Field(None, max_length=30, description="e.g. 10 hours, 4 weeks")
    source_url: str = Field(..., max_length=255, description="URL to the resource")
    source: Optional[str] = Field(
        None, max_length=60, description="Publisher / provider (e.g. Coursera)"
    )
    moderation_state: ModerationState = ModerationState.PENDING
    skill_tags: list[SkillTagInput] = Field(
        ...,
        min_length=1,
        description="At least one canonical skill tag is required (BR-01, TC-F4-07)",
    )

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("source_url must be a valid HTTP or HTTPS URL")
        return v


class LearningItemModerate(BaseModel):
    """Payload to update the moderation state of a catalogue resource."""

    moderation_state: ModerationState


class SkillTagResponse(BaseModel):
    """Skill tag representation in response."""

    skill_id: int
    skill_name: str
    coverage_level: SkillLevel


class LearningItemResponse(BaseModel):
    """Catalogue resource response."""

    item_id: int
    title: str
    description: str
    item_type: LearningItemType
    level: SkillLevel
    duration: Optional[str] = None
    source_url: str
    source: Optional[str] = None
    moderation_state: ModerationState
    skill_tags: list[SkillTagResponse] = []

    model_config = {"from_attributes": True}


class PaginatedLearningItemResponse(BaseModel):
    """Paginated list of catalogue learning resources (NFR-PERF-04)."""

    total: int
    limit: int
    offset: int
    items: list[LearningItemResponse]
