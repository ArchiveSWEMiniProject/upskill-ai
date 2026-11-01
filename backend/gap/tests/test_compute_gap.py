"""
backend/gap/tests/test_compute_gap.py

Tests for compute_gap() (RM-1 / RM-2). The fixtures model the Backend
Developer sample role from taxonomy_seed.sql. They were written before the
implementation, per the Sprint 1 study task, and now run against it.
"""

import pytest

from backend.gap.service import GapItem, RoleSkillRequirement, compute_gap
from backend.shared.skill_vector import Level, SkillVector, SkillVectorEntry

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


def test_compute_gap_identifies_and_ranks_missing_and_below_level_skills(
    partial_student_vector, backend_developer_requirements
):
    result = compute_gap(partial_student_vector, backend_developer_requirements)
    assert result == EXPECTED_PARTIAL_GAP


def test_compute_gap_excludes_skills_already_met(
    partial_student_vector, backend_developer_requirements
):
    result = compute_gap(partial_student_vector, backend_developer_requirements)
    gap_skill_ids = {item.skill_id for item in result}
    assert SKILL_SQL_BASICS not in gap_skill_ids  # met at intermediate, required beginner


def test_compute_gap_is_empty_when_all_requirements_met(
    fully_qualified_student_vector, backend_developer_requirements
):
    result = compute_gap(fully_qualified_student_vector, backend_developer_requirements)
    assert result == []


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


def test_compute_gap_ranking_is_strictly_descending_by_weight(
    empty_student_vector, backend_developer_requirements
):
    result = compute_gap(empty_student_vector, backend_developer_requirements)
    weights = [item.weight for item in result]
    assert weights == sorted(weights, reverse=True)


def test_compute_gap_breaks_weight_ties_by_skill_id_ascending(
    empty_student_vector_for_ties, tied_weight_requirements
):
    """Docker (id 4) and Unit Testing (id 5) share weight=2 — the lower
    skill_id must sort first, per the tie-break rule in the docstring."""
    result = compute_gap(empty_student_vector_for_ties, tied_weight_requirements)
    assert [item.skill_id for item in result] == [SKILL_DOCKER, SKILL_UNIT_TESTING]


def test_compute_gap_ranking_does_not_depend_on_input_order(
    partial_student_vector, backend_developer_requirements
):
    shuffled = list(reversed(backend_developer_requirements))
    assert compute_gap(partial_student_vector, shuffled) == EXPECTED_PARTIAL_GAP


def test_compute_gap_is_empty_when_the_role_has_no_requirements(partial_student_vector):
    assert compute_gap(partial_student_vector, []) == []


def test_compute_gap_uses_the_highest_level_when_a_skill_appears_twice():
    student = [
        SkillVectorEntry(
            SKILL_PYTHON, "Python", Level.beginner, confidence=0.50, source="manual"
        ),
        SkillVectorEntry(
            SKILL_PYTHON, "Python", Level.advanced, confidence=0.90, source="course"
        ),
    ]
    requirements = [
        RoleSkillRequirement(
            ROLE_BACKEND_DEVELOPER, SKILL_PYTHON, "Python", Level.intermediate, weight=5
        ),
    ]
    assert compute_gap(student, requirements) == []


def test_compute_gap_does_not_modify_its_inputs(
    partial_student_vector, backend_developer_requirements
):
    vector_before = list(partial_student_vector)
    requirements_before = list(backend_developer_requirements)
    compute_gap(partial_student_vector, backend_developer_requirements)
    assert partial_student_vector == vector_before
    assert backend_developer_requirements == requirements_before


def test_compute_gap_accepts_a_skill_vector_object(
    partial_student_vector, backend_developer_requirements
):
    vector = SkillVector(tuple(partial_student_vector))
    assert compute_gap(vector, backend_developer_requirements) == EXPECTED_PARTIAL_GAP


def test_requirement_converts_a_string_level_to_level():
    requirement = RoleSkillRequirement(
        ROLE_BACKEND_DEVELOPER, SKILL_PYTHON, "Python", "advanced", weight=5
    )
    assert requirement.required_level is Level.advanced


def test_requirement_rejects_an_unknown_level():
    with pytest.raises(ValueError, match="required_level"):
        RoleSkillRequirement(
            ROLE_BACKEND_DEVELOPER, SKILL_PYTHON, "Python", "expert", weight=5
        )


def test_compute_gap_string_level_is_compared_by_rank_not_alphabetically_beginner():
    """A beginner must not count as meeting an advanced requirement."""
    student = [
        SkillVectorEntry(
            SKILL_PYTHON, "Python", Level.beginner, confidence=0.80, source="resume"
        ),
    ]
    requirements = [
        RoleSkillRequirement(
            ROLE_BACKEND_DEVELOPER, SKILL_PYTHON, "Python", "advanced", weight=5
        ),
    ]
    assert compute_gap(student, requirements) == [
        GapItem(
            SKILL_PYTHON, "Python", Level.advanced,
            current_level=Level.beginner, weight=5, rank=1
        )
    ]


def test_compute_gap_string_level_is_compared_by_rank_not_alphabetically_advanced():
    """An advanced student must not show a gap against an intermediate requirement."""
    student = [
        SkillVectorEntry(
            SKILL_PYTHON, "Python", Level.advanced, confidence=0.90, source="course"
        ),
    ]
    requirements = [
        RoleSkillRequirement(
            ROLE_BACKEND_DEVELOPER, SKILL_PYTHON, "Python", "intermediate", weight=5
        ),
    ]
    assert compute_gap(student, requirements) == []


def test_compute_gap_gives_identical_output_on_repeated_calls(
    partial_student_vector, backend_developer_requirements
):
    """TC-F2-03: a pure function returns the same result every time."""
    first = compute_gap(partial_student_vector, backend_developer_requirements)
    second = compute_gap(partial_student_vector, backend_developer_requirements)
    assert first == second
