"""The student's roadmap: their gap, with ranked catalogue resources for each skill (RM-4).

Prerequisite ordering (RM-5) and the explanation of each recommendation (RM-6) are
added later; for now the entries keep the gap's own order, most important first.
"""

from dataclasses import dataclass

from backend.gap.service import GapItem
from backend.gap.student_gap import StudentGapService
from backend.recommendations.engine import Resource, recommend_for_gap_item
from backend.recommendations.repository import ResourceRepository


@dataclass(frozen=True)
class RoadmapEntry:
    gap: GapItem
    resources: list[Resource]  # empty when the catalogue has nothing suitable


@dataclass(frozen=True)
class Roadmap:
    role_id: int
    role_name: str
    entries: list[RoadmapEntry]


class RoadmapService:
    def __init__(self, gaps: StudentGapService, resources: ResourceRepository):
        self._gaps = gaps
        self._resources = resources

    def roadmap_for_user(self, user_id: int) -> Roadmap:
        gap = self._gaps.gap_for_user(user_id)
        candidates: list[Resource] = []
        if gap.items:
            candidates = self._resources.approved_for_skills(
                [item.skill_id for item in gap.items]
            )
        return Roadmap(
            role_id=gap.role_id,
            role_name=gap.role_name,
            entries=[
                RoadmapEntry(item, recommend_for_gap_item(item, candidates))
                for item in gap.items
            ],
        )
