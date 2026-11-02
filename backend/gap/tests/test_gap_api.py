"""RM-3: GET /api/v1/roadmap/gap against real Postgres (see backend/conftest.py).

The skill vector comes from M1 (UP-11). These tests fix it, so they check M2's own
work: the target role, its requirements, the ranking and the response shape.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.database import get_session
from backend.gap.routes import vector_provider
from backend.main import app
from backend.shared.skill_vector import Level, SkillVector, SkillVectorEntry

URL = "/api/v1/roadmap/gap"
REQUIREMENTS = [
    ("Python", "intermediate", 5),
    ("SQL Basics", "beginner", 3),
    ("Docker", "beginner", 1),
]


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def set_vector(client):
    """Fix the skill vector the endpoint sees: set_vector((skill_id, name, level), ...)."""

    def _set(*entries):
        vector = SkillVector(
            tuple(
                SkillVectorEntry(skill_id, name, level, confidence=0.8, source="manual")
                for skill_id, name, level in entries
            )
        )
        app.dependency_overrides[vector_provider] = lambda: (lambda student_id: vector)

    return _set


@pytest.fixture
def role(db_session):
    """A career role with three requirements; returns its id and the skill ids."""
    skills = {}
    for name, _, _ in REQUIREMENTS:
        skills[name] = db_session.execute(
            text("INSERT INTO skill (skill_name, category) VALUES (:n, 'Test') RETURNING skill_id"),
            {"n": name},
        ).scalar_one()
    role_id = db_session.execute(
        text(
            "INSERT INTO career_role (role_name, description) "
            "VALUES ('Test Role', 'Role for gap tests') RETURNING role_id"
        )
    ).scalar_one()
    for name, level, weight in REQUIREMENTS:
        db_session.execute(
            text(
                "INSERT INTO role_skill_requirement (role_id, skill_id, required_level, weight) "
                "VALUES (:r, :s, CAST(:l AS skill_level), :w)"
            ),
            {"r": role_id, "s": skills[name], "l": level, "w": weight},
        )
    return {"id": role_id, "skills": skills}


@pytest.fixture
def student_headers(client, make_user, bearer):
    headers = bearer(make_user())
    assert client.post("/api/v1/profile", json={"name": "Asha"}, headers=headers).status_code == 201
    return headers


def choose_role(client, db_session, headers, role_id):
    student_id = client.get("/api/v1/profile", headers=headers).json()["student_id"]
    db_session.execute(
        text("UPDATE student SET target_role_id = :r WHERE student_id = :s"),
        {"r": role_id, "s": student_id},
    )


def test_gap_lists_missing_and_below_level_skills_most_important_first(
    client, db_session, student_headers, role, set_vector
):
    skills = role["skills"]
    choose_role(client, db_session, student_headers, role["id"])
    set_vector((skills["Python"], "Python", Level.beginner))

    response = client.get(URL, headers=student_headers)

    assert response.status_code == 200
    assert response.json() == {
        "role_id": role["id"],
        "role_name": "Test Role",
        "items": [
            {
                "rank": 1, "skill_id": skills["Python"], "skill_name": "Python",
                "required_level": "intermediate", "current_level": "beginner", "weight": 5,
            },
            {
                "rank": 2, "skill_id": skills["SQL Basics"], "skill_name": "SQL Basics",
                "required_level": "beginner", "current_level": None, "weight": 3,
            },
            {
                "rank": 3, "skill_id": skills["Docker"], "skill_name": "Docker",
                "required_level": "beginner", "current_level": None, "weight": 1,
            },
        ],
    }


def test_gap_is_empty_when_the_student_meets_every_requirement(
    client, db_session, student_headers, role, set_vector
):
    skills = role["skills"]
    choose_role(client, db_session, student_headers, role["id"])
    set_vector(
        (skills["Python"], "Python", Level.advanced),
        (skills["SQL Basics"], "SQL Basics", Level.beginner),
        (skills["Docker"], "Docker", Level.intermediate),
    )

    response = client.get(URL, headers=student_headers)

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_no_profile_returns_404(client, make_user, bearer):
    response = client.get(URL, headers=bearer(make_user()))

    assert response.status_code == 404
    assert response.json() == {"detail": "Create your profile before viewing your skill gap"}


def test_no_target_role_returns_409(client, student_headers):
    response = client.get(URL, headers=student_headers)

    assert response.status_code == 409
    assert response.json() == {"detail": "Choose a target role to see your skill gap"}


def test_login_is_required(client):
    assert client.get(URL).status_code == 401
