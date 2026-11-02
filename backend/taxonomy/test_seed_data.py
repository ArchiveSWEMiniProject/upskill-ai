"""The taxonomy seed files load on the real schema and meet UA-7.

Runs against the migrated test database (backend/conftest.py), so a seed that
no longer matches the schema fails CI instead of failing at demo time.
"""

from pathlib import Path

import pytest
from sqlalchemy import text

from backend.taxonomy.resolver import SkillResolver, build_alias_index

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_SEED = REPO_ROOT / "taxonomy_seed.sql"


def seed_files() -> list[Path]:
    """The base seed first; the others only add to it."""
    others = sorted(p for p in REPO_ROOT.glob("taxonomy_seed*.sql") if p != BASE_SEED)
    return [BASE_SEED, *others]


def load(session, path: Path) -> None:
    # Each file wraps itself in BEGIN/COMMIT for psql; the test owns the
    # transaction instead, so those two lines are dropped.
    sql = "\n".join(
        line for line in path.read_text().splitlines()
        if line.strip().upper() not in {"BEGIN;", "COMMIT;"}
    )
    session.connection().exec_driver_sql(sql)


def count(session, table: str) -> int:
    return session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


TABLES = ["skill", "skill_alias", "skill_prerequisite", "career_role", "role_skill_requirement"]


@pytest.fixture
def seeded(db_session):
    for path in seed_files():
        load(db_session, path)
    return db_session


def test_seed_files_exist():
    assert BASE_SEED.exists()
    assert len(seed_files()) >= 3


def test_meets_ua7_acceptance_criteria(seeded):
    assert count(seeded, "skill") >= 40
    assert count(seeded, "skill_alias") > 0
    assert count(seeded, "skill_prerequisite") > 0
    roles = seeded.execute(text(
        "SELECT r.role_name, count(q.skill_id) FROM career_role r "
        "LEFT JOIN role_skill_requirement q USING (role_id) GROUP BY r.role_name"
    )).all()
    assert len(roles) >= 2
    assert all(required > 0 for _, required in roles), roles


def test_loading_again_changes_nothing(seeded):
    before = {table: count(seeded, table) for table in TABLES}
    for path in seed_files():
        load(seeded, path)
    assert {table: count(seeded, table) for table in TABLES} == before


def test_prerequisite_graph_has_no_cycles(seeded):
    cycles = seeded.execute(text("""
        WITH RECURSIVE walk(start, current, path) AS (
            SELECT skill_id, prerequisite_skill_id, ARRAY[skill_id]
            FROM skill_prerequisite
            UNION ALL
            SELECT w.start, p.prerequisite_skill_id, w.path || w.current
            FROM walk w JOIN skill_prerequisite p ON p.skill_id = w.current
            WHERE NOT w.current = ANY(w.path)
        )
        SELECT count(*) FROM walk WHERE current = start
    """)).scalar_one()
    assert cycles == 0


def test_aliases_build_a_conflict_free_resolver(seeded):
    """No alias may point at two skills or shadow another skill's name;
    build_alias_index raises AliasConflictError if one does."""
    skills = seeded.execute(text("SELECT skill_id, skill_name FROM skill")).all()
    aliases = seeded.execute(text("SELECT skill_id, alias_text FROM skill_alias")).all()
    resolver = SkillResolver(build_alias_index(skills, aliases))
    react = dict((name, skill_id) for skill_id, name in skills)["React"]

    # TC-F1-08 against the real seed data
    for variant in ["ReactJS", "React.js", "react", " REACT "]:
        assert resolver.resolve(variant) == react


def test_aliases_are_stored_normalised(seeded):
    bad = seeded.execute(text(
        "SELECT alias_text FROM skill_alias WHERE alias_text <> lower(trim(alias_text))"
    )).scalars().all()
    assert bad == []
