from pydantic import BaseModel

from backend.gap.schemas import GapItemOut
from backend.shared.skill_vector import Level


class ResourceOut(BaseModel):
    item_id: int
    title: str
    item_type: str
    coverage_level: Level  # the level this resource brings the skill to
    duration: str | None
    source: str | None
    source_url: str

    model_config = {"from_attributes": True}


class RoadmapItemOut(GapItemOut):
    resources: list[ResourceOut]


class RoadmapOut(BaseModel):
    role_id: int
    role_name: str
    items: list[RoadmapItemOut]
