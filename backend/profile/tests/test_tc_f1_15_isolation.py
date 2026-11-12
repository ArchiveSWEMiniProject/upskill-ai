"""TC-F1-15: a student cannot read or change another student's profile, and the
decision is M4's authorize(), not M1 role logic (NFR-SEC-07, REQ-F1-39). Runs
against real Postgres (see backend/conftest.py).

Two real accounts are registered and logged in through the API. M1's routes
never take a student id, because the profile is always the caller's own. The
only ids in M1 URLs are entry and resume ids, so those are what student B
tries with student A's ids. Faculty see a student only through M4's mentee
view, and only when the student is assigned to them.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.database import get_session
from backend.main import app
from backend.profile import dependencies

API = "/api/v1"
PROFILE = f"{API}/profile"
COURSE = {
    "course_name": "Data Structures",
    "course_code": "UE23CS251A",
    "grade": "A",
    "completion_term": "Sem 3",
}
PROJECT = {
    "title": "Study goals API",
    "description": "A REST API for tracking study goals, built with FastAPI and Postgres.",
    "repository_url": "https://github.com/asha/study-goals",
}


@pytest.fixture
def client(db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("RESUME_STORAGE_DIR", str(tmp_path))
    app.dependency_overrides[get_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def account(client, email: str, name: str) -> dict[str, str]:
    """Register, log in and create a profile; returns the auth headers."""
    credentials = {"email": email, "password": "Isolation2026"}
    assert client.post(f"{API}/auth/register", json=credentials).status_code == 201
    token = client.post(f"{API}/auth/login", json=credentials).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post(PROFILE, json={"name": name}, headers=headers).status_code == 201
    return headers


@pytest.fixture
def python_skill(db_session) -> int:
    return db_session.execute(
        text(
            "INSERT INTO skill (skill_name, category) VALUES ('Python', 'Test') "
            "RETURNING skill_id"
        )
    ).scalar_one()


@pytest.fixture
def asha(client, python_skill):
    """Student A with a course, a project and a skill."""
    headers = account(client, "asha@pes.edu", "Asha")
    course = client.post(f"{PROFILE}/courses", json=COURSE, headers=headers).json()
    project = client.post(f"{PROFILE}/projects", json=PROJECT, headers=headers).json()
    declared = client.post(
        f"{PROFILE}/skills", json={"skill": "Python", "level": "advanced"}, headers=headers
    )
    assert declared.status_code == 201
    return {"headers": headers, "course": course, "project": project}


def snapshot(client, headers) -> dict:
    return {
        "profile": client.get(PROFILE, headers=headers).json(),
        "courses": client.get(f"{PROFILE}/courses", headers=headers).json(),
        "projects": client.get(f"{PROFILE}/projects", headers=headers).json(),
        "vector": client.get(f"{PROFILE}/skill-vector", headers=headers).json(),
        "resumes": client.get(f"{PROFILE}/resume", headers=headers).json(),
    }


def test_tc_f1_15_student_b_cannot_read_or_change_student_a(client, asha):
    before = snapshot(client, asha["headers"])
    ravi = account(client, "ravi@pes.edu", "Ravi")

    # B's reads return B's own (empty) data, never A's.
    seen = snapshot(client, ravi)
    assert seen["profile"]["name"] == "Ravi"
    assert seen["profile"]["student_id"] != before["profile"]["student_id"]
    assert seen["courses"] == seen["projects"] == seen["resumes"] == []
    assert seen["vector"] == {"entries": []}

    # A's entry ids behave as missing for B, for every verb.
    course = f"{PROFILE}/courses/{asha['course']['course_id']}"
    project = f"{PROFILE}/projects/{asha['project']['project_id']}"
    assert client.put(course, json={**COURSE, "grade": "F"}, headers=ravi).status_code == 404
    assert client.delete(course, headers=ravi).status_code == 404
    assert client.put(project, json=PROJECT, headers=ravi).status_code == 404
    assert client.delete(project, headers=ravi).status_code == 404

    # Nothing of A's changed.
    assert snapshot(client, asha["headers"]) == before


def test_m1_routes_defer_to_authorize(client, asha, monkeypatch):
    """If M4's authorize() says no, every M1 route refuses, even for the owner:
    M1 has no role check of its own to fall back on."""
    calls = []

    def deny(user, action, resource=None, **_):
        calls.append((user.user_id, action, resource))
        return False

    monkeypatch.setattr(dependencies, "authorize", deny)
    headers = asha["headers"]
    for path in ["", "/courses", "/projects", "/skill-vector", "/resume"]:
        assert client.get(f"{PROFILE}{path}", headers=headers).status_code == 403, path
    assert client.post(f"{PROFILE}/courses", json=COURSE, headers=headers).status_code == 403
    assert calls and all(action == "student:update" for _, action, _ in calls)
    # The resource is always the caller's own account, never a client-supplied id.
    assert all(resource == {"user_id": user_id} for user_id, _, resource in calls)


def test_faculty_cannot_use_student_routes(client, asha, make_user, bearer):
    faculty = bearer(make_user("faculty_mentor"), role="faculty_mentor")
    assert client.get(PROFILE, headers=faculty).status_code == 403
    assert client.get(f"{PROFILE}/skill-vector", headers=faculty).status_code == 403


def test_faculty_see_a_student_only_when_assigned(client, db_session, asha, make_user, bearer):
    student_id = client.get(PROFILE, headers=asha["headers"]).json()["student_id"]
    mentor_id = make_user("faculty_mentor")
    mentor = bearer(mentor_id, role="faculty_mentor")
    url = f"{API}/faculty/mentees/{student_id}"

    assert client.get(url, headers=mentor).status_code == 403

    db_session.execute(
        text("INSERT INTO mentor_assignment (mentor_id, student_id) VALUES (:m, :s)"),
        {"m": mentor_id, "s": student_id},
    )
    response = client.get(url, headers=mentor)
    assert response.status_code == 200
    assert response.json()["name"] == "Asha"

    # Another mentor still cannot.
    other = bearer(make_user("faculty_mentor"), role="faculty_mentor")
    assert client.get(url, headers=other).status_code == 403
