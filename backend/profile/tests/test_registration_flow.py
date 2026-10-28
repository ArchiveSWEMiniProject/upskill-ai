"""UP-1 end to end against real Postgres: register, log in, land on an empty
profile, create it (UP-2), plus the registration rules and fixes from review."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.auth.models import UserAccount
from backend.database import get_session
from backend.main import app
from backend.profile.models import Student

REGISTER, LOGIN = "/api/v1/auth/register", "/api/v1/auth/login"
ASHA = {"email": "asha@pes.edu", "password": "Upskill2026"}


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def login(client, email: str, password: str) -> dict:
    response = client.post(LOGIN, json={"email": email, "password": password})
    assert response.status_code == 200, response.json()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def accounts(db_session) -> int:
    return db_session.scalar(select(func.count()).select_from(UserAccount))


def test_student_registers_logs_in_and_lands_on_an_empty_profile(client, db_session):
    registered = client.post(REGISTER, json=ASHA)
    assert registered.status_code == 201
    assert registered.json()["role"] == "student"

    headers = login(client, ASHA["email"], ASHA["password"])
    assert client.get("/api/v1/auth/me", headers=headers).json()["email"] == "asha@pes.edu"

    # Registration creates the account only; the profile is the student's to create.
    assert client.get("/api/v1/profile", headers=headers).status_code == 404
    assert db_session.scalar(select(func.count()).select_from(Student)) == 0

    created = client.post("/api/v1/profile", json={"name": "Asha"}, headers=headers)
    assert created.status_code == 201
    assert client.get("/api/v1/profile", headers=headers).json()["name"] == "Asha"


def test_email_is_normalised_for_registration_and_login(client):
    client.post(REGISTER, json={**ASHA, "email": "  Asha@PES.edu "})
    login(client, "ASHA@pes.edu", ASHA["password"])
    assert client.post(REGISTER, json=ASHA).status_code == 400  # same address


# --- Role escalation (review of #76) -------------------------------------------


@pytest.mark.parametrize("role", ["administrator", "faculty_mentor"])
def test_self_registration_cannot_create_privileged_accounts(client, db_session, role):
    response = client.post(REGISTER, json={**ASHA, "role": role})
    assert response.status_code == 403
    assert response.json() == {"detail": "Self-registration creates student accounts only"}
    assert accounts(db_session) == 0


def test_asking_for_the_student_role_explicitly_is_fine(client):
    assert client.post(REGISTER, json={**ASHA, "role": "student"}).status_code == 201


# --- Validation (UP-1 acceptance criteria) -------------------------------------


@pytest.mark.parametrize(
    "email", ["asha", "asha@pes", "asha@pes.e", "as ha@pes.edu", "@pes.edu", "asha@-pes.edu"]
)
def test_malformed_email_is_rejected(client, db_session, email):
    response = client.post(REGISTER, json={**ASHA, "email": email})
    assert response.status_code == 422
    assert [e["loc"][-1] for e in response.json()["detail"]] == ["email"]
    assert accounts(db_session) == 0


@pytest.mark.parametrize(
    "password", ["short1", "onlyletters", "1234567890", "a1" * 65]
)
def test_weak_or_oversized_password_is_rejected(client, db_session, password):
    response = client.post(REGISTER, json={**ASHA, "password": password})
    assert response.status_code == 422
    assert [e["loc"][-1] for e in response.json()["detail"]] == ["password"]
    assert accounts(db_session) == 0


def test_duplicate_email_is_rejected(client, db_session):
    client.post(REGISTER, json=ASHA)
    response = client.post(REGISTER, json={**ASHA, "password": "Different2026"})
    assert response.status_code == 400
    assert accounts(db_session) == 1


def test_password_is_stored_only_as_an_argon2id_hash(client, db_session):
    client.post(REGISTER, json=ASHA)
    stored = db_session.scalar(select(UserAccount.password_hash))
    assert stored.startswith("$argon2id$")
    assert ASHA["password"] not in stored


# --- Login errors do not reveal which field was wrong ---------------------------


def test_unknown_email_and_wrong_password_get_the_same_error(client):
    client.post(REGISTER, json=ASHA)
    unknown = client.post(LOGIN, json={"email": "nobody@pes.edu", "password": ASHA["password"]})
    wrong = client.post(LOGIN, json={"email": ASHA["email"], "password": "Wrong2026pass"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json() == {"detail": "Invalid email or password"}


@pytest.mark.parametrize(
    "credentials",
    [
        {"email": "", "password": ASHA["password"]},
        {"email": ASHA["email"], "password": ""},
        {"email": "a" * 300 + "@pes.edu", "password": ASHA["password"]},
        {"email": "not-an-email", "password": "x"},
    ],
)
def test_blank_or_malformed_credentials_get_the_same_generic_error(client, credentials):
    client.post(REGISTER, json=ASHA)
    response = client.post(LOGIN, json=credentials)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


# --- Signing secret (review of #76) -----------------------------------------------


def test_api_refuses_to_start_without_a_signing_secret(monkeypatch):
    monkeypatch.delenv("JWT_SECRET")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        with TestClient(app):
            pass


def test_concurrent_duplicate_registration_is_still_rejected(client, db_session, monkeypatch):
    """Two sign-ups with one email can both pass the existence check; the
    unique constraint must still stop the second with the same 400."""
    from sqlalchemy.orm import Query

    client.post(REGISTER, json=ASHA)
    monkeypatch.setattr(Query, "first", lambda self: None)  # the check misses, as in a race
    response = client.post(REGISTER, json=ASHA)
    assert response.status_code == 400
    assert response.json() == {"detail": "A user with this email already exists"}
    monkeypatch.undo()
    assert accounts(db_session) == 1


def test_deactivated_account_cannot_log_in(client, db_session):
    client.post(REGISTER, json=ASHA)
    db_session.execute(
        UserAccount.__table__.update().values(is_active=False)
    )
    response = client.post(LOGIN, json=ASHA)
    assert response.status_code == 403
