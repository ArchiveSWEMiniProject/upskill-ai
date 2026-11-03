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


class SkillVectorEntryOut(BaseModel):
    """One entry in the frozen skill vector format (docs/CONTRACTS.md, section 1)."""

    canonical_skill_id: int
    canonical_skill_name: str
    level: Level
    confidence: float | None  # 0.00 to 1.00; null for manually declared skills
    source: Literal["manual", "course", "resume", "completion"]


class SkillVectorOut(BaseModel):
    entries: list[SkillVectorEntryOut]
