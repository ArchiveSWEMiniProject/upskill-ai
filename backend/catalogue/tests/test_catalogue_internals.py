"""Unit tests for catalogue skill resolution and get_resources_for_skill() (CA-4,
CA-11), backfilled in Sprint 3 for the branches the API tests do not reach.

Seeded skills (conftest.py): 1 Docker (alias "docker containers"), 2 Python,
3 PostgreSQL, 4 Go.
"""

import pytest
from fastapi import HTTPException

from backend.catalogue import service
from backend.catalogue.models import (
    LearningItem,
    LearningItemSkill,
    LearningItemType,
    ModerationState,
    SkillLevel,
)
from backend.catalogue.schemas import SkillTagInput
from backend.catalogue.service import get_resources_for_skill
from backend.catalogue.validators import resolve_canonical_skill

# --- resolve_canonical_skill ----------------------------------------------------


def test_resolves_by_skill_id(db_session):
    assert resolve_canonical_skill(SkillTagInput(skill_id=2), db_session) == (2, "Python")


def test_unknown_skill_id_is_rejected(db_session):
    with pytest.raises(HTTPException) as excinfo:
        resolve_canonical_skill(SkillTagInput(skill_id=99), db_session)
    assert excinfo.value.status_code == 400
    assert "Skill ID 99" in excinfo.value.detail


@pytest.mark.parametrize("tag", [SkillTagInput(), SkillTagInput(skill_name="   ")])
def test_tag_without_id_or_name_is_rejected(db_session, tag):
    with pytest.raises(HTTPException) as excinfo:
        resolve_canonical_skill(tag, db_session)
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Skill tag must provide either a skill_id or skill_name."


def test_resolves_canonical_name_ignoring_case_and_spaces(db_session):
    assert resolve_canonical_skill(SkillTagInput(skill_name="  postgresql "), db_session) == (
        3, "PostgreSQL",
    )


def test_resolves_alias_to_its_canonical_skill(db_session):
    assert resolve_canonical_skill(SkillTagInput(skill_name="Docker Containers"), db_session) == (
        1, "Docker",
    )


def test_unknown_name_lists_closest_matches(db_session):
    with pytest.raises(HTTPException) as excinfo:
        resolve_canonical_skill(SkillTagInput(skill_name="Pythn"), db_session)
    assert excinfo.value.status_code == 400
    assert "Closest matching canonical skills: Python" in excinfo.value.detail


def test_unknown_name_with_nothing_close_has_no_suggestions(db_session):
    with pytest.raises(HTTPException) as excinfo:
        resolve_canonical_skill(SkillTagInput(skill_name="zzzzzzzzzzzz"), db_session)
    assert "Closest matching" not in excinfo.value.detail


# --- get_resources_for_skill ----------------------------------------------------


def add_item(db, title, level, state, skill_ids):
    item = LearningItem(
        title=title,
        description=f"{title} description",
        item_type=LearningItemType.COURSE,
        level=level,
        duration="2h",
        source_url=f"https://example.com/{title.replace(' ', '-').lower()}",
        source="Example",
        moderation_state=state,
    )
    item.skills = [
        LearningItemSkill(skill_id=skill_id, coverage_level=level) for skill_id in skill_ids
    ]
    db.add(item)
    db.flush()
    return item.item_id


@pytest.fixture
def items(db_session):
    return {
        "python basics": add_item(
            db_session, "Python Basics", SkillLevel.BEGINNER, ModerationState.APPROVED, [2]
        ),
        "python advanced": add_item(
            db_session, "Python Advanced", SkillLevel.ADVANCED, ModerationState.APPROVED, [2, 3]
        ),
        "python draft": add_item(
            db_session, "Python Draft", SkillLevel.BEGINNER, ModerationState.PENDING, [2]
        ),
        "go retired": add_item(
            db_session, "Go Retired", SkillLevel.BEGINNER, ModerationState.INACTIVE, [4]
        ),
    }


def titles(resources):
    return [r["title"] for r in resources]


def test_no_skill_ids_returns_nothing_without_querying():
    # No session is passed; an empty list must not even open one.
    assert get_resources_for_skill([]) == []


def test_returns_only_approved_items_in_id_order(db_session, items):
    assert titles(get_resources_for_skill([2], db=db_session)) == [
        "Python Basics", "Python Advanced",
    ]
    assert get_resources_for_skill([4], db=db_session) == []


def test_item_tagged_with_several_requested_skills_is_returned_once(db_session, items):
    assert titles(get_resources_for_skill([2, 3], db=db_session)) == [
        "Python Basics", "Python Advanced",
    ]


@pytest.mark.parametrize("level", [SkillLevel.ADVANCED, "advanced", "ADVANCED"])
def test_level_filter_accepts_enum_or_string(db_session, items, level):
    assert titles(get_resources_for_skill([2], level=level, db=db_session)) == ["Python Advanced"]


def test_resource_shape_matches_the_contract(db_session, items):
    [resource] = get_resources_for_skill([3], db=db_session)
    assert resource == {
        "item_id": items["python advanced"],
        "title": "Python Advanced",
        "description": "Python Advanced description",
        "item_type": "course",
        "level": "advanced",
        "duration": "2h",
        "source_url": "https://example.com/python-advanced",
        "source": "Example",
        "moderation_state": "approved",
        "skill_tags": [
            {"skill_id": 2, "skill_name": "Python", "coverage_level": "advanced"},
            {"skill_id": 3, "skill_name": "PostgreSQL", "coverage_level": "advanced"},
        ],
    }


def test_opens_and_closes_its_own_session_when_none_is_given(db_session, items, monkeypatch):
    closed = []

    class TrackingSession:
        def __getattr__(self, name):
            return getattr(db_session, name)

        def close(self):
            closed.append(True)

    monkeypatch.setattr(service, "_session_factory", lambda: TrackingSession)
    assert titles(get_resources_for_skill([2])) == ["Python Basics", "Python Advanced"]
    assert closed == [True]
