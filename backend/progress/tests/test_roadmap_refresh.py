"""TC-F3-11 M3-side verification using an injected M2 boundary."""

from unittest.mock import Mock

import pytest
from sqlalchemy import text

from backend.main import app
from backend.progress.roadmap_refresh import get_roadmap_invalidator
from backend.progress.tests.test_evidence_vector import tag_resource
from backend.progress.vector_update import get_skill_vector_writer
from backend.shared.skill_vector import Level, SkillVector, SkillVectorEntry, Source


@pytest.mark.parametrize("changed", [False, True])
def test_refresh_is_forwarded_only_for_a_changed_vector(
    client, student, resource, bearer, db_session, changed
):
    user_id, student_id = student
    resource_id = resource()
    skill_id = tag_resource(db_session, resource_id)
    headers = bearer(user_id)
    response = client.post("/api/v1/progress/enrol", json={"resource_id": resource_id},
                           headers=headers)
    assert response.status_code == 201
    url = f'/api/v1/progress/{response.json()["progress_id"]}/complete'
    body = {"evidence": {"evidence_type": "quiz", "score": 90}}
    vector = SkillVector((SkillVectorEntry(
        skill_id, "Testing", Level.intermediate, None, Source.completion
    ),)) if changed else SkillVector()
    writer = Mock(return_value=vector)
    app.dependency_overrides[get_skill_vector_writer] = lambda: writer

    assert client.post(url, json=body, headers=headers).status_code == 200
    pending = text("SELECT roadmap_refresh_pending FROM completion_evidence")
    assert db_session.scalar(pending) is changed

    invalidate = Mock()
    app.dependency_overrides[get_roadmap_invalidator] = lambda: invalidate
    assert client.post(url, json=body, headers=headers).status_code == 200
    assert client.post(url, json=body, headers=headers).status_code == 200
    assert writer.call_count == 1
    if changed:
        invalidate.assert_called_once_with(student_id, session=db_session)
    else:
        invalidate.assert_not_called()
    assert db_session.scalar(pending) is False
