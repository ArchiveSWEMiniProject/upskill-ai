"""UA-8: the catalogue seed loads on the real schema and meets the story.

Runs against the migrated test database (backend/conftest.py): the taxonomy
seeds first, then every catalogue seed, so a seed that drifts from the schema
or the taxonomy fails CI instead of failing at demo time.
"""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOGUE_SEED = REPO_ROOT / "catalogue_seed.sql"


def ordered(pattern: str, base: str) -> list[Path]:
    """The base file first; the others only add to it."""
    first = REPO_ROOT / base
    return [first, *sorted(p for p in REPO_ROOT.glob(pattern) if p != first)]


def load(session, path: Path) -> None:
    # Each file wraps itself in BEGIN/COMMIT for psql; the test owns the
    # transaction instead, so those two lines are dropped. The driver reads
    # "%" as a parameter marker, so a literal one (RAISE messages) is doubled.
    sql = "\n".join(
        line for line in path.read_text().splitlines()
        if line.strip().upper() not in {"BEGIN;", "COMMIT;"}
    )
    session.connection().exec_driver_sql(sql.replace("%", "%%"))


def load_catalogue(session) -> None:
    for path in ordered("catalogue_seed*.sql", "catalogue_seed.sql"):
        load(session, path)


def rows(session, sql: str):
    return session.execute(text(sql)).all()


@pytest.fixture
def seeded(db_session):
    for path in ordered("taxonomy_seed*.sql", "taxonomy_seed.sql"):
        load(db_session, path)
    load_catalogue(db_session)
    return db_session


def test_at_least_25_approved_resources(seeded):
    (approved,) = rows(
        seeded, "SELECT count(*) FROM learning_item WHERE moderation_state = 'approved'"
    )
    assert approved[0] >= 25


def test_every_resource_is_tagged_with_skill_level_and_duration(seeded):
    untagged = rows(seeded, """
        SELECT li.title FROM learning_item li
        WHERE NOT EXISTS (SELECT 1 FROM learning_item_skill t WHERE t.item_id = li.item_id)
           OR li.duration IS NULL OR trim(li.duration) = ''
    """)
    assert untagged == []  # level is NOT NULL in the schema


def test_resources_cover_several_skills_and_all_three_types(seeded):
    (skills,) = rows(seeded, "SELECT count(DISTINCT skill_id) FROM learning_item_skill")
    assert skills[0] >= 20
    types = {t for (t,) in rows(seeded, "SELECT DISTINCT item_type::text FROM learning_item")}
    assert types == {"course", "certification", "project_idea"}


def test_every_role_requirement_has_a_resource_at_the_required_level(seeded):
    """The user story: roadmaps contain real resources, not empty results."""
    uncovered = rows(seeded, """
        SELECT r.role_name, s.skill_name, q.required_level
        FROM role_skill_requirement q
        JOIN career_role r USING (role_id)
        JOIN skill s USING (skill_id)
        WHERE NOT EXISTS (
            SELECT 1 FROM learning_item_skill t
            JOIN learning_item li USING (item_id)
            WHERE t.skill_id = q.skill_id
              AND li.moderation_state = 'approved'
              AND t.coverage_level >= q.required_level
        )
    """)
    assert uncovered == []


def test_source_urls_are_http_and_unique(seeded):
    bad = rows(
        seeded, "SELECT source_url FROM learning_item WHERE source_url !~ '^https?://[^/ ]+'"
    )
    assert bad == []
    duplicated = rows(seeded, """
        SELECT source_url FROM learning_item GROUP BY source_url HAVING count(*) > 1
    """)
    assert duplicated == []


def test_loading_again_changes_nothing(seeded):
    snapshot = (
        "SELECT count(*) FROM learning_item UNION ALL SELECT count(*) FROM learning_item_skill"
    )
    before = rows(seeded, snapshot)
    load_catalogue(seeded)
    assert rows(seeded, snapshot) == before


def test_loading_again_keeps_an_administrators_moderation_decision(seeded):
    sqlbolt = "WHERE source_url = 'https://sqlbolt.com/'"
    seeded.execute(text(f"UPDATE learning_item SET moderation_state = 'inactive' {sqlbolt}"))
    load_catalogue(seeded)
    (state,) = rows(seeded, f"SELECT moderation_state FROM learning_item {sqlbolt}")
    assert state[0] == "inactive"


def test_refuses_to_run_before_the_taxonomy(db_session):
    with pytest.raises(DBAPIError, match="Load the taxonomy seeds before catalogue_seed.sql"):
        load(db_session, CATALOGUE_SEED)
