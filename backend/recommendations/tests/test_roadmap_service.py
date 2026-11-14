"""RM-4: the roadmap use case, with no database (fakes)."""

import pytest

from backend.gap.exceptions import NoTargetRoleError
from backend.gap.service import GapItem
from backend.gap.student_gap import StudentGap
from backend.recommendations.engine import Resource
from backend.recommendations.service import RoadmapService
from backend.shared.skill_vector import Level

PYTHON = 1
SQL = 2

PYTHON_GAP = GapItem(
    PYTHON, "Python", Level.intermediate, current_level=Level.beginner, weight=5, rank=1
)
SQL_GAP = GapItem(SQL, "SQL Basics", Level.beginner, current_level=None, weight=3, rank=2)


class FakeGaps:
    """Stands in for StudentGapService."""

    def __init__(self, gap=None, error=None):
        self._gap = gap
        self._error = error

    def gap_for_user(self, user_id):
        if self._error is not None:
            raise self._error
        return self._gap


class FakeResources:
    """Stands in for ResourceRepository and records what was asked for."""

    def __init__(self, resources=()):
        self._resources = list(resources)
        self.asked = []

    def approved_for_skills(self, skill_ids):
        self.asked.append(list(skill_ids))
        return list(self._resources)


def make_gap(*items):
    return StudentGap(role_id=3, role_name="Backend Developer", items=list(items))


def resource(item_id, skill_id, level):
    return Resource(
        item_id=item_id,
        skill_id=skill_id,
        title=f"Resource {item_id}",
        item_type="course",
        coverage_level=level,
        source_url=f"https://example.com/{item_id}",
    )


def test_each_gap_item_gets_its_own_ranked_resources_from_one_query():
    resources = FakeResources(
        [
            resource(10, SQL, Level.beginner),
            resource(11, PYTHON, Level.intermediate),
            resource(12, PYTHON, Level.beginner),  # the student already holds this level
        ]
    )
    service = RoadmapService(FakeGaps(make_gap(PYTHON_GAP, SQL_GAP)), resources)

    roadmap = service.roadmap_for_user(11)

    assert (roadmap.role_id, roadmap.role_name) == (3, "Backend Developer")
    assert [entry.gap for entry in roadmap.entries] == [PYTHON_GAP, SQL_GAP]
    assert [[r.item_id for r in entry.resources] for entry in roadmap.entries] == [[11], [10]]
    assert resources.asked == [[PYTHON, SQL]]


def test_a_gap_skill_without_resources_has_an_empty_list():
    service = RoadmapService(FakeGaps(make_gap(SQL_GAP)), FakeResources([]))

    assert service.roadmap_for_user(11).entries[0].resources == []


def test_no_gap_means_no_catalogue_query():
    resources = FakeResources([resource(10, SQL, Level.beginner)])

    roadmap = RoadmapService(FakeGaps(make_gap()), resources).roadmap_for_user(11)

    assert roadmap.entries == []
    assert resources.asked == []


def test_gap_errors_are_not_swallowed():
    service = RoadmapService(FakeGaps(error=NoTargetRoleError()), FakeResources())

    with pytest.raises(NoTargetRoleError):
        service.roadmap_for_user(11)
