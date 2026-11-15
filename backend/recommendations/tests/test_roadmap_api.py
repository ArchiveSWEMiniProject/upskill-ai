"""RM-4: GET /api/v1/roadmap against real Postgres (see backend/conftest.py).

The skill vector comes from M1 (UP-11). These tests fix it, so they check M2's own
work: which approved resources are recommended for each gap skill, and in what order.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.database import get_session
from backend.gap.routes import vector_provider
from backend.main import app
from backend.shared.skill_vector import Level, SkillVector, SkillVectorEntry

URL = "/api/v1/roadmap"
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
            "VALUES ('Test Role', 'Role for roadmap tests') RETURNING role_id"
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


def add_resource(db_session, title, state, tags, level="beginner"):
    """Insert one catalogue resource with its skill tags; returns its item id."""
    item_id = db_session.execute(
        text(
            "INSERT INTO learning_item "
            "(title, description, item_type, level, duration, source_url, source, "
            "moderation_state) "
            "VALUES (:title, 'A test resource for recommendations', 'course', "
            "CAST(:level AS skill_level), '3 hours', :url, 'Example Academy', "
            "CAST(:state AS moderation_state)) RETURNING item_id"
        ),
        {
            "title": title,
            "level": level,
            "url": f"https://example.com/{title.lower().replace(' ', '-')}",
            "state": state,
        },
    ).scalar_one()
    for skill_id, coverage in tags:
        db_session.execute(
            text(
                "INSERT INTO learning_item_skill (item_id, skill_id, coverage_level) "
                "VALUES (:item, :skill, CAST(:coverage AS skill_level))"
            ),
            {"item": item_id, "skill": skill_id, "coverage": coverage},
        )
    return item_id


@pytest.fixture
def catalogue(db_session, role):
    """Approved, pending and inactive resources for the role's skills."""
    python = role["skills"]["Python"]
    sql = role["skills"]["SQL Basics"]
    add_resource(db_session, "Python basics", "approved", [(python, "beginner")])
    add_resource(
        db_session, "Python deeper", "approved", [(python, "intermediate")], level="intermediate"
    )
    add_resource(
        db_session, "Python expert", "approved", [(python, "advanced")], level="advanced"
    )
    add_resource(
        db_session, "Python pending", "pending", [(python, "intermediate")], level="intermediate"
    )
    add_resource(
        db_session, "Python retired", "inactive", [(python, "intermediate")], level="intermediate"
    )
    add_resource(db_session, "SQL intro", "approved", [(sql, "beginner")])
    add_resource(
        db_session, "SQL deep", "approved", [(sql, "intermediate")], level="intermediate"
    )
    add_resource(
        db_session, "Data bootcamp", "approved", [(python, "beginner"), (sql, "beginner")]
    )


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


def item_for(response, skill_name):
    return next(i for i in response.json()["items"] if i["skill_name"] == skill_name)


def titles(response, skill_name):
    return [r["title"] for r in item_for(response, skill_name)["resources"]]


def test_a_student_with_no_skills_gets_resources_lowest_level_first(
    client, db_session, student_headers, role, catalogue, set_vector
):
    choose_role(client, db_session, student_headers, role["id"])
    set_vector()

    response = client.get(URL, headers=student_headers)

    assert response.status_code == 200
    assert titles(response, "Python") == ["Python basics", "Data bootcamp", "Python deeper"]
    assert titles(response, "SQL Basics") == ["SQL intro", "Data bootcamp"]
    assert titles(response, "Docker") == []


def test_levels_the_student_already_holds_are_not_recommended_again(
    client, db_session, student_headers, role, catalogue, set_vector
):
    choose_role(client, db_session, student_headers, role["id"])
    set_vector((role["skills"]["Python"], "Python", Level.beginner))

    response = client.get(URL, headers=student_headers)

    assert response.status_code == 200
    assert titles(response, "Python") == ["Python deeper"]
    assert titles(response, "SQL Basics") == ["SQL intro", "Data bootcamp"]


def test_tc_f2_10_pending_and_inactive_resources_never_reach_the_student(
    client, db_session, student_headers, role, catalogue, set_vector
):
    choose_role(client, db_session, student_headers, role["id"])
    set_vector()

    response = client.get(URL, headers=student_headers)

    shown = [r["title"] for item in response.json()["items"] for r in item["resources"]]
    assert shown
    assert "Python pending" not in shown
    assert "Python retired" not in shown


def test_each_resource_carries_what_the_student_needs_to_act_on_it(
    client, db_session, student_headers, role, catalogue, set_vector
):
    choose_role(client, db_session, student_headers, role["id"])
    set_vector()

    response = client.get(URL, headers=student_headers)

    item = item_for(response, "Python")
    assert (item["rank"], item["required_level"], item["current_level"], item["weight"]) == (
        1,
        "intermediate",
        None,
        5,
    )
    first = item["resources"][0]
    assert first == {
        "item_id": first["item_id"],
        "title": "Python basics",
        "item_type": "course",
        "coverage_level": "beginner",
        "duration": "3 hours",
        "source": "Example Academy",
        "source_url": "https://example.com/python-basics",
    }


def test_no_profile_returns_404(client, make_user, bearer):
    response = client.get(URL, headers=bearer(make_user()))

    assert response.status_code == 404


def test_no_target_role_returns_409(client, student_headers):
    response = client.get(URL, headers=student_headers)

    assert response.status_code == 409


def test_login_is_required(client):
    assert client.get(URL).status_code == 401


def test_a_faculty_account_is_refused(client, make_user, bearer):
    headers = bearer(make_user("faculty_mentor"), "faculty_mentor")

    assert client.get(URL, headers=headers).status_code == 403
