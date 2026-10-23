"""
backend/gap/tests/test_compute_gap.py

Written before compute_gap() is implemented, per the Sprint 1 study
task: "write compute_gap() test fixtures before the implementation."

These fixtures model the Backend Developer sample role from
taxonomy_seed.sql, so once RM-1/RM-2 land in Sprint 2/3 this file
should need zero changes — only the xfail markers come off.

Expected to currently fail with NotImplementedError (the stub in
service.py) — that is the "right reason" called for in the kickoff
plan, not a bug in these fixtures.
"""

import pytest

from backend.gap.service import GapItem, RoleSkillRequirement, compute_gap
from backend.shared.skill_vector import Level, SkillVectorEntry

# ---------------------------------------------------------------------
# Skill ids below mirror taxonomy_seed.sql's Backend Developer role.
# Using small fixed ints here for fixture readability; the real ids
# come from the DB once seeded (skill_name is the stable join key).
# ---------------------------------------------------------------------
SKILL_PYTHON = 1
SKILL_REST_API = 2
SKILL_SQL_BASICS = 3
SKILL_DOCKER = 4
SKILL_UNIT_TESTING = 5

ROLE_BACKEND_DEVELOPER = 100


@pytest.fixture
def backend_developer_requirements() -> list[RoleSkillRequirement]:
    """Mirrors the role_skill_requirement rows seeded for 'Backend
    Developer' in taxonomy_seed.sql."""
    return [
        RoleSkillRequirement(
            ROLE_BACKEND_DEVELOPER, SKILL_PYTHON, "Python", Level.intermediate, weight=5
        ),
        RoleSkillRequirement(
            ROLE_BACKEND_DEVELOPER, SKILL_REST_API, "REST API Design", Level.intermediate, weight=4
        ),
        RoleSkillRequirement(
            ROLE_BACKEND_DEVELOPER, SKILL_SQL_BASICS, "SQL Basics", Level.beginner, weight=3
        ),
        RoleSkillRequirement(
            ROLE_BACKEND_DEVELOPER, SKILL_DOCKER, "Docker & Containerization",
            Level.beginner, weight=2
        ),
        RoleSkillRequirement(
            ROLE_BACKEND_DEVELOPER, SKILL_UNIT_TESTING, "Unit Testing", Level.beginner, weight=1
        ),
    ]


@pytest.fixture
def tied_weight_requirements() -> list[RoleSkillRequirement]:
    """Two requirements sharing the same weight, to pin down the
    documented tie-break rule: ties break by skill_id ascending."""
    return [
        RoleSkillRequirement(
            ROLE_BACKEND_DEVELOPER, SKILL_DOCKER, "Docker & Containerization",
            Level.beginner, weight=2
        ),
        RoleSkillRequirement(
            ROLE_BACKEND_DEVELOPER, SKILL_UNIT_TESTING, "Unit Testing", Level.beginner, weight=2
        ),
    ]


@pytest.fixture
def partial_student_vector() -> list[SkillVectorEntry]:
    """
    A student who:
      - has Python, but only at beginner (required: intermediate)  -> gap
      - has SQL Basics at intermediate (required: beginner)        -> already meets, excluded
      - has no entry at all for REST API Design                    -> gap
      - has no entry at all for Docker                             -> gap
      - has no entry at all for Unit Testing                       -> gap
    """
    return [
        SkillVectorEntry(SKILL_PYTHON, "Python", Level.beginner, confidence=0.80, source="resume"),
        SkillVectorEntry(
            SKILL_SQL_BASICS, "SQL Basics", Level.intermediate, confidence=0.90, source="course"
        ),
    ]


@pytest.fixture
def empty_student_vector_for_ties() -> list[SkillVectorEntry]:
    """No prior skills — used with tied_weight_requirements."""
    return []


@pytest.fixture
def fully_qualified_student_vector() -> list[SkillVectorEntry]:
    """A student who already meets or exceeds every requirement — gap should be empty."""
    return [
        SkillVectorEntry(
            SKILL_PYTHON, "Python", Level.advanced, confidence=1.0, source="completion"
        ),
        SkillVectorEntry(
            SKILL_REST_API, "REST API Design", Level.intermediate, confidence=0.85, source="course"
        ),
        SkillVectorEntry(
            SKILL_SQL_BASICS, "SQL Basics", Level.intermediate, confidence=0.90, source="course"
        ),
        SkillVectorEntry(
            SKILL_DOCKER, "Docker & Containerization", Level.beginner,
            confidence=0.70, source="manual"
        ),
        SkillVectorEntry(
            SKILL_UNIT_TESTING, "Unit Testing", Level.advanced, confidence=0.95, source="completion"
        ),
    ]


