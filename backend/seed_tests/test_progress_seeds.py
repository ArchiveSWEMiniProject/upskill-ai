"""UA-7/UA-8 seed integration checks against the real Alembic schema.

The shared db_session fixture rolls everything back. Only the SQL files' outer
BEGIN/COMMIT lines are omitted here to keep that test transaction in control;
all data statements execute unchanged. The documented psql check also executes
the complete files, including their own transaction boundaries.
"""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

ROOT = Path(__file__).resolve().parents[2]
PROGRESS_SKILLS = {
    "Software Testing Fundamentals",
    "Integration Testing",
    "API Testing",
    "Test Automation",
    "Code Coverage Analysis",
}


def apply_seed(session, filename):
    lines = (ROOT / filename).read_text(encoding="utf-8").splitlines()
    assert sum(line.strip() == "BEGIN;" for line in lines) == 1
    assert sum(line.strip() == "COMMIT;" for line in lines) == 1
    sql = "\n".join(line for line in lines if line.strip() not in {"BEGIN;", "COMMIT;"})
    session.connection().exec_driver_sql(sql)


def skill_snapshot(session):
    return session.execute(
        text("SELECT skill_id, skill_name, category, created_at FROM skill ORDER BY skill_name")
    ).all()


def test_progress_seed_creates_five_canonical_skills(db_session):
    apply_seed(db_session, "taxonomy_seed_progress.sql")
    rows = skill_snapshot(db_session)
    assert {row.skill_name for row in rows} == PROGRESS_SKILLS
    assert all(row.category == "Quality" and row.created_at is not None for row in rows)


def test_progress_seed_is_idempotent_and_keeps_ids_and_timestamps(db_session):
    apply_seed(db_session, "taxonomy_seed_progress.sql")
    first = skill_snapshot(db_session)
    apply_seed(db_session, "taxonomy_seed_progress.sql")
    assert skill_snapshot(db_session) == first


def test_progress_seed_does_not_overwrite_existing_taxonomy_metadata(db_session):
    db_session.execute(
        text("INSERT INTO skill (skill_name, category) VALUES (:name, :category)"),
        {"name": "API Testing", "category": "Team-maintained category"},
    )
    original = skill_snapshot(db_session)[0]
    apply_seed(db_session, "taxonomy_seed_progress.sql")
    existing = next(row for row in skill_snapshot(db_session) if row.skill_name == "API Testing")
    assert existing == original


def test_progress_aliases_are_normalised_and_idempotent(db_session):
    apply_seed(db_session, "taxonomy_seed_progress.sql")
    query = text("SELECT alias_id, skill_id, alias_text FROM skill_alias ORDER BY alias_text")
    first = db_session.execute(query).all()
    assert len(first) == 5
    assert all(row.alias_text == row.alias_text.strip().lower() for row in first)
    apply_seed(db_session, "taxonomy_seed_progress.sql")
    assert db_session.execute(query).all() == first


def test_combined_prerequisite_graph_is_acyclic_and_edges_are_idempotent(db_session):
    apply_seed(db_session, "taxonomy_seed.sql")
    previous = db_session.execute(text("SELECT count(*) FROM skill_prerequisite")).scalar_one()
    apply_seed(db_session, "taxonomy_seed_progress.sql")
    query = text("SELECT skill_id, prerequisite_skill_id FROM skill_prerequisite ORDER BY 1, 2")
    first = db_session.execute(query).all()
    assert len(first) == previous + 4
    apply_seed(db_session, "taxonomy_seed_progress.sql")
    assert db_session.execute(query).all() == first
    cyclic = db_session.execute(
        text("""
        WITH RECURSIVE reachable(root, dependency) AS (
            SELECT skill_id, prerequisite_skill_id FROM skill_prerequisite
            UNION
            SELECT r.root, p.prerequisite_skill_id
            FROM reachable r JOIN skill_prerequisite p ON p.skill_id = r.dependency
        )
        SELECT EXISTS (SELECT 1 FROM reachable WHERE root = dependency)
    """)
    ).scalar_one()
    assert not cyclic


