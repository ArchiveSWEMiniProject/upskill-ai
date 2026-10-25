"""Catalogue service implementing internal module interfaces (Module 4).

Complies with:
- CONTRACTS.md §5.2: get_resources_for_skill(skill_ids, level) -> list[Resource]
- SW Architecture §5.2, §6.3: Returns approved catalogue resources only.
"""

from typing import Optional, Union

from sqlalchemy.orm import Session, joinedload

from backend.catalogue.models import (
    LearningItem,
    LearningItemSkill,
    ModerationState,
    SkillLevel,
)
from backend.database import get_session


def get_resources_for_skill(
    skill_ids: list[int],
    level: Optional[Union[SkillLevel, str]] = None,
    db: Optional[Session] = None,
) -> list[dict]:
    """Retrieve approved catalogue resources for given canonical skill IDs.

    Contract: get_resources_for_skill(skill_ids, level) -> list[Resource]
    Provider: M4
    Consumers: M2 (Roadmap & Recommender)
    Rules: Returns approved catalogue resources only.
    """
    if not skill_ids:
        return []

    owns_session = False
    if db is None:
        db = next(get_session())
        owns_session = True

    try:
        query = (
            db.query(LearningItem)
            .join(LearningItem.skills)
            .filter(
                LearningItem.moderation_state == ModerationState.APPROVED,
                LearningItemSkill.skill_id.in_(skill_ids),
            )
            .options(
                joinedload(LearningItem.skills).joinedload(LearningItemSkill.skill)
            )
            .distinct()
        )

        if level is not None:
            level_str = level.value if hasattr(level, "value") else str(level).lower()
            query = query.filter(LearningItem.level == level_str)

        items = query.all()

        results = []
        for item in items:
            skill_tags = [
                {
                    "skill_id": s.skill_id,
                    "skill_name": (
                        s.skill.skill_name if s.skill else f"Skill {s.skill_id}"
                    ),
                    "coverage_level": (
                        s.coverage_level.value
                        if hasattr(s.coverage_level, "value")
                        else str(s.coverage_level)
                    ),
                }
                for s in item.skills
            ]
            results.append(
                {
                    "item_id": item.item_id,
                    "title": item.title,
                    "description": item.description,
                    "item_type": (
                        item.item_type.value
                        if hasattr(item.item_type, "value")
                        else str(item.item_type)
                    ),
                    "level": (
                        item.level.value
                        if hasattr(item.level, "value")
                        else str(item.level)
                    ),
                    "duration": item.duration,
                    "source_url": item.source_url,
                    "source": item.source,
                    "moderation_state": (
                        item.moderation_state.value
                        if hasattr(item.moderation_state, "value")
                        else str(item.moderation_state)
                    ),
                    "skill_tags": skill_tags,
                }
            )
        return results
    finally:
        if owns_session:
            db.close()
