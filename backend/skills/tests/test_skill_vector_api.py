"""UP-11: the skill vector, computed from student_skill and exposed in the
frozen contract format, against real Postgres (see backend/conftest.py)."""

from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from backend.profile.models import Student
from backend.shared.skill_vector import (
    Level,
    ProfileNotFoundError,
    SkillVector,
    SkillVectorEntry,
    Source,
)
from backend.skills import vector as vector_module
from backend.skills.models import StudentSkill
from backend.skills.vector import get_skill_vector

URL = "/api/v1/profile/skill-vector"
SKILLS = "/api/v1/profile/skills"
CONTRACT_FIELDS = {
    "canonical_skill_id", "canonical_skill_name", "level", "confidence", "source",
}


@pytest.fixture
def student_id(db_session, student) -> int:
    """The student_id of the `student` fixture's profile (the newest one)."""
    newest = select(Student.student_id).order_by(Student.student_id.desc())
    return db_session.scalars(newest).first()


def hold(db_session, student_id, skill_id, source, level, confidence=None):
    """A skill arriving from a source other than manual entry (courses, confirmed
    resume skills and completions write these rows once they exist)."""
    db_session.add(StudentSkill(
        student_id=student_id, skill_id=skill_id, source=source, level=level,
        confidence=confidence,
    ))
    db_session.flush()


def entries(client, headers) -> list[dict]:
    response = client.get(URL, headers=headers)
    assert response.status_code == 200
    return response.json()["entries"]


# --- TC-F1-10, REQ-F1-28 ------------------------------------------------------


def test_tc_f1_10_highest_level_wins_and_both_sources_stay_recorded(
    client, db_session, skill_ids, student, student_id
):
    python = skill_ids["Python"]
    hold(db_session, student_id, python, "course", "beginner")
    hold(db_session, student_id, python, "resume", "advanced", Decimal("0.90"))

    assert entries(client, student) == [{
        "canonical_skill_id": python,
        "canonical_skill_name": "Python",
        "level": "advanced",
        "confidence": 0.9,
        "source": "resume",
    }]
    recorded = db_session.scalars(
        select(StudentSkill.source).where(StudentSkill.skill_id == python)
    ).all()
    assert sorted(recorded) == ["course", "resume"]


def test_the_winning_row_supplies_source_and_confidence(
    client, db_session, skill_ids, student, student_id
):
    sql = skill_ids["SQL Basics"]
    hold(db_session, student_id, sql, "resume", "beginner", Decimal("0.55"))
    client.post(SKILLS, json={"skill": "sql", "level": "intermediate"}, headers=student)

    assert entries(client, student) == [{
        "canonical_skill_id": sql,
        "canonical_skill_name": "SQL Basics",
        "level": "intermediate",
        "confidence": None,  # manually declared
        "source": "manual",
    }]


def test_equal_levels_go_to_the_stronger_evidence(
    client, db_session, skill_ids, student, student_id
):
    react = skill_ids["React"]
    client.post(SKILLS, json={"skill": "reactjs", "level": "intermediate"}, headers=student)
    hold(db_session, student_id, react, "course", "intermediate")
    assert entries(client, student)[0]["source"] == "course"
    hold(db_session, student_id, react, "completion", "intermediate", Decimal("1.00"))
    assert entries(client, student)[0]["source"] == "completion"


# --- REQ-F1-26: recomputed on every change ---------------------------------------


def test_the_vector_follows_every_change_to_the_profile(
    client, db_session, skill_ids, student, student_id
):
    assert entries(client, student) == []

    client.post(SKILLS, json={"skill": "python3", "level": "beginner"}, headers=student)
    assert [(e["canonical_skill_name"], e["level"]) for e in entries(client, student)] == [
        ("Python", "beginner"),
    ]

    client.post(SKILLS, json={"skill": "Python", "level": "advanced"}, headers=student)  # edit
    client.post(SKILLS, json={"skill": "react.js", "level": "intermediate"}, headers=student)
    assert {(e["canonical_skill_name"], e["level"]) for e in entries(client, student)} == {
        ("Python", "advanced"), ("React", "intermediate"),
    }

    db_session.execute(delete(StudentSkill).where(StudentSkill.skill_id == skill_ids["React"]))
    assert [e["canonical_skill_name"] for e in entries(client, student)] == ["Python"]


