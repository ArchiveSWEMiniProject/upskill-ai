"""PR-1: TC-F3-01/02 and authenticated ownership on migrated Postgres."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.progress.repository import ProgressRepository

URL = "/api/v1/progress/enrol"


def test_tc_f3_01_enrolment_starts_at_zero(client, student, resource, bearer, db_session):
    user, sid = student
    rid = resource()
    response = client.post(URL, json={"resource_id": rid}, headers=bearer(user))
    assert response.status_code == 201
    assert response.json() == {
        "progress_id": response.json()["progress_id"], "resource_id": rid,
        "status": "enrolled", "completion_percentage": 0,
    }
    row = db_session.execute(text("SELECT * FROM progress")).one()
    assert row.student_id == sid and row.resource_id == rid


def test_tc_f3_02_invalid_resource_creates_nothing(client, student, bearer, db_session):
    response = client.post(URL, json={"resource_id": 999999}, headers=bearer(student[0]))
    assert response.status_code == 404
    assert "resource" in response.json()["detail"].lower()
    assert db_session.execute(text("SELECT count(*) FROM progress")).scalar_one() == 0


@pytest.mark.parametrize("moderation", ["pending", "inactive"])
def test_nonapproved_resource_cannot_be_enrolled(client, student, resource, bearer, moderation):
    response = client.post(URL, json={"resource_id": resource(moderation)},
                           headers=bearer(student[0]))
    assert response.status_code == 404


def test_retry_returns_existing_progress_without_resetting_it(
    client, student, resource, bearer, db_session
):
    rid = resource()
    headers = bearer(student[0])
    first = client.post(URL, json={"resource_id": rid}, headers=headers).json()
    db_session.execute(text(
        "UPDATE progress SET status='in-progress', completion_percentage=60"
    ))
    again = client.post(URL, json={"resource_id": rid}, headers=headers)
    assert again.status_code == 201
    assert again.json()["progress_id"] == first["progress_id"]
    assert again.json()["completion_percentage"] == 60
    assert db_session.execute(text("SELECT count(*) FROM progress")).scalar_one() == 1


@pytest.mark.parametrize("payload", [
    {}, {"resource_id": 0}, {"resource_id": -1}, {"resource_id": "12"},
    {"resource_id": True}, {"resource_id": 1, "student_id": 99},
])
def test_invalid_or_spoofed_enrolment_is_rejected(client, student, bearer, payload):
    assert client.post(URL, json=payload, headers=bearer(student[0])).status_code == 422


def test_token_required_not_placeholder_header(client):
    assert client.post(URL, json={"resource_id": 1},
                       headers={"X-Student-Id": "1"}).status_code == 401


@pytest.mark.parametrize("role", ["faculty_mentor", "administrator"])
def test_only_students_can_enrol(client, make_user, resource, bearer, role):
    assert client.post(URL, json={"resource_id": resource()},
                       headers=bearer(make_user(role), role)).status_code == 403


def test_profile_required(client, make_user, resource, bearer):
    assert client.post(URL, json={"resource_id": resource()},
                       headers=bearer(make_user())).status_code == 404


def test_two_students_have_independent_records(client, student, resource, make_user, bearer):
    other = make_user()
    client.post("/api/v1/profile", json={"name": "Other Student"}, headers=bearer(other))
    rid = resource()
    a = client.post(URL, json={"resource_id": rid}, headers=bearer(student[0])).json()
    b = client.post(URL, json={"resource_id": rid}, headers=bearer(other)).json()
    assert a["progress_id"] != b["progress_id"]


def test_database_enforces_progress_bounds_and_state(student, resource, db_session):
    record = ProgressRepository(db_session).enrol(student[1], resource())
    for assignment in ["completion_percentage=101", "completion_percentage=-1", "status='other'"]:
        with pytest.raises(IntegrityError), db_session.begin_nested():
            db_session.execute(text(f"UPDATE progress SET {assignment}"))
    assert record.completion_percentage == 0
