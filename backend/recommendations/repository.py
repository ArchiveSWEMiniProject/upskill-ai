"""Read-only catalogue query behind the recommendations (RM-4).

M4 owns the catalogue and has not published get_resources_for_skill() yet, so M2
reads the two catalogue tables through lightweight table constructs, never by
importing M4's models (rule R2), as backend/skills/vector.py does for `skill`.
Only approved resources are returned (REQ-F4-12, TC-F2-10). When M4 publishes its
interface, replace this class and leave RoadmapService unchanged.
"""

from collections.abc import Iterable

from sqlalchemy import column, literal_column, select, table
from sqlalchemy.orm import Session

from backend.recommendations.engine import Resource

_item = table(
    "learning_item",
    column("item_id"),
    column("title"),
    column("item_type"),
    column("duration"),
    column("source_url"),
    column("source"),
    column("moderation_state"),
)
_tag = table(
    "learning_item_skill",
    column("item_id"),
    column("skill_id"),
    column("coverage_level"),
)


class ResourceRepository:
    def __init__(self, session: Session):
        self._session = session

    def approved_for_skills(self, skill_ids: Iterable[int]) -> list[Resource]:
        ids = sorted(set(skill_ids))
        if not ids:
            return []
        query = (
            select(
                _item.c.item_id,
                _tag.c.skill_id,
                _item.c.title,
                _item.c.item_type,
                _tag.c.coverage_level,
                _item.c.source_url,
                _item.c.duration,
                _item.c.source,
            )
            .select_from(_tag)
            .join(_item, _item.c.item_id == _tag.c.item_id)
            .where(
                _tag.c.skill_id.in_(ids),
                _item.c.moderation_state == literal_column("'approved'"),
            )
            .order_by(_item.c.item_id, _tag.c.skill_id)
        )
        return [Resource(*row) for row in self._session.execute(query)]