@pytest.mark.parametrize("progress_first", [False, True])
def test_progress_seed_coexists_with_shared_seed_in_either_order(db_session, progress_first):
    names = ["taxonomy_seed.sql", "taxonomy_seed_progress.sql"]
    if progress_first:
        names.reverse()
    for filename in names:
        apply_seed(db_session, filename)
    first = skill_snapshot(db_session)
    assert len(first) == 25  # Current shared 20 plus Hemanth's five, not the team target.
    assert PROGRESS_SKILLS <= {row.skill_name for row in first}
    for filename in reversed(names):
        apply_seed(db_session, filename)
    assert skill_snapshot(db_session) == first
    assert db_session.execute(text("SELECT count(*) FROM student_skill")).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM skill_change_history")).scalar_one() == 0


def catalogue_snapshot(session):
    items = session.execute(text("SELECT * FROM learning_item ORDER BY item_id")).all()
    tags = session.execute(
        text("SELECT * FROM learning_item_skill ORDER BY item_id, skill_id")
    ).all()
    return items, tags


def test_catalogue_seed_creates_five_approved_resources_with_canonical_tags(db_session):
    apply_seed(db_session, "taxonomy_seed_progress.sql")
    apply_seed(db_session, "catalogue_seed_progress.sql")
    items, tags = catalogue_snapshot(db_session)
    assert len(items) == 5
    assert len(tags) == 6
    assert {row.item_id for row in tags} == {row.item_id for row in items}
    assert {row.skill_id for row in tags} == {row.skill_id for row in skill_snapshot(db_session)}
    assert all(row.moderation_state == "approved" and row.item_type == "course" for row in items)
    assert all(row.duration and row.source_url.startswith("https://") for row in items)
    assert all(row.title and row.description and row.source for row in items)
    levels = {row.item_id: row.level for row in items}
    assert all(row.coverage_level == levels[row.item_id] for row in tags)


def test_catalogue_seed_is_idempotent_and_keeps_ids_and_metadata(db_session):
    apply_seed(db_session, "taxonomy_seed_progress.sql")
    apply_seed(db_session, "catalogue_seed_progress.sql")
    first = catalogue_snapshot(db_session)
    apply_seed(db_session, "catalogue_seed_progress.sql")
    assert catalogue_snapshot(db_session) == first


def test_catalogue_seed_keeps_existing_moderation_and_edits(db_session):
    apply_seed(db_session, "taxonomy_seed_progress.sql")
    apply_seed(db_session, "catalogue_seed_progress.sql")
    db_session.execute(
        text("""
        UPDATE learning_item SET moderation_state = 'inactive', description = 'Team-edited text'
        WHERE title = 'Introduction to pytest'
    """)
    )
    first = catalogue_snapshot(db_session)
    apply_seed(db_session, "catalogue_seed_progress.sql")
    assert catalogue_snapshot(db_session) == first


@pytest.mark.parametrize("partial_taxonomy", [False, True])
def test_catalogue_seed_rejects_missing_skills_without_partial_resources(
    db_session, partial_taxonomy
):
    if partial_taxonomy:
        apply_seed(db_session, "taxonomy_seed_progress.sql")
        db_session.execute(text("DELETE FROM skill WHERE skill_name = 'API Testing'"))
    with pytest.raises(DBAPIError, match="Run taxonomy_seed_progress.sql"):
        with db_session.begin_nested():
            apply_seed(db_session, "catalogue_seed_progress.sql")
    assert catalogue_snapshot(db_session) == ([], [])


def test_catalogue_seed_preserves_other_contributors_resources(db_session):
    apply_seed(db_session, "taxonomy_seed.sql")
    apply_seed(db_session, "taxonomy_seed_progress.sql")
    existing_id = db_session.execute(
        text("""
        INSERT INTO learning_item
            (title, description, item_type, level, source_url, moderation_state)
        VALUES ('Other contributor resource', 'Keep this unrelated row', 'course',
                'beginner', 'https://example.org/team-resource', 'pending')
        RETURNING item_id
    """)
    ).scalar_one()
    previous = catalogue_snapshot(db_session)[0][0]
    apply_seed(db_session, "catalogue_seed_progress.sql")
    items, tags = catalogue_snapshot(db_session)
    assert len(items) == 6
    assert next(row for row in items if row.item_id == existing_id) == previous
    assert all(row.item_id != existing_id for row in tags)
