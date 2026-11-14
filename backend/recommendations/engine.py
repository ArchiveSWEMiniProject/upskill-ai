"""Recommend catalogue resources for a skill gap (RM-4, REQ-F2-05).

Pure functions: no I/O, and the arguments are not modified. Catalogue rows come in
as Resource values, so the ranking is tested with plain fixtures.

A resource is appropriate for a gap item when it brings the skill to a level above
the student's current one (any level if they hold nothing) and no higher than the
level the role requires. Appropriate resources are ranked lowest level first, so the
student meets the next step before the later ones. Ties break by item id, so the
order is the same on every call.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from backend.gap.service import GapItem
from backend.shared.skill_vector import Level


@dataclass(frozen=True)
class Resource:
    """One approved catalogue resource covering one skill (docs/CONTRACTS.md, section 3).

    A resource may cover several skills, each at its own level, so there is one
    Resource per (resource, skill) pair and coverage_level is the level it brings
    that skill to.
    """

    item_id: int
    skill_id: int
    title: str
    item_type: str
    coverage_level: Level
    source_url: str
    duration: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "coverage_level", Level(self.coverage_level))


def recommend_for_gap_item(item: GapItem, candidates: Iterable[Resource]) -> list[Resource]:
    """The ranked resources that help the student close this gap item."""
    floor = -1 if item.current_level is None else item.current_level.rank
    ceiling = item.required_level.rank
    chosen = [
        resource
        for resource in candidates
        if resource.skill_id == item.skill_id and floor < resource.coverage_level.rank <= ceiling
    ]
    return sorted(chosen, key=lambda resource: (resource.coverage_level.rank, resource.item_id))
