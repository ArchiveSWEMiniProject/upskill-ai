"""PR-2: TC-F3-03/04, inclusive bounds, ownership and completion bypass."""

import pytest
from sqlalchemy import text


@pytest.fixture
def enrolled(client, student, resource, bearer):
    headers = bearer(student[0])
    record = client.post("/api/v1/progress/enrol", json={"resource_id": resource()},
                         headers=headers).json()
    return f'/api/v1/progress/{record["progress_id"]}', headers


@pytest.mark.parametrize("value", [0, 1, 60, 99, 100])
def test_tc_f3_03_valid_percentage_is_persisted(client, enrolled, db_session, value):
    url, headers = enrolled
    response = client.patch(url, json={"completion_percentage": value}, headers=headers)
    assert response.status_code == 200
    expected_status = "enrolled" if value == 0 else "in-progress"
    assert response.json()["completion_percentage"] == value
    assert response.json()["status"] == expected_status
    row = db_session.execute(text("SELECT status, completion_percentage FROM progress")).one()
    assert tuple(row) == (expected_status, value)


@pytest.mark.parametrize("value", [-1, 101, 140, None, "60", True, 60.5])
def test_tc_f3_04_rejected_percentage_leaves_saved_value_unchanged(
    client, enrolled, db_session, value
):
    url, headers = enrolled
    client.patch(url, json={"completion_percentage": 60}, headers=headers)
    response = client.patch(url, json={"completion_percentage": value}, headers=headers)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "completion_percentage"
    row = db_session.execute(text("SELECT status, completion_percentage FROM progress")).one()
    assert tuple(row) == ("in-progress", 60)


def test_cannot_supply_owner_or_set_completed_state(client, enrolled):
    url, headers = enrolled
    for extra in [{"student_id": 99}, {"status": "completed"}]:
        assert client.patch(url, json={"completion_percentage": 100, **extra},
                            headers=headers).status_code == 422


def test_missing_update_value_rejected(client, enrolled):
    url, headers = enrolled
    assert client.patch(url, json={}, headers=headers).status_code == 422


def test_cannot_update_someone_elses_progress(client, enrolled, make_user, bearer):
    url, _ = enrolled
    other = make_user()
    headers = bearer(other)
    client.post("/api/v1/profile", json={"name": "Other Student"}, headers=headers)
    assert client.patch(url, json={"completion_percentage": 60}, headers=headers).status_code == 404


def test_missing_progress_is_not_an_enrolment(client, student, bearer, db_session):
    response = client.patch("/api/v1/progress/999999", json={"completion_percentage": 60},
                            headers=bearer(student[0]))
    assert response.status_code == 404
    assert db_session.execute(text("SELECT count(*) FROM progress")).scalar_one() == 0


def test_completed_progress_cannot_be_reopened(client, enrolled, db_session):
    url, headers = enrolled
    db_session.execute(text("UPDATE progress SET status='completed', completion_percentage=100"))
    response = client.patch(url, json={"completion_percentage": 60}, headers=headers)
    assert response.status_code == 409
    percentage = db_session.execute(text("SELECT completion_percentage FROM progress")).scalar_one()
    assert percentage == 100


@pytest.mark.parametrize("role", ["faculty_mentor", "administrator"])
def test_nonstudent_cannot_update(client, enrolled, make_user, bearer, role):
    url, _ = enrolled
    assert client.patch(url, json={"completion_percentage": 60},
                        headers=bearer(make_user(role), role)).status_code == 403


def test_update_requires_authentication(client, enrolled):
    assert client.patch(enrolled[0], json={"completion_percentage": 60}).status_code == 401
