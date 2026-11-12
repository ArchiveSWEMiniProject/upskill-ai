"""TC-F3-10: the M3 API delegates validated evidence to a supplied M1 writer."""

import pytest
from sqlalchemy import text

from backend.main import app
from backend.profile import staleness
from backend.progress.vector_update import get_skill_vector_writer
from backend.shared.skill_vector import Level, SkillVector, SkillVectorEntry, Source
from backend.skills.vector import get_skill_vector


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

    app.dependency_overrides[get_skill_vector_writer] = lambda: None  # M1 unavailable
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


# --- With M1's real writer (UP-12 apply_vector_update) --------------------------


def complete_with_evidence(client, headers, resource_id):
    enrolled = client.post("/api/v1/progress/enrol", json={"resource_id": resource_id},
                           headers=headers)
    assert enrolled.status_code == 201
    url = f'/api/v1/progress/{enrolled.json()["progress_id"]}/complete'
    payload = {"evidence": {"evidence_type": "quiz", "score": 80}}
    assert client.post(url, json=payload, headers=headers).status_code == 200
    return url, payload


def hold(db_session, student_id, skill_id, level):
    db_session.execute(text(
        "INSERT INTO student_skill (student_id, skill_id, source, level) "
        "VALUES (:st, :sk, 'manual', CAST(:lv AS skill_level))"
    ), {"st": student_id, "sk": skill_id, "lv": level})


def completion_rows(db_session):
    return db_session.execute(text(
        "SELECT skill_id, level::text FROM student_skill WHERE source = 'completion'"
    )).all()


def history_rows(db_session):
    return db_session.execute(text(
        "SELECT previous_level::text, new_level::text, source::text FROM skill_change_history"
    )).all()


@pytest.fixture
def stale_calls():
    calls = []
    staleness.set_stale_hook(calls.append)
    yield calls
    staleness.set_stale_hook(None)


def test_completion_raises_the_vector_through_m1(
    client, student, resource, bearer, db_session, stale_calls
):
    user_id, student_id = student
    resource_id = resource()
    skill_id = tag_resource(db_session, resource_id)
    hold(db_session, student_id, skill_id, "beginner")
    headers = bearer(user_id)

    url, payload = complete_with_evidence(client, headers, resource_id)

    assert completion_rows(db_session) == [(skill_id, "intermediate")]
    assert history_rows(db_session) == [(None, "intermediate", "completion")]
    assert stale_calls == [student_id]
    assert db_session.scalar(text("SELECT vector_applied_at FROM completion_evidence")) is not None
    [entry] = get_skill_vector(student_id, db_session).entries
    assert (entry.level, entry.source) == (Level.intermediate, Source.completion)

    # Resubmitting the same evidence applies nothing again.
    assert client.post(url, json=payload, headers=headers).status_code == 200
    assert len(history_rows(db_session)) == 1
    assert stale_calls == [student_id]


def test_completion_below_the_held_level_changes_nothing(
    client, student, resource, bearer, db_session, stale_calls
):
    user_id, student_id = student
    resource_id = resource()
    skill_id = tag_resource(db_session, resource_id)
    hold(db_session, student_id, skill_id, "advanced")
    before = get_skill_vector(student_id, db_session)

    complete_with_evidence(client, bearer(user_id), resource_id)

    assert completion_rows(db_session) == []
    assert history_rows(db_session) == []
    assert stale_calls == []
    assert get_skill_vector(student_id, db_session) == before
    # The evidence is still marked applied, so it is not retried forever.
    assert db_session.scalar(text("SELECT vector_applied_at FROM completion_evidence")) is not None