def test_each_skill_appears_once_in_skill_id_order(
    client, db_session, skill_ids, student, student_id
):
    for name in ["SQL Basics", "React", "Python"]:
        for source, level in [("course", "beginner"), ("resume", "intermediate")]:
            hold(db_session, student_id, skill_ids[name], source, level, Decimal("0.70"))

    ids = [e["canonical_skill_id"] for e in entries(client, student)]
    assert ids == sorted(skill_ids.values())


# --- REQ-F1-27: frozen contract format ---------------------------------------------


def test_every_entry_has_exactly_the_contract_fields(client, skill_ids, student):
    client.post(SKILLS, json={"skill": "py", "level": "beginner"}, headers=student)
    (entry,) = entries(client, student)
    assert set(entry) == CONTRACT_FIELDS
    assert entry["level"] in {level.value for level in Level}
    assert entry["source"] in {source.value for source in Source}


def test_get_skill_vector_returns_the_shared_contract_types(
    db_session, skill_ids, student, student_id
):
    hold(db_session, student_id, skill_ids["Python"], "course", "intermediate")
    hold(db_session, student_id, skill_ids["Python"], "completion", "advanced", Decimal("1"))

    result = get_skill_vector(student_id, db_session)

    assert isinstance(result, SkillVector)
    assert result.entries == (SkillVectorEntry(
        canonical_skill_id=skill_ids["Python"],
        canonical_skill_name="Python",
        level=Level.advanced,
        confidence=Decimal("1.00"),
        source=Source.completion,
    ),)


def test_get_skill_vector_opens_its_own_session_when_given_none(
    db_session, skill_ids, student, student_id, monkeypatch
):
    hold(db_session, student_id, skill_ids["React"], "manual", "beginner")
    closed = []

    def own_session():
        try:
            yield db_session
        finally:
            closed.append(True)

    monkeypatch.setattr(vector_module, "get_session", own_session)
    assert [e.canonical_skill_name for e in get_skill_vector(student_id)] == ["React"]
    assert closed == [True]


def test_get_skill_vector_refuses_a_student_without_a_profile(db_session):
    with pytest.raises(ProfileNotFoundError):
        get_skill_vector(999_999, db_session)


# --- Access (REQ-F1-39) ---------------------------------------------------------


def test_each_student_sees_only_their_own_vector(client, skill_ids, make_user, bearer, student):
    other = bearer(make_user())
    client.post("/api/v1/profile", json={"name": "Ravi"}, headers=other)
    client.post(SKILLS, json={"skill": "sql", "level": "advanced"}, headers=other)

    assert entries(client, student) == []
    assert [e["canonical_skill_name"] for e in entries(client, other)] == ["SQL Basics"]


def test_without_a_profile_returns_404(client, make_user, bearer):
    response = client.get(URL, headers=bearer(make_user()))
    assert response.status_code == 404
    assert response.json() == {"detail": "Profile not found"}


def test_requires_a_student_token(client, make_user, bearer):
    assert client.get(URL).status_code == 401
    faculty = bearer(make_user("faculty_mentor"), role="faculty_mentor")
    assert client.get(URL, headers=faculty).status_code == 403


# --- TC-F1-13: the vector M1 produces is what M2's gap analysis consumes ------------


@pytest.mark.xfail(
    raises=NotImplementedError, reason="compute_gap() (RM-1, M2) not implemented yet"
)
def test_tc_f1_13_gap_analysis_consumes_the_vector(
    client, db_session, skill_ids, student, student_id
):
    from sqlalchemy import text

    from backend.gap.service import RoleSkillRequirement, compute_gap

    docker = db_session.execute(text(
        "INSERT INTO skill (skill_name, category) VALUES ('Docker', 'Test') RETURNING skill_id"
    )).scalar_one()
    client.post(SKILLS, json={"skill": "Python", "level": "intermediate"}, headers=student)
    client.post(SKILLS, json={"skill": "sql", "level": "beginner"}, headers=student)
    required = [
        RoleSkillRequirement(1, skill_ids["Python"], "Python", Level.advanced, 3),
        RoleSkillRequirement(1, skill_ids["SQL Basics"], "SQL Basics", Level.intermediate, 2),
        RoleSkillRequirement(1, docker, "Docker", Level.beginner, 1),
    ]

    gap = compute_gap(list(get_skill_vector(student_id, db_session)), required)

    assert [(item.skill_name, item.current_level) for item in gap] == [
        ("Python", Level.intermediate), ("SQL Basics", Level.beginner), ("Docker", None),
    ]
