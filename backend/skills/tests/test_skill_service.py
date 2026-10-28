"""SkillService logic with in-memory fakes (no database)."""

from types import SimpleNamespace

import pytest

from backend.profile.exceptions import ProfileNotFoundError
from backend.skills.exceptions import UnknownSkillError
from backend.skills.service import SkillService
from backend.taxonomy.resolver import SkillResolver, build_alias_index

NAMES = {1: "React", 2: "Python"}


class FakeTaxonomy:
    def names(self):
        return NAMES

    def resolver(self):
        return SkillResolver(build_alias_index(NAMES.items(), [(1, "ReactJS")]))


class FakeStudents:
    def get_by_user_id(self, user_id):
        return SimpleNamespace(student_id=user_id * 10) if user_id != 404 else None


class FakeSkills:
    def __init__(self, lose_insert_race=False):
        self.rows, self.changes = {}, []
        self.lose_insert_race = lose_insert_race

    def get(self, student_id, skill_id, source):
        return self.rows.get((student_id, skill_id, source))

    def add(self, entry):
        key = (entry.student_id, entry.skill_id, entry.source)
        if self.lose_insert_race:  # another request inserted the row first
            self.rows[key] = SimpleNamespace(level="beginner")
            return False
        self.rows[key] = entry
        return True

    def record_change(self, student_id, skill_id, previous, new, source):
        self.changes.append((skill_id, previous, new, source))


def service(skills=None):
    return SkillService(FakeStudents(), skills or FakeSkills(), FakeTaxonomy())


def test_new_skill_is_created_and_recorded():
    skills = FakeSkills()
    result = service(skills).declare_skill(1, "reactjs", "beginner")
    assert (result.skill_name, result.created, result.changed) == ("React", True, True)
    assert skills.changes == [(1, None, "beginner", "manual")]


def test_same_level_again_changes_nothing():
    skills = FakeSkills()
    svc = service(skills)
    svc.declare_skill(1, "React", "beginner")
    result = svc.declare_skill(1, " react ", "beginner")
    assert (result.created, result.changed) == (False, False)
    assert len(skills.changes) == 1


def test_lowering_a_manually_declared_level_is_allowed():
    """A manual declaration is the student's own correction (SRS 5.1, sequence 4),
    unlike completion updates, which may only raise a level (UP-12)."""
    skills = FakeSkills()
    svc = service(skills)
    svc.declare_skill(1, "Python", "advanced")
    result = svc.declare_skill(1, "Python", "beginner")
    assert result.level == "beginner"
    assert skills.changes[-1] == (2, "advanced", "beginner", "manual")


def test_losing_an_insert_race_updates_the_row_that_won():
    skills = FakeSkills(lose_insert_race=True)
    result = service(skills).declare_skill(1, "Python", "advanced")
    assert (result.created, result.changed, result.level) == (False, True, "advanced")
    assert skills.changes == [(2, "beginner", "advanced", "manual")]


def test_unknown_skill_carries_suggestions():
    with pytest.raises(UnknownSkillError) as error:
        service().declare_skill(1, "Reakt", "beginner")
    assert error.value.raw == "Reakt"
    assert error.value.suggestions == [(1, "React")]


def test_no_profile_raises():
    with pytest.raises(ProfileNotFoundError):
        service().declare_skill(404, "React", "beginner")
