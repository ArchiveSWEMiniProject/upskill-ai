"""Shared database fixtures for tests that need real Postgres.

Set TEST_DATABASE_URL to a disposable Postgres database. The schema is
rebuilt from the Alembic migrations once per test session, and each test runs
inside a transaction that is rolled back afterwards. Without TEST_DATABASE_URL
the database tests are skipped; CI always provides one.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping database tests")
    # The schema is dropped and rebuilt, so never touch a database that is not
    # obviously a test one.
    parsed = make_url(url)
    if "test" not in (parsed.database or ""):
        raise RuntimeError("TEST_DATABASE_URL must name a database containing 'test'")
    # Fail fast instead of hanging when the server cannot be reached.
    if "connect_timeout" not in parsed.query:
        parsed = parsed.update_query_dict({"connect_timeout": "10"})
    url = parsed.render_as_string(hide_password=False)
    # backend/migrations/env.py takes its URL from DATABASE_URL.
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        config = Config(str(REPO_ROOT / "alembic.ini"))
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """A session whose commits are savepoints inside one outer transaction
    that is always rolled back, so tests never see each other's data."""
    with db_engine.connect() as connection:
        outer = connection.begin()
        session = Session(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            session.close()
            outer.rollback()


@pytest.fixture
def make_user(db_session: Session):
    """Insert a user_account row (an M4 table) for tests that need an account."""
    counter = iter(range(1, 10_000))

    def _make_user(role: str = "student") -> int:
        email = f"test-user-{next(counter)}@pes.edu"
        return db_session.execute(
            text(
                "INSERT INTO user_account (email, password_hash, role) "
                "VALUES (:email, 'not-a-real-hash', :role) RETURNING user_id"
            ),
            {"email": email, "role": role},
        ).scalar_one()

    return _make_user
