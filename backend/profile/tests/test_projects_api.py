"""UP-4 project entries against real Postgres (see backend/conftest.py)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.database import get_session
from backend.main import app
from backend.profile.models import ProfileItem

URL = "/api/v1/profile/projects"
PROJECT = {
    "title": "Test Project",
    "description": "A REST API for tracking study goals, built with FastAPI and Postgres.",
    "repository_url": "https://github.com/asha/study-goals",
}


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def student(client, make_user, bearer):
    headers = bearer(make_user())
    assert client.post("/api/v1/profile", json={"name": "Asha"}, headers=headers).status_code == 201
    return headers


def project_count(db_session) -> int:
    return db_session.scalar(
        select(func.count()).select_from(ProfileItem).where(ProfileItem.item_type == "project")
    )


def test_project_is_saved_and_listed(client, student):
    created = client.post(URL, json=PROJECT, headers=student)

    assert created.status_code == 201
    project = created.json()
    assert project == {"project_id": project["project_id"], **PROJECT}
    assert client.get(URL, headers=student).json() == [project]


# --- TC-F1-04, REQ-F1-37 ------------------------------------------------------


def test_tc_f1_04_over_length_description_is_rejected_with_its_count(
    client, db_session, student
):
    response = client.post(
        URL, json={"title": "Test Project", "description": "x" * 2050}, headers=student
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert [e["loc"][-1] for e in errors] == ["description"]
    assert "2050 characters" in errors[0]["msg"]
    assert "2000" in errors[0]["msg"]
    assert project_count(db_session) == 0


def test_description_of_exactly_2000_characters_is_accepted(client, student):
    response = client.post(URL, json={**PROJECT, "description": "x" * 2000}, headers=student)
    assert response.status_code == 201


# --- Repository URL (REQ-F1-03) -----------------------------------------------


def test_repository_url_is_optional(client, student):
    without = {k: v for k, v in PROJECT.items() if k != "repository_url"}
    assert client.post(URL, json=without, headers=student).json()["repository_url"] is None
    blank = {**PROJECT, "repository_url": "   "}
    assert client.post(URL, json=blank, headers=student).json()["repository_url"] is None


@pytest.mark.parametrize(
    "url",
    ["github.com/asha/x", "ftp://example.com/x", "https://", "not a url", "javascript:alert(1)",
     "https://github.com/" + "a" * 240],
)
def test_invalid_repository_url_is_rejected(client, db_session, student, url):
    response = client.post(URL, json={**PROJECT, "repository_url": url}, headers=student)
    assert response.status_code == 422
    assert [e["loc"][-1] for e in response.json()["detail"]] == ["repository_url"]
    assert project_count(db_session) == 0


# --- Mandatory fields (REQ-F1-35) ---------------------------------------------


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"title": None}, "title"),
        ({"title": "  "}, "title"),
        ({"title": "x" * 101}, "title"),
        ({"description": None}, "description"),
        ({"description": "   "}, "description"),
        ({"stars": 5}, "stars"),
    ],
)
def test_invalid_project_is_rejected_naming_the_field(
    client, db_session, student, change, field
):
    payload = {k: v for k, v in {**PROJECT, **change}.items() if v is not None}
    response = client.post(URL, json=payload, headers=student)
    assert response.status_code == 422
    assert [e["loc"][-1] for e in response.json()["detail"]] == [field]
    assert project_count(db_session) == 0


# --- Edit, delete, ownership ----------------------------------------------------


def test_edit_and_delete(client, student):
    project_id = client.post(URL, json=PROJECT, headers=student).json()["project_id"]
    edited = {**PROJECT, "title": "Study Goals API", "repository_url": None}

    response = client.put(f"{URL}/{project_id}", json=edited, headers=student)
    assert response.status_code == 200
    assert response.json() == {"project_id": project_id, **edited}

    assert client.delete(f"{URL}/{project_id}", headers=student).status_code == 204
    assert client.get(URL, headers=student).json() == []


def test_another_students_project_behaves_as_missing(client, make_user, bearer, student):
    project = client.post(URL, json=PROJECT, headers=student).json()
    other = bearer(make_user())
    client.post("/api/v1/profile", json={"name": "Ravi"}, headers=other)

    path = f"{URL}/{project['project_id']}"
    assert client.get(URL, headers=other).json() == []
    assert client.put(path, json=PROJECT, headers=other).status_code == 404
    assert client.delete(path, headers=other).status_code == 404
    assert client.get(URL, headers=student).json() == [project]


def test_courses_and_projects_do_not_mix(client, student):
    """Both live in profile_item; a course id is not a project id."""
    course = client.post(
        "/api/v1/profile/courses",
        json={"course_name": "DBMS", "grade": "A", "completion_term": "Sem 4"},
        headers=student,
    ).json()

    assert client.get(URL, headers=student).json() == []
    assert client.delete(f"{URL}/{course['course_id']}", headers=student).status_code == 404
    assert len(client.get("/api/v1/profile/courses", headers=student).json()) == 1


def test_without_a_profile_returns_404(client, make_user, bearer):
    headers = bearer(make_user())
    assert client.post(URL, json=PROJECT, headers=headers).status_code == 404


def test_requires_authentication(client):
    assert client.get(URL).status_code == 401
