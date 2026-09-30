from dataclasses import dataclass
from typing import Literal, Protocol

from backend.progress.enums import EvidenceType

SkillLevel = Literal["beginner", "intermediate", "advanced"]


@dataclass(frozen=True)
class SkillOutcome:
    skill_id: int
    level: SkillLevel


@dataclass(frozen=True)
class LearningItem:
    resource_id: str
    title: str
    evidence_required: bool
    evidence_types: tuple[EvidenceType, ...]
    skill_outcomes: tuple[SkillOutcome, ...]


@dataclass(frozen=True)
class VectorUpdateResult:
    changed: bool


@dataclass(frozen=True)
class RecommendationUpdateResult:
    status: str
    roadmap_version: str | None = None


class LearningCataloguePort(Protocol):
    def get_learning_item(self, resource_id: str) -> LearningItem | None: ...


class SkillVectorPort(Protocol):
    def apply_vector_update(
        self, student_id: str, skill_id: int, level: str, source: str = "completion"
    ) -> VectorUpdateResult: ...


class RecommendationPort(Protocol):
    def recompute(self, student_id: str) -> RecommendationUpdateResult: ...
