"""UP-11: the merge rules of build_vector(), without a database."""

from decimal import Decimal

import pytest

from backend.shared.skill_vector import InvalidSkillVectorError, Level, Source
from backend.skills.vector import SkillRow, build_vector


def row(skill_id, source, level, confidence=None, name=None):
    return SkillRow(skill_id, name or f"Skill {skill_id}", source, level, confidence)


def test_no_rows_is_an_empty_vector():
    assert len(build_vector([])) == 0


@pytest.mark.parametrize("order", [1, -1])
def test_highest_level_wins_whatever_the_row_order(order):
    rows = [row(1, "course", "beginner"), row(1, "resume", "advanced", Decimal("0.8"))][::order]
    (entry,) = build_vector(rows)
    assert (entry.level, entry.source, entry.confidence) == (
        Level.advanced, Source.resume, Decimal("0.80"),
    )


def test_level_is_compared_by_rank_not_alphabetically():
    # Alphabetically "intermediate" > "advanced"; by rank it is lower.
    (entry,) = build_vector([row(1, "manual", "intermediate"), row(1, "course", "advanced")])
    assert entry.level is Level.advanced


@pytest.mark.parametrize(
    ("sources", "winner"),
    [
        (["manual", "course"], "course"),
        (["course", "resume"], "resume"),
        (["resume", "completion"], "completion"),
        (["completion", "manual", "resume", "course"], "completion"),
    ],
)
def test_equal_levels_go_to_the_stronger_evidence(sources, winner):
    (entry,) = build_vector([row(1, source, "intermediate") for source in sources])
    assert entry.source == Source(winner)


def test_several_skills_each_appear_once_sorted_by_id():
    rows = [
        row(9, "manual", "beginner"),
        row(2, "course", "advanced"),
        row(9, "resume", "advanced"),
        row(5, "manual", "intermediate"),
    ]
    assert [(e.canonical_skill_id, e.level) for e in build_vector(rows)] == [
        (2, Level.advanced), (5, Level.intermediate), (9, Level.advanced),
    ]


def test_a_row_outside_the_contract_is_refused():
    with pytest.raises(ValueError):
        build_vector([row(1, "manual", "expert")])
    with pytest.raises(InvalidSkillVectorError):
        build_vector([row(1, "manual", "beginner", Decimal("1.5"))])