@pytest.fixture
def empty_student_vector() -> list[SkillVectorEntry]:
    """A brand-new student with no skills recorded yet — gap should equal every requirement."""
    return []


# ---------------------------------------------------------------------
# Expected results — these are what RM-1/RM-2 must produce once built.
# Ranked strictly by weight descending; SQL Basics is correctly absent
# because the student already meets it.
# ---------------------------------------------------------------------

EXPECTED_PARTIAL_GAP = [
    GapItem(
        SKILL_PYTHON, "Python", Level.intermediate,
        current_level=Level.beginner, weight=5, rank=1
    ),
    GapItem(
        SKILL_REST_API, "REST API Design", Level.intermediate,
        current_level=None, weight=4, rank=2
    ),
    GapItem(
        SKILL_DOCKER, "Docker & Containerization", Level.beginner,
        current_level=None, weight=2, rank=3
    ),
    GapItem(
        SKILL_UNIT_TESTING, "Unit Testing", Level.beginner,
        current_level=None, weight=1, rank=4
    ),
]


@pytest.mark.xfail(raises=NotImplementedError, reason="RM-1/RM-2 not implemented until Sprint 2/3")
def test_compute_gap_identifies_and_ranks_missing_and_below_level_skills(
    partial_student_vector, backend_developer_requirements
):
    result = compute_gap(partial_student_vector, backend_developer_requirements)
    assert result == EXPECTED_PARTIAL_GAP


@pytest.mark.xfail(raises=NotImplementedError, reason="RM-1/RM-2 not implemented until Sprint 2/3")
def test_compute_gap_excludes_skills_already_met(
    partial_student_vector, backend_developer_requirements
):
    result = compute_gap(partial_student_vector, backend_developer_requirements)
    gap_skill_ids = {item.skill_id for item in result}
    assert SKILL_SQL_BASICS not in gap_skill_ids  # met at intermediate, required beginner


@pytest.mark.xfail(raises=NotImplementedError, reason="RM-1/RM-2 not implemented until Sprint 2/3")
def test_compute_gap_is_empty_when_all_requirements_met(
    fully_qualified_student_vector, backend_developer_requirements
):
    result = compute_gap(fully_qualified_student_vector, backend_developer_requirements)
    assert result == []


@pytest.mark.xfail(raises=NotImplementedError, reason="RM-1/RM-2 not implemented until Sprint 2/3")
def test_compute_gap_for_new_student_equals_full_requirement_list(
    empty_student_vector, backend_developer_requirements
):
    result = compute_gap(empty_student_vector, backend_developer_requirements)
    assert len(result) == len(backend_developer_requirements)
    assert all(item.current_level is None for item in result)
    # still ranked by weight descending
    expected_order = [
        SKILL_PYTHON, SKILL_REST_API, SKILL_SQL_BASICS, SKILL_DOCKER, SKILL_UNIT_TESTING,
    ]
    assert [item.skill_id for item in result] == expected_order


@pytest.mark.xfail(raises=NotImplementedError, reason="RM-1/RM-2 not implemented until Sprint 2/3")
def test_compute_gap_ranking_is_strictly_descending_by_weight(
    empty_student_vector, backend_developer_requirements
):
    result = compute_gap(empty_student_vector, backend_developer_requirements)
    weights = [item.weight for item in result]
    assert weights == sorted(weights, reverse=True)


@pytest.mark.xfail(raises=NotImplementedError, reason="RM-1/RM-2 not implemented until Sprint 2/3")
def test_compute_gap_breaks_weight_ties_by_skill_id_ascending(
    empty_student_vector_for_ties, tied_weight_requirements
):
    """Docker (id 4) and Unit Testing (id 5) share weight=2 — the lower
    skill_id must sort first, per the tie-break rule in the docstring."""
    result = compute_gap(empty_student_vector_for_ties, tied_weight_requirements)
    assert [item.skill_id for item in result] == [SKILL_DOCKER, SKILL_UNIT_TESTING]