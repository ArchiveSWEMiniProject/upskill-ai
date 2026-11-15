"""UP-13: choose a target role (TC-F1-12), against real Postgres."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.database import get_session
from backend.main import app
from backend.profile import staleness

URL = "/api/v1/profile/target-role"
SKILLS = "/api/v1/profile/skills"


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def student(client, make_user, bearer) -> dict:
    headers = bearer(make_user())
    assert client.post("/api/v1/profile", json={"name": "Asha"}, headers=headers).status_code == 201
    return headers


def _insert(db_session, sql: str, **params):
    return db_session.execute(text(sql), params).scalar_one()


@pytest.fixture
def roles(db_session) -> dict[str, int]:
    """Two roles over three skills (M4's tables; test data only). 'Backend' is
    TC-F1-13's role: Python Advanced, SQL Intermediate, Docker Beginner."""
    skills = {
        name: _insert(
            db_session,
            "INSERT INTO skill (skill_name, category) VALUES (:n, 'Test') RETURNING skill_id",
            n=name,
        )
        for name in ("Python", "SQL", "Docker")
    }
    for name in skills:
        db_session.execute(
            text("INSERT INTO skill_alias (skill_id, alias_text) VALUES (:s, :a)"),
            {"s": skills[name], "a": name.lower()},
        )
    ids = {}
    wanted = {
        "Backend": [
            ("Python", "advanced", 3),
            ("SQL", "intermediate", 2),
            ("Docker", "beginner", 1),
        ],
        "Analyst": [("SQL", "beginner", 2)],
    }
    for role, rows in wanted.items():
        ids[role] = _insert(
            db_session,
            "INSERT INTO career_role (role_name) VALUES (:n) RETURNING role_id",
            n=role,
        )
        for skill, level, weight in rows:
            db_session.execute(
                text(
                    "INSERT INTO role_skill_requirement "
                    "(role_id, skill_id, required_level, weight) "
                    "VALUES (:r, :s, CAST(:l AS skill_level), :w)"
                ),
                {"r": ids[role], "s": skills[skill], "l": level, "w": weight},
            )
    return ids


@pytest.fixture
def stale_calls():
    calls: list[int] = []
    staleness.set_stale_hook(calls.append)
    yield calls
    staleness.set_stale_hook(None)


def declare(client, headers, skill: str, level: str) -> None:
    response = client.post(SKILLS, json={"skill": skill, "level": level}, headers=headers)
    assert response.status_code in (200, 201), response.json()


# --- TC-F1-12 ------------------------------------------------------------------


def test_choose_a_role_and_read_it_back(client, student, roles, stale_calls):
    response = client.put(URL, json={"role_id": roles["Backend"]}, headers=student)

    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["role_id"] == roles["Backend"]
    assert body["role_name"] == "Backend"
    assert body["set_at"] is not None
    assert client.get(URL, headers=student).json() == body
    profile = client.get("/api/v1/profile", headers=student).json()
    assert profile["target_role_id"] == roles["Backend"]


def test_only_one_role_is_active_and_changing_it_marks_recommendations_stale(
    client, student, roles, stale_calls
):
    client.put(URL, json={"role_id": roles["Backend"]}, headers=student)
    assert len(stale_calls) == 1

    response = client.put(URL, json={"role_id": roles["Analyst"]}, headers=student)

    assert response.json()["role_id"] == roles["Analyst"]
    assert client.get(URL, headers=student).json()["role_id"] == roles["Analyst"]
    assert len(stale_calls) == 2
    assert stale_calls[0] == stale_calls[1]


def test_choosing_the_same_role_again_changes_nothing(client, student, roles, stale_calls):
    first = client.put(URL, json={"role_id": roles["Backend"]}, headers=student).json()
    second = client.put(URL, json={"role_id": roles["Backend"]}, headers=student).json()

    assert second["set_at"] == first["set_at"]
    assert len(stale_calls) == 1


def test_the_summary_counts_required_held_and_gap_skills(client, student, roles):
    """TC-F1-13: Python Intermediate and SQL Beginner against Python Advanced,
    SQL Intermediate and Docker Beginner leave exactly three gaps."""
    declare(client, student, "python", "intermediate")
    declare(client, student, "sql", "beginner")

    backend = client.put(URL, json={"role_id": roles["Backend"]}, headers=student).json()
    assert (backend["required"], backend["held"], backend["gap"]) == (3, 0, 3)

    analyst = client.put(URL, json={"role_id": roles["Analyst"]}, headers=student).json()
    assert (analyst["required"], analyst["held"], analyst["gap"]) == (1, 1, 0)


def test_the_summary_follows_later_skill_changes(client, student, roles):
    client.put(URL, json={"role_id": roles["Analyst"]}, headers=student)
    assert client.get(URL, headers=student).json()["gap"] == 1

    declare(client, student, "sql", "advanced")

    summary = client.get(URL, headers=student).json()
    assert (summary["held"], summary["gap"]) == (1, 0)


# --- Rejections ----------------------------------------------------------------


def test_an_unknown_role_is_rejected_and_the_current_one_kept(
    client, student, roles, stale_calls
):
    client.put(URL, json={"role_id": roles["Backend"]}, headers=student)

    response = client.put(URL, json={"role_id": 999_999}, headers=student)

    assert response.status_code == 422
    assert client.get(URL, headers=student).json()["role_id"] == roles["Backend"]
    assert len(stale_calls) == 1


def test_no_role_chosen_yet_is_a_404(client, student, roles):
    assert client.get(URL, headers=student).status_code == 404


def test_a_user_without_a_profile_gets_404(client, make_user, bearer, roles):
    headers = bearer(make_user())
    assert client.put(URL, json={"role_id": roles["Backend"]}, headers=headers).status_code == 404
    assert client.get(URL, headers=headers).status_code == 404


def test_the_role_id_is_required(client, student):
    assert client.put(URL, json={}, headers=student).status_code == 422


def test_only_students_may_choose_and_the_caller_must_be_signed_in(
    client, make_user, bearer, roles
):
    assert client.put(URL, json={"role_id": roles["Backend"]}).status_code == 401
    faculty = bearer(make_user("faculty_mentor"), "faculty_mentor")
    assert client.put(URL, json={"role_id": roles["Backend"]}, headers=faculty).status_code == 403


def test_students_cannot_touch_each_others_role(client, student, make_user, bearer, roles):
    other = bearer(make_user())
    client.post("/api/v1/profile", json={"name": "Ben"}, headers=other)
    client.put(URL, json={"role_id": roles["Backend"]}, headers=student)

    assert client.get(URL, headers=other).status_code == 404
