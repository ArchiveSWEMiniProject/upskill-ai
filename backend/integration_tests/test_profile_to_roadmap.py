"""Sprint 3 end-to-end demo: profile in, roadmap out (plan.md §7), against real
Postgres (see backend/conftest.py).

One student goes through the whole journey over HTTP only, with no dependency
overrides apart from the test database session:

    register -> log in -> create profile -> declare skills -> skill vector
    -> choose target role (summary + mark_stale) -> GET /roadmap/gap
    -> GET /roadmap -> improve a skill -> gap and summary recomputed

The data is TC-F1-13's: Python Intermediate and SQL Beginner against a role
that needs Python Advanced, SQL Intermediate and Docker Beginner, which gives
exactly three gap entries. Taxonomy, role and catalogue rows are test data
written straight to M4's tables, as the other modules' tests do.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.database import get_session
from backend.main import app
from backend.profile import staleness

API = "/api/v1"

# (skill, alias, required level, weight) for the "Backend Developer" role.
ROLE = [
    ("Python", "py", "advanced", 3),
    ("SQL Basics", "sql", "intermediate", 2),
    ("Docker", "docker", "beginner", 1),
]

# (title, skill, coverage level, moderation state). Only resources that move a
# gap skill above the student's level, up to the required level, and that are
# approved may be recommended (RM-4).
CATALOGUE = [
    ("Python in depth", "Python", "advanced", "approved"),
    ("Python refresher", "Python", "beginner", "approved"),  # below current level
    ("Python draft course", "Python", "advanced", "pending"),  # not approved
    ("SQL joins and indexes", "SQL Basics", "intermediate", "approved"),
    ("SQL first steps", "SQL Basics", "beginner", "approved"),  # already held
    ("Docker from zero", "Docker", "beginner", "approved"),
]


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def stale_calls():
    calls: list[int] = []
    staleness.set_stale_hook(calls.append)
    yield calls
    staleness.set_stale_hook(None)


def _scalar(db_session, sql: str, **params):
    return db_session.execute(text(sql), params).scalar_one()


@pytest.fixture
def role_id(db_session) -> int:
    skills = {}
    for name, alias, _, _ in ROLE:
        skills[name] = _scalar(
            db_session,
            "INSERT INTO skill (skill_name, category) VALUES (:n, 'Demo') RETURNING skill_id",
            n=name,
        )
        db_session.execute(
            text("INSERT INTO skill_alias (skill_id, alias_text) VALUES (:s, :a)"),
            {"s": skills[name], "a": alias},
        )
    role = _scalar(
        db_session,
        "INSERT INTO career_role (role_name, description) "
        "VALUES ('Backend Developer', 'Sprint 3 demo role') RETURNING role_id",
    )
    for name, _, level, weight in ROLE:
        db_session.execute(
            text(
                "INSERT INTO role_skill_requirement (role_id, skill_id, required_level, weight) "
                "VALUES (:r, :s, CAST(:l AS skill_level), :w)"
            ),
            {"r": role, "s": skills[name], "l": level, "w": weight},
        )
    for title, skill, level, state in CATALOGUE:
        item = _scalar(
            db_session,
            "INSERT INTO learning_item (title, description, item_type, level, duration, "
            "source_url, source, moderation_state) VALUES (:t, 'Demo resource', 'course', "
            "CAST(:l AS skill_level), '4 hours', :u, 'Demo Academy', "
            "CAST(:m AS moderation_state)) RETURNING item_id",
            t=title,
            l=level,
            u="https://example.com/" + title.lower().replace(" ", "-"),
            m=state,
        )
        db_session.execute(
            text(
                "INSERT INTO learning_item_skill (item_id, skill_id, coverage_level) "
                "VALUES (:i, :s, CAST(:l AS skill_level))"
            ),
            {"i": item, "s": skills[skill], "l": level},
        )
    return role


def sign_up(client) -> dict[str, str]:
    credentials = {"email": "demo.student@pes.edu", "password": "DemoPass2026"}
    assert client.post(f"{API}/auth/register", json=credentials).status_code == 201
    login = client.post(f"{API}/auth/login", json=credentials)
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def gap_rows(client, headers):
    response = client.get(f"{API}/roadmap/gap", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["role_name"] == "Backend Developer"
    return [
        (i["rank"], i["skill_name"], i["current_level"], i["required_level"])
        for i in body["items"]
    ]


def test_profile_in_roadmap_out(client, role_id, stale_calls):
    headers = sign_up(client)

    # No profile yet: M2 says so instead of returning an empty roadmap.
    assert client.get(f"{API}/roadmap", headers=headers).status_code == 404

    profile = client.post(f"{API}/profile", json={"name": "Demo Student"}, headers=headers)
    assert profile.status_code == 201
    student_id = profile.json()["student_id"]

    # Skills typed the way a student would; both resolve to canonical skills (UP-9).
    for raw, level in [("Python", "intermediate"), ("sql", "beginner")]:
        declared = client.post(
            f"{API}/profile/skills", json={"skill": raw, "level": level}, headers=headers
        )
        assert declared.status_code == 201, declared.json()

    vector = client.get(f"{API}/profile/skill-vector", headers=headers).json()
    assert sorted((e["canonical_skill_name"], e["level"]) for e in vector["entries"]) == [
        ("Python", "intermediate"), ("SQL Basics", "beginner"),
    ]

    # A profile without a target role has no gap yet.
    assert client.get(f"{API}/roadmap/gap", headers=headers).status_code == 409

    # UP-13: choose the role. The summary agrees with compute_gap() and M2 is told.
    chosen = client.put(f"{API}/profile/target-role", json={"role_id": role_id}, headers=headers)
    assert chosen.status_code == 200, chosen.json()
    assert {k: chosen.json()[k] for k in ("role_name", "required", "held", "gap")} == {
        "role_name": "Backend Developer", "required": 3, "held": 0, "gap": 3,
    }
    assert stale_calls == [student_id]

    # TC-F1-13: exactly three gap entries, most important first.
    assert gap_rows(client, headers) == [
        (1, "Python", "intermediate", "advanced"),
        (2, "SQL Basics", "beginner", "intermediate"),
        (3, "Docker", None, "beginner"),
    ]

    # RM-4: each gap skill gets only approved resources that close it.
    roadmap = client.get(f"{API}/roadmap", headers=headers)
    assert roadmap.status_code == 200
    assert {
        item["skill_name"]: [r["title"] for r in item["resources"]]
        for item in roadmap.json()["items"]
    } == {
        "Python": ["Python in depth"],
        "SQL Basics": ["SQL joins and indexes"],
        "Docker": ["Docker from zero"],
    }

    # The student improves SQL: the gap and the summary are recomputed (UP-11).
    raised = client.post(
        f"{API}/profile/skills", json={"skill": "SQL", "level": "intermediate"}, headers=headers
    )
    assert raised.status_code in (200, 201)
    assert gap_rows(client, headers) == [
        (1, "Python", "intermediate", "advanced"),
        (2, "Docker", None, "beginner"),
    ]
    summary = client.get(f"{API}/profile/target-role", headers=headers).json()
    assert (summary["held"], summary["gap"]) == (1, 2)
    assert [i["skill_name"] for i in client.get(f"{API}/roadmap", headers=headers).json()[
        "items"
    ]] == ["Python", "Docker"]


def test_another_student_cannot_see_this_roadmap(client, role_id, make_user, bearer):
    """The roadmap is always the caller's own: a second student with no profile
    gets 404, not the first student's data."""
    first = sign_up(client)
    client.post(f"{API}/profile", json={"name": "Demo Student"}, headers=first)
    client.put(f"{API}/profile/target-role", json={"role_id": role_id}, headers=first)

    second = bearer(make_user())
    assert client.get(f"{API}/roadmap", headers=second).status_code == 404
    assert client.get(f"{API}/roadmap/gap", headers=second).status_code == 404


