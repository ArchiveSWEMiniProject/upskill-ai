from backend.progress.enums import EvidenceType
from backend.progress.ports import (
    LearningItem,
    RecommendationUpdateResult,
    SkillOutcome,
    VectorUpdateResult,
)


class FakeCatalogue:
    def __init__(self, items=None):
        self.items = items or {
            "LI-1001": LearningItem(
                resource_id="LI-1001",
                title="Git fundamentals",
                evidence_required=True,
                evidence_types=(EvidenceType.CERTIFICATE, EvidenceType.QUIZ),
                skill_outcomes=(SkillOutcome(7, "beginner"),),
            )
        }

    def get_learning_item(self, resource_id):
        return self.items.get(resource_id)


class FakeSkillVector:
    def __init__(self, changed=True, error=None):
        self.changed = changed
        self.error = error
        self.calls = []

    def apply_vector_update(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return VectorUpdateResult(changed=self.changed)


class FakeRecommendations:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def recompute(self, student_id):
        self.calls.append(student_id)
        if self.error:
            raise self.error
        return RecommendationUpdateResult(status="recomputed", roadmap_version="v2")
