"""PR-3 draft: the real default blocks completion; injected policies test the boundary.

These tests do not establish catalogue policy or PR-4 evidence integration.
"""

import pytest
from sqlalchemy import text

from backend.main import app
from backend.progress.completion import get_completion_policy


@pytest.fixture
def enrolled(client, student, resource, bearer):
    headers = bearer(student[0])
    record = client.post("/api/v1/progress/enrol", json={"resource_id": resource()},
                         headers=headers).json()
    return record, headers


def completion_url(record):
    return f'/api/v1/progress/{record["progress_id"]}/complete'


def saved(db_session):
    return tuple(db_session.execute(text(
        "SELECT status, completion_percentage FROM progress"
    )).one())


def set_policy(requirement):
    calls = []

    def policy(resource_id):
        calls.append(resource_id)
        return requirement

    app.dependency_overrides[get_completion_policy] = lambda: policy
    return calls


def test_default_unresolved_policy_does_not_accept_completion(client, enrolled, db_session):
    record, headers = enrolled
    response = client.post(completion_url(record), json={}, headers=headers)
    assert response.status_code == 503
    assert "evidence requirements" in response.json()["detail"]
    assert saved(db_session) == ("enrolled", 0)


def test_explicit_server_exemption_records_completion(client, enrolled, db_session):
    record, headers = enrolled
    calls = set_policy(False)
    response = client.post(completion_url(record), json={}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {**record, "status": "completed", "completion_percentage": 100}
    assert saved(db_session) == ("completed", 100)
    assert calls == [record["resource_id"]]
    assert db_session.execute(text("SELECT count(*) FROM student_skill")).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM skill_change_history")).scalar_one() == 0


def test_tc_f3_06_required_evidence_is_requested_not_bypassed(client, enrolled, db_session):
    record, headers = enrolled
    set_policy(True)
    response = client.post(completion_url(record), json={}, headers=headers)
    assert response.status_code == 409
    assert "Submit valid completion evidence" in response.json()["detail"]
    assert saved(db_session) == ("enrolled", 0)


@pytest.mark.parametrize("requirement", [None, True])
def test_one_hundred_percent_does_not_bypass_evidence(client, enrolled, db_session, requirement):
    record, headers = enrolled
    client.patch(f'/api/v1/progress/{record["progress_id"]}',
                 json={"completion_percentage": 100}, headers=headers)
    set_policy(requirement)
    response = client.post(completion_url(record), json={}, headers=headers)
    assert response.status_code in {409, 503}
    assert saved(db_session) == ("in-progress", 100)


def test_tc_f3_05_non_enrolled_completion_creates_nothing(client, student, bearer, db_session):
    calls = set_policy(False)
    response = client.post("/api/v1/progress/999999/complete", json={}, headers=bearer(student[0]))
    assert response.status_code == 404
    assert calls == []
    assert db_session.execute(text("SELECT count(*) FROM progress")).scalar_one() == 0


def test_cannot_complete_someone_elses_progress(client, enrolled, make_user, bearer, db_session):
    record, _ = enrolled
    other = make_user()
    headers = bearer(other)
    client.post("/api/v1/profile", json={"name": "Other Student"}, headers=headers)
    set_policy(False)
    assert client.post(completion_url(record), json={}, headers=headers).status_code == 404
    assert saved(db_session) == ("enrolled", 0)


def test_repeated_completion_does_not_reapply_or_reopen(client, enrolled, db_session):
    record, headers = enrolled
    calls = set_policy(False)
    first = client.post(completion_url(record), json={}, headers=headers)
    second = client.post(completion_url(record), json={}, headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert calls == [record["resource_id"]]
    assert saved(db_session) == ("completed", 100)


def test_invalidated_resource_cannot_be_completed(client, enrolled, db_session):
    record, headers = enrolled
    set_policy(False)
    db_session.execute(text("UPDATE learning_item SET moderation_state='inactive'"))
    assert client.post(completion_url(record), json={}, headers=headers).status_code == 404
    assert saved(db_session) == ("enrolled", 0)


@pytest.mark.parametrize("payload", [
    {"evidence_required": False}, {"status": "completed"}, {"student_id": 1},
    {"score": 100}, {"evidence_url": "https://example.org/unvalidated"},
])
def test_client_cannot_supply_policy_or_unvalidated_evidence(client, enrolled, payload):
    record, headers = enrolled
    assert client.post(completion_url(record), json=payload, headers=headers).status_code == 422


@pytest.mark.parametrize("role", ["faculty_mentor", "administrator"])
def test_nonstudent_cannot_complete(client, enrolled, make_user, bearer, role):
    record, _ = enrolled
    assert client.post(completion_url(record), json={},
                       headers=bearer(make_user(role), role)).status_code == 403


def test_completion_requires_authentication(client, enrolled):
    assert client.post(completion_url(enrolled[0]), json={}).status_code == 401
