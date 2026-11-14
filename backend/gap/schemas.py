from pydantic import BaseModel

from backend.shared.skill_vector import Level


class GapItemOut(BaseModel):
    rank: int
    skill_id: int
    skill_name: str
    required_level: Level
    current_level: Level | None  # None: the student has no entry for this skill
    weight: int


class GapOut(BaseModel):
    role_id: int
    role_name: str
    items: list[GapItemOut]