# --- the same journey on the real seed data the demo uses ---------------------

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_seeds(db_session) -> None:
    """Load taxonomy then catalogue seeds, as backend/seed_tests does: the
    files' own BEGIN/COMMIT lines are dropped and literal % doubled."""
    for pattern, base in [
        ("taxonomy_seed*.sql", "taxonomy_seed.sql"),
        ("catalogue_seed*.sql", "catalogue_seed.sql"),
    ]:
        first = REPO_ROOT / base
        for path in [first, *sorted(p for p in REPO_ROOT.glob(pattern) if p != first)]:
            sql = "\n".join(
                line for line in path.read_text().splitlines()
                if line.strip().upper() not in {"BEGIN;", "COMMIT;"}
            )
            db_session.connection().exec_driver_sql(sql.replace("%", "%%"))


def test_demo_on_seed_data(client, db_session):
    """What the 10 Nov demo shows on a freshly seeded stack: Python intermediate,
    SQL and Docker beginner against Backend Developer is 5 required, 3 held,
    2 gap (the same numbers as STC-F1-01), and every gap skill has resources."""
    load_seeds(db_session)
    role_id = _scalar(
        db_session, "SELECT role_id FROM career_role WHERE role_name = 'Backend Developer'"
    )
    headers = sign_up(client)
    assert client.post(f"{API}/profile", json={"name": "Demo"}, headers=headers).status_code == 201
    for raw, level in [("python3", "intermediate"), ("sql", "beginner"), ("docker", "beginner")]:
        declared = client.post(
            f"{API}/profile/skills", json={"skill": raw, "level": level}, headers=headers
        )
        assert declared.status_code == 201, declared.json()

    chosen = client.put(f"{API}/profile/target-role", json={"role_id": role_id}, headers=headers)
    assert {k: chosen.json()[k] for k in ("required", "held", "gap")} == {
        "required": 5, "held": 3, "gap": 2,
    }

    roadmap = client.get(f"{API}/roadmap", headers=headers)
    assert roadmap.status_code == 200
    items = roadmap.json()["items"]
    assert [(i["rank"], i["skill_name"]) for i in items] == [
        (1, "REST API Design"), (2, "Unit Testing"),
    ]
    for item in items:
        assert item["resources"], f"no resources recommended for {item['skill_name']}"
