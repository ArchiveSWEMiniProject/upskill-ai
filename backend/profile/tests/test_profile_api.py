"""UP-2 against real Postgres (see backend/conftest.py)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.database import get_session
from backend.main import app
from backend.profile.dependencies import DEV_AUTH_ENV
from backend.profile.exceptions import ProfileAlreadyExistsError
from backend.profile.models import Student
from backend.profile.repository import StudentRepository

VALID = {"name": "Test Student", "education_level": "UG"}


@pytest.fixture
def client(db_session, monkeypatch):
    monkeypatch.setenv(DEV_AUTH_ENV, "1")
    app.dependency_overrides[get_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def as_user(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def profiles_for(db_session, user_id: int) -> int:
    return db_session.scalar(
        select(func.count()).select_from(Student).where(Student.user_id == user_id)
    )


# --- TC-F1-01 --------------------------------------------------------------


def test_tc_f1_01_student_creates_exactly_one_profile_linked_to_account(
    client, db_session, make_user
):
    user = make_user()

    created = client.post("/api/v1/profile", json=VALID, headers=as_user(user))
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Test Student"
    assert body["education_level"] == "UG"
    assert body["target_role_id"] is None
    assert db_session.get(Student, body["student_id"]).user_id == user

    again = client.post("/api/v1/profile", json=VALID, headers=as_user(user))
    assert again.status_code == 409
    assert again.json() == {"detail": "Profile already exists"}
    assert profiles_for(db_session, user) == 1


def test_student_views_own_profile(client, make_user):
    user = make_user()
    client.post("/api/v1/profile", json=VALID, headers=as_user(user))

    response = client.get("/api/v1/profile", headers=as_user(user))

    assert response.status_code == 200
    assert response.json()["name"] == "Test Student"


def test_view_before_creating_returns_404(client, make_user):
    response = client.get("/api/v1/profile", headers=as_user(make_user()))
    assert response.status_code == 404
    assert response.json() == {"detail": "Profile not found"}


def test_each_account_sees_only_its_own_profile(client, make_user):
    alice, bob = make_user(), make_user()
    client.post("/api/v1/profile", json={"name": "Alice"}, headers=as_user(alice))
    client.post("/api/v1/profile", json={"name": "Bob"}, headers=as_user(bob))

    assert client.get("/api/v1/profile", headers=as_user(alice)).json()["name"] == "Alice"
    assert client.get("/api/v1/profile", headers=as_user(bob)).json()["name"] == "Bob"


def test_name_is_trimmed_and_education_level_optional(client, make_user):
    response = client.post(
        "/api/v1/profile", json={"name": "  Asha  "}, headers=as_user(make_user())
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Asha"
    assert response.json()["education_level"] is None


# --- Validation (REQ-F1-35) ------------------------------------------------


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"education_level": "UG"}, "name"),
        ({"name": ""}, "name"),
        ({"name": "   "}, "name"),
        ({"name": "x" * 61}, "name"),
        ({"name": "Asha", "education_level": "x" * 31}, "education_level"),
        ({"name": "Asha", "student_id": 7}, "student_id"),
    ],
)
def test_invalid_profile_is_rejected_naming_the_field(client, make_user, payload, field):
    user = make_user()
    response = client.post("/api/v1/profile", json=payload, headers=as_user(user))
    assert response.status_code == 422
    assert [error["loc"][-1] for error in response.json()["detail"]] == [field]


def test_rejected_profile_writes_nothing(client, db_session, make_user):
    user = make_user()
    client.post("/api/v1/profile", json={"name": ""}, headers=as_user(user))
    assert profiles_for(db_session, user) == 0


# --- Authentication stand-in -----------------------------------------------


def test_request_without_identity_is_unauthenticated(client):
    for method in (client.get, client.post):
        kwargs = {"json": VALID} if method is client.post else {}
        response = method("/api/v1/profile", **kwargs)
        assert response.status_code == 401


def test_identity_header_is_ignored_unless_dev_auth_is_enabled(client, make_user, monkeypatch):
    monkeypatch.delenv(DEV_AUTH_ENV)
    response = client.get("/api/v1/profile", headers=as_user(make_user()))
    assert response.status_code == 401


# --- Database guard ---------------------------------------------------------


def test_database_rejects_a_second_profile_even_without_the_service_check(
    db_session, make_user
):
    """Two concurrent creates can both pass the service's existence check; the
    unique constraint on student.user_id must still stop the second one."""
    user = make_user()
    students = StudentRepository(db_session)
    students.add(Student(user_id=user, name="First"))

    with pytest.raises(ProfileAlreadyExistsError):
        students.add(Student(user_id=user, name="Second"))
    assert profiles_for(db_session, user) == 1


def test_other_integrity_errors_are_not_reported_as_duplicates(db_session):
    with pytest.raises(IntegrityError):
        StudentRepository(db_session).add(Student(user_id=999_999, name="No account"))
