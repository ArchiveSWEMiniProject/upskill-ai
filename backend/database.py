"""Database engine and session for every module.

The schema is owned by the Alembic migrations in backend/migrations (UA-5);
models here only map onto it, so nothing calls create_all(). Each module
declares its own models on `Base` and uses `get_session` as a FastAPI
dependency.
"""

import os
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Every secret in .env.example starts with this, so a copied but unedited
# .env is refused instead of running with a password everyone knows.
PLACEHOLDER_PREFIX = "change-me"


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    if (make_url(url).password or "").startswith(PLACEHOLDER_PREFIX):
        raise RuntimeError(
            "The database password is still the change-me placeholder from .env.example; "
            "set POSTGRES_PASSWORD in .env"
        )
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(database_url(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """One session per request; the caller commits, errors roll back."""
    session = _session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Alias for compatibility across module dependencies
get_db = get_session
