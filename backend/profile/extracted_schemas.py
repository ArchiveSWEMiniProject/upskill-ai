"""Request and response shapes for extracted resume skills (UP-7, UP-8)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SkillLevel = Literal["beginner", "intermediate", "advanced"]


class ExtractedSkillOut(BaseModel):
    candidate_id: int
    upload_id: int
    skill_id: int
    skill_name: str
    suggested_level: SkillLevel
    confidence: float
    source_sentence: str
    status: Literal["pending", "confirmed", "rejected"]


class ExtractedSkillsOut(BaseModel):
    threshold: float  # REQ-F1-17: bulk confirm covers confidence at or above this
    candidates: list[ExtractedSkillOut]


class SkillDecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: int
    action: Literal["confirm", "reject"]
    level: SkillLevel | None = None  # confirm only: an edited level

    @model_validator(mode="after")
    def _level_only_when_confirming(self):
        if self.action == "reject" and self.level is not None:
            raise ValueError("A level can only be given when confirming")
        return self


class SkillDecisionsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decisions: list[SkillDecisionIn] = Field(min_length=1, max_length=200)

    @field_validator("decisions")
    @classmethod
    def _each_once(cls, decisions):
        ids = [d.candidate_id for d in decisions]
        if len(ids) != len(set(ids)):
            raise ValueError("Each extracted skill can be decided only once per request")
        return decisions


class SkillDecisionOut(BaseModel):
    candidate_id: int
    skill_id: int
    skill_name: str
    status: Literal["confirmed", "rejected"]
    level: SkillLevel | None


class BulkConfirmOut(BaseModel):
    threshold: float
    confirmed: list[SkillDecisionOut]
