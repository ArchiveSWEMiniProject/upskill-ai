"""
backend/gap/service.py

RM-1 / RM-2: compute the level-aware skill gap between a student's skill
vector and a target role's requirements, ranked by requirement weight.

compute_gap() is a pure function. It does no I/O, reads no database and
changes none of its arguments, so M2 can call it with whatever the skill
vector and role requirement loaders return.

Level and SkillVectorEntry live in backend/shared/skill_vector.py (frozen
contract, owned by M1). They are imported here, not redefined, per review
feedback on PR #6.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from backend.shared.skill_vector import Level, SkillVectorEntry


@dataclass(frozen=True)
class RoleSkillRequirement:
    """One row of role_skill_requirement (docs/CONTRACTS.md, section 2)."""
    role_id: int
    skill_id: int
    skill_name: str
    required_level: Level
    weight: int


@dataclass(frozen=True)
class GapItem:
    """One entry in the output of compute_gap()."""
    skill_id: int
    skill_name: str
    required_level: Level
    current_level: Level | None  # None if the student has no entry at all
    weight: int
    rank: int  # 1 = highest priority, assigned after sorting by weight desc


def _current_levels(student_vector: Iterable[SkillVectorEntry]) -> dict[int, Level]:
    """Map skill id to the student's level, keeping the highest if a skill repeats."""
    levels: dict[int, Level] = {}
    for entry in student_vector:
        known = levels.get(entry.canonical_skill_id)
        if known is None or entry.level > known:
            levels[entry.canonical_skill_id] = entry.level
    return levels


def compute_gap(
    student_vector: Iterable[SkillVectorEntry],
    role_requirements: Iterable[RoleSkillRequirement],
) -> list[GapItem]:
    """
    RM-1 / RM-2: compute the level-aware skill gap between a student's
    current skill vector and a target role's requirements, then rank the
    gap items by role_skill_requirement.weight (descending).

    A skill is a "gap" when the student has no entry for it, OR their
    current level is strictly below the required level. A skill the
    student already meets or exceeds is NOT included in the result.

    Ties in weight break by skill_id ascending (stable, deterministic
    ordering, so tests and the UI render the same order). Ranks are
    assigned 1, 2, 3, ... after sorting.

    Pure function: no I/O, and the arguments are not modified. If a skill
    appears more than once in the student's vector, the highest level wins.
    """
    current = _current_levels(student_vector)

    gaps: list[tuple[RoleSkillRequirement, Level | None]] = []
    for requirement in role_requirements:
        level = current.get(requirement.skill_id)
        if level is None or level < requirement.required_level:
            gaps.append((requirement, level))

    gaps.sort(key=lambda gap: (-gap[0].weight, gap[0].skill_id))

    return [
        GapItem(
            skill_id=requirement.skill_id,
            skill_name=requirement.skill_name,
            required_level=requirement.required_level,
            current_level=level,
            weight=requirement.weight,
            rank=rank,
        )
        for rank, (requirement, level) in enumerate(gaps, start=1)
    ]