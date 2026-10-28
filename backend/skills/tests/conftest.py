import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.database import get_session
from backend.main import app

TAXONOMY = {
    "React": ["reactjs", "react.js"],
    "Python": ["py", "python3"],
    "SQL Basics": ["sql"],
}


@pytest.fixture
def skill_ids(db_session) -> dict[str, int]:
    """Seed a small taxonomy (M4's tables; test data only) and return name -> id."""
    ids = {}
    for name, aliases in TAXONOMY.items():
        ids[name] = db_session.execute(
            text("INSERT INTO skill (skill_name, category) VALUES (:n, 'Test') RETURNING skill_id"),
            {"n": name},
        ).scalar_one()
        for alias in aliases:
            db_session.execute(
                text("INSERT INTO skill_alias (skill_id, alias_text) VALUES (:s, :a)"),
                {"s": ids[name], "a": alias},
            )
    return ids


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def student(client, make_user, bearer) -> dict:
    """A user with a profile; returns the request headers for that user."""
    headers = bearer(make_user())
    assert client.post("/api/v1/profile", json={"name": "Asha"}, headers=headers).status_code == 201
    return headers
