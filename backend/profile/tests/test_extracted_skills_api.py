"""UP-7 and UP-8: skills found in an uploaded resume are proposed, and reach
the profile only once the student confirms them. Real Postgres."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from backend.database import get_session
from backend.main import app
from backend.profile import staleness
from backend.profile.tests.resume_files import RESUME_LINES, pdf_with_text, pdf_without_text
from backend.skills.models import SkillChangeHistory, StudentSkill

RESUME = "/api/v1/profile/resume"
EXTRACTED = "/api/v1/profile/resume/extracted"
CONFIRM = "/api/v1/profile/skills/confirm"
BULK = "/api/v1/profile/skills/confirm-high-confidence"
VECTOR = "/api/v1/profile/skill-vector"

# RESUME_LINES: "Skills: Python, SQL, React, Docker, Git", then a project
# sentence naming FastAPI and PostgreSQL, then "Experience: ... Pandas".
TAXONOMY = {
    "Python": [], "SQL Basics": ["sql"], "React": ["react.js"], "Docker": [], "Pandas": [],
}


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("RESUME_STORAGE_DIR", str(tmp_path))
    monkeypatch.delenv("RESUME_HIGH_CONFIDENCE_THRESHOLD", raising=False)
    return tmp_path


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def skill_ids(db_session) -> dict[str, int]:
    ids = {}
    for name, aliases in TAXONOMY.items():
        ids[name] = db_session.execute(
            text("INSERT INTO skill (skill_name, category) VALUES (:n, 'Test') RETURNING skill_id"),
            {"n": name},
        ).scalar_one()
        for alias in aliases:
            db_session.execute(
                text("INSERT INTO skill_alias (skill_id, alias_text) VALUES (:s, :a)"),
                {"s": ids[name], "a": alias},
            )
    return ids


@pytest.fixture
def student(client, make_user, bearer) -> dict:
    headers = bearer(make_user())
    assert client.post("/api/v1/profile", json={"name": "Asha"}, headers=headers).status_code == 201
    return headers


@pytest.fixture
def stale_calls():
    calls: list[int] = []
    staleness.set_stale_hook(calls.append)
    yield calls
    staleness.set_stale_hook(None)


def upload(client, headers, lines=RESUME_LINES):
    response = client.post(
        RESUME, files={"file": ("cv.pdf", pdf_with_text(lines), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 201, response.json()
    return response.json()


def pending(client, headers, **params) -> list[dict]:
    response = client.get(EXTRACTED, headers=headers, params=params)
    assert response.status_code == 200, response.json()
    return response.json()["candidates"]


def by_name(candidates) -> dict[str, dict]:
    return {c["skill_name"]: c for c in candidates}


def profile_skills(db_session) -> list[tuple]:
    return sorted(
        (s.skill_id, s.level, s.source)
        for s in db_session.scalars(select(StudentSkill))
    )


# --- UP-7: extraction (REQ-F1-12 to F1-14) ------------------------------------


def test_upload_proposes_skills_with_confidence_and_source_sentence(
    client, db_session, skill_ids, student
):
    result = upload(client, student)

    assert (result["status"], result["skills_found"], result["message"]) == ("extracted", 5, None)
    assert result["manual_entry"] is None
    found = by_name(pending(client, student))
    assert set(found) == {"Python", "SQL Basics", "React", "Docker", "Pandas"}
    assert found["Python"] == {
        "candidate_id": found["Python"]["candidate_id"],
        "upload_id": result["upload_id"],
        "skill_id": skill_ids["Python"],
        "skill_name": "Python",
        "suggested_level": "beginner",
        "confidence": 0.7,
        "source_sentence": "Skills: Python, SQL, React, Docker, Git",
        "status": "pending",
    }
    assert found["Pandas"]["suggested_level"] == "intermediate"
    assert found["Pandas"]["source_sentence"].endswith("data pipelines with Pandas")


def test_nothing_reaches_the_profile_before_confirmation(client, db_session, skill_ids, student):
    """REQ-F1-15: extracted skills are proposals only."""
    upload(client, student)
    assert profile_skills(db_session) == []
    assert client.get(VECTOR, headers=student).json()["entries"] == []


def test_candidates_are_ordered_and_filtered_by_confidence(client, skill_ids, student):
    """REQ-F1-13."""
    upload(client, student)

    candidates = pending(client, student)
    confidences = [c["confidence"] for c in candidates]
    assert confidences == sorted(confidences, reverse=True)
    assert [c["skill_name"] for c in pending(client, student, min_confidence=0.65)] == [
        "Python", "SQL Basics", "React", "Docker",
    ]
    assert pending(client, student, min_confidence=0.95) == []


def test_a_resume_with_no_known_skills_suggests_manual_entry(client, skill_ids, student):
    result = upload(client, student, [
        "Asha Rao - Computer Science undergraduate, PES University",
        "Hobbies: chess, hiking, and reading long novels about the sea and mountains",
    ])
    assert result["skills_found"] == 0
    assert "add your skills manually" in result["message"]
    assert result["manual_entry"] is not None


def test_an_unreadable_resume_proposes_nothing_and_changes_nothing(
    client, db_session, skill_ids, student
):
    """TC-F1-07."""
    response = client.post(
        RESUME, files={"file": ("scan.pdf", pdf_without_text(), "application/pdf")},
        headers=student,
    )
    assert response.json()["status"] == "unreadable"
    assert response.json()["skills_found"] is None
    assert pending(client, student, status="all") == []
    assert profile_skills(db_session) == []


# --- UP-8: confirm, edit or reject each one (REQ-F1-16) -------------------------


def test_confirm_edit_and_reject_individually(
    client, db_session, skill_ids, student, stale_calls
):
    upload(client, student)
    found = by_name(pending(client, student))

    response = client.post(CONFIRM, headers=student, json={"decisions": [
        {"candidate_id": found["Python"]["candidate_id"], "action": "confirm"},
        {"candidate_id": found["React"]["candidate_id"], "action": "confirm",
         "level": "advanced"},
        {"candidate_id": found["Docker"]["candidate_id"], "action": "reject"},
    ]})

    assert response.status_code == 200, response.json()
    assert [(d["skill_name"], d["status"], d["level"]) for d in response.json()] == [
        ("Python", "confirmed", "beginner"),
        ("React", "confirmed", "advanced"),
        ("Docker", "rejected", None),
    ]
    assert profile_skills(db_session) == sorted([
        (skill_ids["Python"], "beginner", "resume"),
        (skill_ids["React"], "advanced", "resume"),
    ])
    vector = {e["canonical_skill_name"]: e for e in client.get(VECTOR, headers=student).json()[
        "entries"]}
    assert vector["React"]["source"] == "resume"
    assert vector["React"]["confidence"] == 0.7
    assert set(by_name(pending(client, student))) == {"SQL Basics", "Pandas"}
    assert len(stale_calls) == 1


def test_confirming_writes_the_change_history(client, db_session, skill_ids, student):
    upload(client, student)
    python = by_name(pending(client, student))["Python"]["candidate_id"]
    client.post(CONFIRM, headers=student, json={"decisions": [
        {"candidate_id": python, "action": "confirm"},
    ]})
    history = db_session.scalars(select(SkillChangeHistory)).all()
    assert [(h.skill_id, h.previous_level, h.new_level, h.source) for h in history] == [
        (skill_ids["Python"], None, "beginner", "resume"),
    ]


def test_a_second_resume_updates_the_resume_skill_instead_of_duplicating(
    client, db_session, skill_ids, student
):
    upload(client, student)
    first = by_name(pending(client, student))["Python"]["candidate_id"]
    client.post(CONFIRM, headers=student, json={"decisions": [
        {"candidate_id": first, "action": "confirm"},
    ]})
    upload(client, student, [
        "Asha Rao - Computer Science undergraduate, PES University",
        "Expert in Python, with years of production work in it every day.",
    ])
    second = by_name(pending(client, student))["Python"]

    client.post(CONFIRM, headers=student, json={"decisions": [
        {"candidate_id": second["candidate_id"], "action": "confirm"},
    ]})

    assert second["suggested_level"] == "advanced"
    assert profile_skills(db_session) == [(skill_ids["Python"], "advanced", "resume")]


def test_rejecting_only_stores_nothing_and_marks_nothing_stale(
    client, db_session, skill_ids, student, stale_calls
):
    upload(client, student)
    docker = by_name(pending(client, student))["Docker"]["candidate_id"]
    client.post(CONFIRM, headers=student, json={"decisions": [
        {"candidate_id": docker, "action": "reject"},
    ]})
    assert profile_skills(db_session) == []
    assert stale_calls == []
    assert by_name(pending(client, student, status="rejected")).keys() == {"Docker"}


def test_a_decided_skill_cannot_be_decided_again_and_nothing_else_applies(
    client, db_session, skill_ids, student
):
    upload(client, student)
    found = by_name(pending(client, student))
    python, react = found["Python"]["candidate_id"], found["React"]["candidate_id"]
    client.post(CONFIRM, headers=student, json={"decisions": [
        {"candidate_id": python, "action": "reject"},
    ]})

    response = client.post(CONFIRM, headers=student, json={"decisions": [
        {"candidate_id": react, "action": "confirm"},
        {"candidate_id": python, "action": "confirm"},
    ]})

    assert response.status_code == 409
    assert profile_skills(db_session) == []
    assert "React" in by_name(pending(client, student))


@pytest.mark.parametrize("body", [
    {"decisions": []},
    {"decisions": [{"candidate_id": 1, "action": "keep"}]},
    {"decisions": [{"candidate_id": 1, "action": "confirm", "level": "guru"}]},
    {"decisions": [{"candidate_id": 1, "action": "reject", "level": "advanced"}]},
    {"decisions": [{"candidate_id": 1, "action": "reject"},
                   {"candidate_id": 1, "action": "confirm"}]},
])
def test_malformed_decisions_are_rejected(client, student, body):
    assert client.post(CONFIRM, headers=student, json=body).status_code == 422


def test_students_cannot_see_or_decide_each_others_skills(
    client, db_session, skill_ids, student, make_user, bearer
):
    upload(client, student)
    python = by_name(pending(client, student))["Python"]["candidate_id"]
    other = bearer(make_user())
    client.post("/api/v1/profile", json={"name": "Ben"}, headers=other)

    assert pending(client, other) == []
    response = client.post(CONFIRM, headers=other, json={"decisions": [
        {"candidate_id": python, "action": "confirm"},
    ]})
    assert response.status_code == 404
    assert profile_skills(db_session) == []


def test_without_a_profile_or_a_token(client, make_user, bearer):
    headers = bearer(make_user())
    assert client.get(EXTRACTED, headers=headers).status_code == 404
    assert client.post(BULK, headers=headers).status_code == 404
    assert client.get(EXTRACTED).status_code == 401


# --- UP-8: bulk confirm above the threshold (REQ-F1-17) -------------------------


def test_bulk_confirm_takes_only_skills_at_or_above_the_threshold(
    client, db_session, skill_ids, student, monkeypatch, stale_calls
):
    monkeypatch.setenv("RESUME_HIGH_CONFIDENCE_THRESHOLD", "0.70")  # Pandas is 0.60
    upload(client, student)
    assert client.get(EXTRACTED, headers=student).json()["threshold"] == 0.7

    response = client.post(BULK, headers=student)

    assert response.status_code == 200
    body = response.json()
    assert body["threshold"] == 0.7
    assert sorted(d["skill_name"] for d in body["confirmed"]) == [
        "Docker", "Python", "React", "SQL Basics",
    ]
    assert len(profile_skills(db_session)) == 4
    assert [c["skill_name"] for c in pending(client, student)] == ["Pandas"]
    assert len(stale_calls) == 1


def test_bulk_confirm_with_nothing_above_the_default_threshold_changes_nothing(
    client, db_session, skill_ids, student, stale_calls
):
    upload(client, student)  # every candidate is below the 0.80 default

    body = client.post(BULK, headers=student).json()

    assert (body["threshold"], body["confirmed"]) == (0.8, [])
    assert profile_skills(db_session) == []
    assert stale_calls == []
