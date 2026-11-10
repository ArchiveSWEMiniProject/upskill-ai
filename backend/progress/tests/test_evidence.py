"""PR-4: validate evidence on the same transaction as completion."""

import pytest
from sqlalchemy import text

from backend.main import app
from backend.progress.completion import get_completion_policy


@pytest.fixture
def enrolment(client, student, resource, bearer):
    headers = bearer(student[0])
    response = client.post("/api/v1/progress/enrol", json={"resource_id": resource()},
                           headers=headers)
    assert response.status_code == 201
    return f'/api/v1/progress/{response.json()["progress_id"]}/complete', headers


@pytest.mark.parametrize("evidence", [
    {"evidence_type": "quiz", "score": 0},
    {"evidence_type": "quiz", "score": 100},
    {"evidence_type": "certificate", "evidence_url": "https://example.org/certificate"},
])
def test_required_evidence_is_stored_and_completion_committed(
    client, enrolment, db_session, evidence
):
    app.dependency_overrides[get_completion_policy] = lambda: lambda _: True
    url, headers = enrolment
    assert client.post(url, json={}, headers=headers).status_code == 409
    body = {"evidence": evidence}
    response = client.post(url, json=body, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert client.post(url, json=body, headers=headers).status_code == 200
    row = db_session.execute(text("SELECT * FROM completion_evidence")).one()
    assert row.progress_id == response.json()["progress_id"]
    assert row.evidence_type == evidence["evidence_type"]
    assert row.score == evidence.get("score")
    assert row.evidence_url == evidence.get("evidence_url")


@pytest.mark.parametrize("evidence", [
    {"evidence_type": "quiz", "score": 130}, {"evidence_type": "quiz", "score": -1},
    {"evidence_type": "quiz", "score": True}, {"evidence_type": "quiz", "score": "50"},
    {"evidence_type": "certificate", "evidence_url": "file:///private/cert.pdf"},
    {"evidence_type": "certificate", "evidence_url": "https://user:pass@example.org/cert"},
    {"evidence_type": "certificate"},
])
def test_invalid_evidence_writes_nothing(client, enrolment, db_session, evidence):
    url, headers = enrolment
    assert client.post(url, json={"evidence": evidence}, headers=headers).status_code == 422
    assert db_session.scalar(text("SELECT count(*) FROM completion_evidence")) == 0
    assert db_session.scalar(text("SELECT status FROM progress")) == "enrolled"


def test_evidence_can_be_added_to_previous_self_report(client, enrolment, db_session):
    url, headers = enrolment
    assert client.post(url, json={}, headers=headers).status_code == 200
    assert db_session.scalar(text("SELECT count(*) FROM completion_evidence")) == 0
    payload = {"evidence": {"evidence_type": "quiz", "score": 70}}
    assert client.post(url, json=payload, headers=headers).status_code == 200
    payload["evidence"]["score"] = 80
    assert client.post(url, json=payload, headers=headers).status_code == 409
    assert db_session.scalar(text("SELECT score FROM completion_evidence")) == 70
