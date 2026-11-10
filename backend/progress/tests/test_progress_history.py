"""TC-F3-09: persisted progress is independent of roadmap identity."""

from sqlalchemy import text

from backend.main import app
from backend.progress.roadmap_refresh import get_roadmap_invalidator
from backend.progress.tests.test_evidence_vector import tag_resource
from backend.progress.vector_update import get_skill_vector_writer
from backend.shared.skill_vector import Level, SkillVector, SkillVectorEntry, Source


def test_roadmap_replacement_preserves_saved_history(client, student, resource, bearer, db_session):
    headers = bearer(student[0])
    resource_id = resource()
    skill_id = tag_resource(db_session, resource_id)
    other_id = resource()
    enrol = "/api/v1/progress/enrol"
    first = client.post(enrol, json={"resource_id": resource_id}, headers=headers).json()
    other = client.post(enrol, json={"resource_id": other_id}, headers=headers).json()
    assert client.post(enrol, json={"resource_id": resource_id}, headers=headers).json() == first
    url = f'/api/v1/progress/{first["progress_id"]}'
    for _ in range(2):
        response = client.patch(url, json={"completion_percentage": 60}, headers=headers)
        assert response.status_code == 200

    roadmap = [resource_id, other_id]

    def replace_roadmap(student_id, *, session):
        assert student_id == student[1] and session is db_session
        roadmap[:] = [other_id]

    vector = SkillVector((SkillVectorEntry(
        skill_id, "Testing", Level.intermediate, None, Source.completion
    ),))
    app.dependency_overrides[get_skill_vector_writer] = lambda: lambda *args, **kwargs: vector
    app.dependency_overrides[get_roadmap_invalidator] = lambda: replace_roadmap
    payload = {"evidence": {"evidence_type": "quiz", "score": 90}}
    for _ in range(2):
        response = client.post(f"{url}/complete", json=payload, headers=headers)
        assert response.status_code == 200
    assert roadmap == [other_id]

    snapshots = db_session.execute(text(
        "SELECT progress_id, status, completion_percentage FROM progress_event ORDER BY event_id"
    )).all()
    assert snapshots == [
        (first["progress_id"], "enrolled", 0), (other["progress_id"], "enrolled", 0),
        (first["progress_id"], "in-progress", 60), (first["progress_id"], "completed", 100),
    ]
    saved = client.post(enrol, json={"resource_id": resource_id}, headers=headers).json()
    assert saved == {**first, "status": "completed", "completion_percentage": 100}
