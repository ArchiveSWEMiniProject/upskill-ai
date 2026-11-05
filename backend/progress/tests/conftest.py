"""Real shared-schema fixtures for M3 API tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.database import get_session
from backend.main import app


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def student(db_session, make_user):
    user_id = make_user()
    student_id = db_session.execute(text(
        "INSERT INTO student (user_id, name) VALUES (:uid, 'Progress Student') "
        "RETURNING student_id"
    ), {"uid": user_id}).scalar_one()
    return user_id, student_id


@pytest.fixture
def resource(db_session):
    def create(moderation="approved"):
        return db_session.execute(text("""
            INSERT INTO learning_item
                (title, description, item_type, level, source_url, moderation_state)
            VALUES ('Learning resource', 'Progress test resource', 'course', 'beginner',
                    'https://example.org/course', :moderation)
            RETURNING item_id
        """), {"moderation": moderation}).scalar_one()
    return create
