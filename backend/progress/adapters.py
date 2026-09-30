from backend.progress.exceptions import DependencyUnavailableError
from backend.progress.ports import (
    LearningCataloguePort,
    LearningItem,
    RecommendationPort,
    RecommendationUpdateResult,
    SkillVectorPort,
    VectorUpdateResult,
)


class UnavailableLearningCatalogue(LearningCataloguePort):
    """M4 integration placeholder; tests inject a fake catalogue."""

    def get_learning_item(self, resource_id: str) -> LearningItem | None:
        raise DependencyUnavailableError("M4 learning catalogue adapter is not connected")


class UnavailableSkillVector(SkillVectorPort):
    """M1 integration placeholder; tests inject a fake skill-vector adapter."""

    def apply_vector_update(
        self, student_id: str, skill_id: int, level: str, source: str = "completion"
    ) -> VectorUpdateResult:
        raise DependencyUnavailableError("M1 skill-vector adapter is not connected")


class UnavailableRecommendations(RecommendationPort):
    """M2 integration placeholder; tests inject a fake recommendation adapter."""

    def recompute(self, student_id: str) -> RecommendationUpdateResult:
        raise DependencyUnavailableError("M2 recommendation adapter is not connected")
