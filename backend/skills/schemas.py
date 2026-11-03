from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

# The level enum from the frozen skill vector contract (docs/CONTRACTS.md, section 1).
Level = Literal["beginner", "intermediate", "advanced"]
SkillText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class SkillDeclare(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: SkillText
    level: Level


class SkillOut(BaseModel):
    skill_id: int
    skill_name: str
    level: Level
    source: Literal["manual", "course", "resume", "completion"]


class SkillSuggestion(BaseModel):
    skill_id: int
    skill_name: str


class UnknownSkillDetail(BaseModel):
    message: str
    suggestions: list[SkillSuggestion]
