"""
backend/gap/service.py

Stub only. Implements nothing yet — exists so that
backend/gap/tests/test_compute_gap.py can import compute_gap() and fail
for the right reason (NotImplementedError) rather than an ImportError,
per the Sprint 1 "done when" criterion.

Fill this in against RM-1 (gap computation) and RM-2 (ranking) once the
skill vector (contract 7.1) is actually being produced by M1.

Level and SkillVectorEntry live in backend/shared/types.py (frozen
contract, owned by M1) — imported here, not redefined, per review
feedback on PR #6.
"""

from dataclasses import dataclass

from backend.shared.shared_types_proposed import Level, SkillVectorEntry


@dataclass(frozen=True)
class RoleSkillRequirement:
    """One row of role_skill_requirement — contract 7.2."""
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


def compute_gap(
    student_vector: list[SkillVectorEntry],
    role_requirements: list[RoleSkillRequirement],
) -> list[GapItem]:
    """
    RM-1 / RM-2: Compute the level-aware skill gap between a student's
    current skill vector and a target role's requirements, then rank
    the gap items by role_skill_requirement.weight (descending).

    A skill is a "gap" when the student has no entry for it, OR their
    current level is strictly below the required level. A skill the
    student already meets or exceeds is NOT included in the result.

    Ties in weight break by skill_id ascending (stable, deterministic
    ordering — needed so tests and the UI render the same order).

    NOT YET IMPLEMENTED. Raises so Sprint 1 CI shows a clear, honest
    failure instead of a false green or an import error.
    """
    raise NotImplementedError(
        "compute_gap() — implementation lands in Sprint 2/3 (RM-1, RM-2)"
    )