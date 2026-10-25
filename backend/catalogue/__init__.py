"""Resource catalogue module for UpSkill-AI (Module 4)."""

from backend.catalogue.models import LearningItem, LearningItemSkill, Skill, SkillAlias
from backend.catalogue.schemas import (
    LearningItemCreate,
    LearningItemModerate,
    LearningItemResponse,
    LearningItemType,
    ModerationState,
    SkillLevel,
    SkillTagInput,
)
from backend.catalogue.service import get_resources_for_skill
from backend.catalogue.views import catalogue_router

__all__ = [
    "LearningItem",
    "LearningItemSkill",
    "Skill",
    "SkillAlias",
    "LearningItemCreate",
    "LearningItemModerate",
    "LearningItemResponse",
    "LearningItemType",
    "ModerationState",
    "SkillLevel",
    "SkillTagInput",
    "catalogue_router",
    "get_resources_for_skill",
]
