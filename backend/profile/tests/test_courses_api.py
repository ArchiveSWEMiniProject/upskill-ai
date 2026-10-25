"""UP-3 course entries against real Postgres (see backend/conftest.py)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.database import get_session
from backend.main import app
from backend.profile.dependencies import DEV_AUTH_ENV
from backend.profile.models import ProfileItem

URL = "/api/v1/profile/courses"
DATA_STRUCTURES = {
    "course_name": "Data Structures",
    "course_code": "UE23CS251A",
    "grade": "A",
    "completion_term": "Sem 3",
}


@pytest.fixture
def client(db_session, monkeypatch):
    monkeypatch.setenv(DEV_AUTH_ENV, "1")
    app.dependency_overrides[get_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def student(client, make_user):
    headers = {"X-User-Id": str(make_user())}
    assert client.post("/api/v1/profile", json={"name": "Asha"}, headers=headers).status_code == 201
    return headers


def course_count(db_session) -> int:
    return db_session.scalar(
        select(func.count()).select_from(ProfileItem).where(ProfileItem.item_type == "course")
    )


# --- TC-F1-02, TC-F1-03 ------------------------------------------------------


def test_tc_f1_02_course_is_saved_and_listed(client, student):
    created = client.post(URL, json=DATA_STRUCTURES, headers=student)

    assert created.status_code == 201
    course = created.json()
    assert course == {"course_id": course["course_id"], **DATA_STRUCTURES}
    assert client.get(URL, headers=student).json() == [course]


def test_tc_f1_03_invalid_grade_is_rejected_naming_the_field(client, db_session, student):
    response = client.post(
        URL,
        json={"course_name": "DBMS", "grade": "Z", "completion_term": "Sem 4"},
        headers=student,
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert [e["loc"][-1] for e in errors] == ["grade"]
    assert "S, A, B, C, D, E, F" in errors[0]["msg"]
    assert course_count(db_session) == 0


# --- Grades (REQ-F1-36, SRS Appendix B) -------------------------------------


@pytest.mark.parametrize(
    ("given", "stored"), [("A", "A"), ("s", "S"), (" f ", "F"), ("85", "85"), ("085", "85"),
                          ("0", "0"), ("100", "100")],
)
def test_valid_grades_are_stored_normalised(client, student, given, stored):
    response = client.post(URL, json={**DATA_STRUCTURES, "grade": given}, headers=student)
    assert response.status_code == 201
    assert response.json()["grade"] == stored


@pytest.mark.parametrize("grade", ["Z", "G", "AB", "101", "-1", "8.5", "", "  "])
def test_invalid_grades_are_rejected(client, student, grade):
    response = client.post(URL, json={**DATA_STRUCTURES, "grade": grade}, headers=student)
    assert response.status_code == 422
    assert [e["loc"][-1] for e in response.json()["detail"]] == ["grade"]


# --- Mandatory fields and lengths (REQ-F1-35, SRS Appendix B) ---------------


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"course_name": None}, "course_name"),
        ({"course_name": "   "}, "course_name"),
        ({"course_name": "x" * 101}, "course_name"),
        ({"course_code": "x" * 16}, "course_code"),
        ({"grade": None}, "grade"),
        ({"completion_term": None}, "completion_term"),
        ({"completion_term": " "}, "completion_term"),
        ({"completion_term": "x" * 11}, "completion_term"),
        ({"credits": 4}, "credits"),
    ],
)
def test_invalid_course_is_rejected_naming_the_field(
    client, db_session, student, change, field
):
    payload = {**DATA_STRUCTURES, **change}
    payload = {k: v for k, v in payload.items() if v is not None}
    response = client.post(URL, json=payload, headers=student)

    assert response.status_code == 422
    assert [e["loc"][-1] for e in response.json()["detail"]] == [field]
    assert course_count(db_session) == 0


def test_course_code_is_optional_and_blank_means_none(client, student):
    without = {k: v for k, v in DATA_STRUCTURES.items() if k != "course_code"}
    assert client.post(URL, json=without, headers=student).json()["course_code"] is None
    blank = {**DATA_STRUCTURES, "course_code": "  "}
    assert client.post(URL, json=blank, headers=student).json()["course_code"] is None


# --- Edit and delete ----------------------------------------------------------


def test_edit_replaces_the_course(client, student):
    course_id = client.post(URL, json=DATA_STRUCTURES, headers=student).json()["course_id"]
    edited = {**DATA_STRUCTURES, "grade": "S", "completion_term": "Sem 4", "course_code": None}

    response = client.put(f"{URL}/{course_id}", json=edited, headers=student)

    assert response.status_code == 200
    assert response.json() == {"course_id": course_id, **edited}
    assert client.get(URL, headers=student).json() == [response.json()]


def test_invalid_edit_leaves_the_course_unchanged(client, student):
    course = client.post(URL, json=DATA_STRUCTURES, headers=student).json()
    response = client.put(
        f"{URL}/{course['course_id']}", json={**DATA_STRUCTURES, "grade": "Z"}, headers=student
    )
    assert response.status_code == 422
    assert client.get(URL, headers=student).json() == [course]


def test_delete_removes_the_course(client, db_session, student):
    course_id = client.post(URL, json=DATA_STRUCTURES, headers=student).json()["course_id"]

    assert client.delete(f"{URL}/{course_id}", headers=student).status_code == 204
    assert client.get(URL, headers=student).json() == []
    assert client.delete(f"{URL}/{course_id}", headers=student).status_code == 404


def test_courses_are_listed_oldest_first(client, student):
    for name in ["First", "Second", "Third"]:
        client.post(URL, json={**DATA_STRUCTURES, "course_name": name}, headers=student)
    assert [c["course_name"] for c in client.get(URL, headers=student).json()] == [
        "First", "Second", "Third",
    ]


# --- Ownership (REQ-F1-39) -----------------------------------------------------


def test_another_students_course_behaves_as_missing(client, make_user, student):
    course = client.post(URL, json=DATA_STRUCTURES, headers=student).json()
    other = {"X-User-Id": str(make_user())}
    client.post("/api/v1/profile", json={"name": "Ravi"}, headers=other)

    assert client.get(URL, headers=other).json() == []
    path = f"{URL}/{course['course_id']}"
    put = client.put(path, json={**DATA_STRUCTURES, "grade": "F"}, headers=other)
    assert put.status_code == 404
    assert put.json() == {"detail": "Entry not found"}
    assert client.delete(path, headers=other).status_code == 404
    assert client.get(URL, headers=student).json() == [course]


def test_unknown_course_id_returns_404(client, student):
    assert client.put(f"{URL}/999999", json=DATA_STRUCTURES, headers=student).status_code == 404


def test_without_a_profile_returns_404(client, make_user):
    headers = {"X-User-Id": str(make_user())}
    assert client.get(URL, headers=headers).status_code == 404
    response = client.post(URL, json=DATA_STRUCTURES, headers=headers)
    assert response.status_code == 404
    assert response.json() == {"detail": "Profile not found"}


def test_requires_authentication(client):
    assert client.get(URL).status_code == 401
    assert client.post(URL, json=DATA_STRUCTURES).status_code == 401
