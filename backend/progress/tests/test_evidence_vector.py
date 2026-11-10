"""TC-F3-10: the M3 API delegates validated evidence to a supplied M1 writer."""

from sqlalchemy import text

from backend.main import app
from backend.progress.vector_update import get_skill_vector_writer
from backend.shared.skill_vector import Level, SkillVector, SkillVectorEntry, Source


def tag_resource(db_session, resource_id):
    skill_id = db_session.scalar(text(
        "INSERT INTO skill (skill_name, category) VALUES ('Testing', 'Quality') RETURNING skill_id"
    ))
    db_session.execute(text(
        "INSERT INTO learning_item_skill (item_id, skill_id, coverage_level) "
        "VALUES (:item, :skill, 'intermediate')"
    ), {"item": resource_id, "skill": skill_id})
    return skill_id


def test_evidence_is_pending_then_sent_to_m1_once(client, student, resource, bearer, db_session):
    user_id, student_id = student
    resource_id = resource()
    skill_id = tag_resource(db_session, resource_id)
    headers = bearer(user_id)
    response = client.post("/api/v1/progress/enrol", json={"resource_id": resource_id},
                           headers=headers)
    assert response.status_code == 201
    url = f'/api/v1/progress/{response.json()["progress_id"]}/complete'
    payload = {"evidence": {"evidence_type": "quiz", "score": 80}}

    assert client.post(url, json=payload, headers=headers).status_code == 200
    assert db_session.scalar(text("SELECT vector_applied_at FROM completion_evidence")) is None

    calls = []

    def writer(student, skill, level, source, *, session):
        assert session is db_session
        calls.append((student, skill, level, source))
        return SkillVector((SkillVectorEntry(skill, "Testing", level, None, source),))

    app.dependency_overrides[get_skill_vector_writer] = lambda: writer
    assert client.post(url, json={}, headers=headers).status_code == 200
    assert client.post(url, json={"evidence": {"evidence_type": "quiz", "score": 101}},
                       headers=headers).status_code == 422
    assert calls == []
    assert client.post(url, json=payload, headers=headers).status_code == 200
    assert client.post(url, json=payload, headers=headers).status_code == 200
    assert calls == [(student_id, skill_id, Level.intermediate, Source.completion)]
    assert db_session.scalar(text("SELECT vector_applied_at FROM completion_evidence")) is not None
    assert db_session.scalar(text("SELECT count(*) FROM student_skill")) == 0
