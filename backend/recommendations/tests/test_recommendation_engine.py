"""RM-4: ranking catalogue resources for a gap item (REQ-F2-05). No database."""

import pytest

from backend.gap.service import GapItem
from backend.recommendations.engine import Resource, recommend_for_gap_item
from backend.shared.skill_vector import Level

PYTHON = 1
SQL = 2


def resource(item_id, level, skill_id=PYTHON):
    return Resource(
        item_id=item_id,
        skill_id=skill_id,
        title=f"Resource {item_id}",
        item_type="course",
        coverage_level=level,
        source_url=f"https://example.com/{item_id}",
    )


def gap(required, current=None):
    return GapItem(PYTHON, "Python", required, current_level=current, weight=5, rank=1)


def ids(resources):
    return [r.item_id for r in resources]


CATALOGUE = [
    resource(5, Level.advanced),
    resource(3, Level.intermediate),
    resource(1, Level.beginner),
    resource(4, Level.intermediate),
    resource(2, Level.beginner),
]


def test_a_student_with_no_entry_gets_every_level_up_to_the_required_one_lowest_first():
    result = recommend_for_gap_item(gap(Level.intermediate), CATALOGUE)
    assert ids(result) == [1, 2, 3, 4]


def test_levels_the_student_already_holds_are_skipped():
    result = recommend_for_gap_item(gap(Level.intermediate, current=Level.beginner), CATALOGUE)
    assert ids(result) == [3, 4]


def test_resources_above_the_required_level_are_not_recommended():
    assert ids(recommend_for_gap_item(gap(Level.beginner), CATALOGUE)) == [1, 2]


def test_an_advanced_requirement_reaches_the_advanced_resource():
    result = recommend_for_gap_item(gap(Level.advanced, current=Level.intermediate), CATALOGUE)
    assert ids(result) == [5]


def test_resources_for_other_skills_are_ignored():
    candidates = [resource(1, Level.beginner, skill_id=SQL), resource(2, Level.beginner)]
    assert ids(recommend_for_gap_item(gap(Level.beginner), candidates)) == [2]


def test_the_order_does_not_depend_on_the_order_of_the_candidates():
    forward = recommend_for_gap_item(gap(Level.advanced), CATALOGUE)
    backward = recommend_for_gap_item(gap(Level.advanced), list(reversed(CATALOGUE)))
    assert forward == backward
    assert ids(forward) == [1, 2, 3, 4, 5]


def test_no_candidates_gives_no_recommendations():
    assert recommend_for_gap_item(gap(Level.intermediate), []) == []


def test_the_candidates_are_not_modified():
    candidates = list(CATALOGUE)
    recommend_for_gap_item(gap(Level.advanced), candidates)
    assert candidates == CATALOGUE


def test_a_resource_accepts_its_level_as_a_string_and_rejects_an_unknown_one():
    assert resource(1, "intermediate").coverage_level is Level.intermediate
    with pytest.raises(ValueError):
        resource(1, "expert")
