"""UP-12: M3's skill vector updates go through M1 and only ever raise a level
(TC-F1-11, TC-F1-14; REQ-F1-29, F1-30), against real Postgres."""

import pytest
from sqlalchemy import select

from backend.profile import staleness
from backend.shared.skill_vector import (
    InvalidSkillVectorError,
    Level,
    ProfileNotFoundError,
    SkillVector,
    SkillVectorEntry,
    Source,
)
from backend.skills import vector as vector_module
from backend.skills.models import SkillChangeHistory, StudentSkill
from backend.skills.vector import VectorUpdate, apply_vector_update

SKILLS = "/api/v1/profile/skills"


@pytest.fixture
def student_id(client, student) -> int:
    return client.get("/api/v1/profile", headers=student).json()["student_id"]


@pytest.fixture
def stale_calls():
    calls: list[int] = []
    staleness.set_stale_hook(calls.append)
    yield calls
    staleness.set_stale_hook(None)


def update(db_session, student_id, skill_id, level, source="completion") -> VectorUpdate:
    return apply_vector_update(student_id, skill_id, level, source, session=db_session)


def history(db_session) -> list[tuple]:
    return [
        (h.skill_id, h.previous_level, h.new_level, h.source)
        for h in db_session.scalars(
            select(SkillChangeHistory).order_by(SkillChangeHistory.history_id)
        )
    ]


def declare(client, headers, skill, level):
    response = client.post(SKILLS, json={"skill": skill, "level": level}, headers=headers)
    assert response.status_code in (200, 201)


# --- TC-F1-11: lower or equal is a silent no-op --------------------------------


def test_tc_f1_11_a_lower_level_does_not_lower_the_stored_level(
    client, db_session, skill_ids, student, student_id, stale_calls
):
    declare(client, student, "python", "advanced")
    before = history(db_session)

    result = update(db_session, student_id, skill_ids["Python"], "intermediate")

    assert result.changed is False
    assert result.get(skill_ids["Python"]).level is Level.advanced
    assert history(db_session) == before
    assert stale_calls == []
    assert db_session.scalars(
        select(StudentSkill).where(StudentSkill.source == "completion")
    ).all() == []


def test_an_equal_level_is_also_a_no_op(
    client, db_session, skill_ids, student, student_id, stale_calls
):
    declare(client, student, "python", "intermediate")
    result = update(db_session, student_id, skill_ids["Python"], "intermediate")
    assert result.changed is False
    assert stale_calls == []


# --- TC-F1-14: a completion raises the level through M1 -------------------------


def test_tc_f1_14_a_completion_adds_a_new_skill_with_source_completion(
    client, db_session, skill_ids, student, student_id, stale_calls
):
    result = update(db_session, student_id, skill_ids["React"], Level.beginner, Source.completion)

    assert result.changed is True
    entry = result.get(skill_ids["React"])
    assert (entry.level, entry.source, entry.confidence) == (
        Level.beginner, Source.completion, None,
    )
    assert history(db_session) == [(skill_ids["React"], None, "beginner", "completion")]
    assert stale_calls == [student_id]
    vector = client.get("/api/v1/profile/skill-vector", headers=student).json()["entries"]
    assert [(e["canonical_skill_name"], e["level"], e["source"]) for e in vector] == [
        ("React", "beginner", "completion"),
    ]


def test_a_higher_level_raises_the_skill_and_keeps_the_other_sources(
    client, db_session, skill_ids, student, student_id, stale_calls
):
    python = skill_ids["Python"]
    declare(client, student, "python", "beginner")

    result = update(db_session, student_id, python, "intermediate")

    assert result.changed is True
    assert result.get(python).level is Level.intermediate
    assert result.get(python).source is Source.completion
    rows = sorted(
        (r.source, r.level)
        for r in db_session.scalars(select(StudentSkill).where(StudentSkill.skill_id == python))
    )
    assert rows == [("completion", "intermediate"), ("manual", "beginner")]
    assert history(db_session)[-1] == (python, None, "intermediate", "completion")
    assert len(stale_calls) == 1


def test_a_later_higher_completion_updates_the_same_row(
    db_session, skill_ids, student_id, stale_calls
):
    python = skill_ids["Python"]
    update(db_session, student_id, python, "beginner")
    update(db_session, student_id, python, "advanced")

    rows = db_session.scalars(select(StudentSkill).where(StudentSkill.skill_id == python)).all()
    assert [(r.source, r.level) for r in rows] == [("completion", "advanced")]
    assert history(db_session) == [
        (python, None, "beginner", "completion"),
        (python, "beginner", "advanced", "completion"),
    ]
    assert len(stale_calls) == 2


def test_the_result_is_the_contracts_skill_vector(db_session, skill_ids, student_id):
    result = update(db_session, student_id, skill_ids["Python"], "beginner")
    assert isinstance(result, SkillVector)
    assert result.entries == vector_module.get_skill_vector(student_id, db_session).entries


def test_a_no_op_result_equals_the_vector_read_before_it(
    client, db_session, skill_ids, student, student_id
):
    """M3's PR-5 checks `after != before` against get_skill_vector(); a no-op
    must compare equal there, and a raise must not."""
    declare(client, student, "python", "advanced")
    before = vector_module.get_skill_vector(student_id, db_session)
    assert update(db_session, student_id, skill_ids["Python"], "beginner") == before
    assert update(db_session, student_id, skill_ids["React"], "beginner") != before


def test_vector_update_compares_by_entries_only():
    entry = SkillVectorEntry(1, "Python", Level.beginner, confidence=None, source="manual")
    plain = SkillVector((entry,))
    assert VectorUpdate((entry,), changed=True) == plain
    assert plain == VectorUpdate((entry,), changed=False)
    assert VectorUpdate((), changed=False) != plain
    assert VectorUpdate((entry,)) != "not a vector"
    assert hash(VectorUpdate((entry,), changed=True)) == hash(plain)


def test_levels_and_sources_may_be_given_as_strings_or_enums(
    db_session, skill_ids, student_id
):
    assert update(db_session, student_id, skill_ids["Python"], "beginner", "completion").changed
    assert update(
        db_session, student_id, skill_ids["Python"], Level.advanced, Source.completion
    ).changed


# --- Rejected calls --------------------------------------------------------------


def test_an_unknown_student_raises(db_session, skill_ids):
    with pytest.raises(ProfileNotFoundError):
        update(db_session, 999_999, skill_ids["Python"], "beginner")


def test_an_unknown_skill_raises_and_writes_nothing(db_session, skill_ids, student_id):
    with pytest.raises(InvalidSkillVectorError, match="not in the taxonomy"):
        update(db_session, student_id, 999_999, "beginner")
    assert history(db_session) == []


@pytest.mark.parametrize(("level", "source"), [("expert", "completion"), ("beginner", "quiz")])
def test_an_unknown_level_or_source_raises(db_session, skill_ids, student_id, level, source):
    with pytest.raises(InvalidSkillVectorError):
        update(db_session, student_id, skill_ids["Python"], level, source)


# --- Without a caller session ----------------------------------------------------


def test_without_a_session_it_uses_and_commits_its_own(
    db_session, skill_ids, student_id, monkeypatch
):
    committed = []
    original = db_session.commit

    def tracking_commit():
        committed.append(True)
        original()

    monkeypatch.setattr(db_session, "commit", tracking_commit)
    def one_session():
        yield db_session

    monkeypatch.setattr(vector_module, "get_session", one_session)

    result = apply_vector_update(student_id, skill_ids["Python"], "beginner")

    assert result.changed is True
    assert committed == [True]
