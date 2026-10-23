import pytest
from sqlalchemy import text

from backend import database


@pytest.fixture(autouse=True)
def fresh_engine_cache():
    database.get_engine.cache_clear()
    database._session_factory.cache_clear()
    yield
    database.get_engine.cache_clear()
    database._session_factory.cache_clear()


def test_missing_database_url_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        database.get_engine()


def test_session_is_usable_and_closed_after_the_request(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    sessions = database.get_session()
    session = next(sessions)
    assert session.execute(text("SELECT 1")).scalar_one() == 1
    with pytest.raises(StopIteration):
        next(sessions)
    assert not session.in_transaction()


def test_session_rolls_back_when_the_request_fails(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    sessions = database.get_session()
    session = next(sessions)
    session.execute(text("SELECT 1"))
    with pytest.raises(ValueError):
        sessions.throw(ValueError("handler failed"))
    assert not session.in_transaction()
