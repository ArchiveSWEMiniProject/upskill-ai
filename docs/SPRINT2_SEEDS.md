# Sprint 2: Hemanth's seed-data contribution

Branch scope: UA-7 (#26), UA-8 (#27), and regression coverage using the existing
CI PostgreSQL provisioning. PR-1 and later progress features are not implemented
here; the current GitHub milestones put them in Sprint 3 or Sprint 4.

## Ownership and scope

- UA-7: the five Quality skills already on main are retained. This contribution
  adds five normalized aliases and four acyclic prerequisite edges, without
  changing their IDs or overwriting existing taxonomy metadata.
- UA-8: five curated courses, six canonical skill links, coverage levels,
  durations and an initial approved seed state. This is shared reference-data
  seeding, not a second runtime catalogue implementation or an admin action by
  a fabricated user. M4 remains the runtime writer under architecture rule R5.
- Existing metadata and moderation decisions are not overwritten on reruns.
  Resource identity for this seed is the pair (title, source_url). A short table
  lock prevents simultaneous copies of this script inserting the same pair;
  no new permanent schema constraints or migrations are introduced.
- No student accounts, skill vectors, recommendations, progress states or
  completion/evidence records are created or changed.

The shared UA-7 issue still requests 40 skills and two roles; the older Kickoff
Plan specifies 30 skills. This branch does not resolve that team-wide conflict
or change either target: Hemanth's documented share is five skills. At base
`274e7cd`, the two committed taxonomy scripts together provide 25 skills and two
roles. The remaining skill contributions are still required. Likewise these five
resources are a contribution to UA-8's team-wide target of 25, not the entire
catalogue. Do not close the shared issues solely on the basis of this branch.

## Run against the shared schema

Use the project's configured environment and Python requirements. Set
`DATABASE_URL` to the intended development/demo PostgreSQL database; do not put
credentials in committed commands. For psql it must be a libpq PostgreSQL URL,
not a SQLAlchemy URL containing a `+psycopg` driver suffix.

```sh
alembic upgrade head
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f taxonomy_seed.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f taxonomy_seed_progress.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f catalogue_seed_progress.sql
```

The progress taxonomy seed is self-contained and may run before or after the
other taxonomy script. The catalogue script requires all five progress skills;
it raises a clear error and inserts nothing if any is missing. Do not remove
this check or invent placeholder taxonomy rows.

Run both progress scripts again to check repeatability. Their transactions
commit together with their skill links; a rerun must not add duplicate rows or
reapprove a resource that an administrator made inactive.

## Curated resource metadata

Levels are this project's curation, not claimed provider certifications.
Durations prefixed with `~` are estimated study time, not provider-published
course lengths. The Coursera listing specifies 26 hours. External availability
and any enrolment/access conditions remain the provider's responsibility; no
claim of free certification is made.

| Resource | Canonical skill(s) | Level | Duration |
|---|---|---|---|
| [Testing From The Inside: Unit Testing Edition](https://testautomationu.applitools.com/unit-testing/) | Software Testing Fundamentals | beginner | ~2 hours |
| [Introduction to pytest](https://testautomationu.applitools.com/pytest-tutorial/index.html) | Test Automation | beginner | ~3 hours |
| [API Testing in Python](https://testautomationu.applitools.com/python-api-testing/) | API Testing; Integration Testing | intermediate | ~3 hours |
| [Setting a Foundation for Successful Test Automation](https://testautomationu.applitools.com/setting-a-foundation-for-successful-test-automation/) | Test Automation | beginner | ~1 hour |
| [Black-box and White-box Testing](https://www.coursera.org/learn/black-box-white-box-testing) | Code Coverage Analysis | intermediate | 26 hours |

## Real-database regression checks

The shared `backend/conftest.py` fixture rebuilds a disposable database from the
actual Alembic migration. Its database name must contain `test`; never point it
at the team's development/demo database or any persistent user data.

```sh
TEST_DATABASE_URL="$DISPOSABLE_TEST_DATABASE_URL" \
  pytest backend/seed_tests -q
TEST_DATABASE_URL="$DISPOSABLE_TEST_DATABASE_URL" \
  pytest --cov=backend
ruff check backend
```

Without `TEST_DATABASE_URL`, database tests are skipped, not passed. Existing
Jenkins CI supplies a throwaway PostgreSQL 16 database and discovers these tests
under `backend/`, so no duplicate database provisioning is added.

The tests check exact seed counts and valid foreign keys, stable IDs/timestamps,
reruns, either taxonomy load order, canonical aliases, graph acyclicity, missing
dependencies, and preservation of unrelated resources and moderation edits.
To preserve fixture rollback isolation, pytest omits only the outer BEGIN and
COMMIT lines. The full-script psql validation must additionally exercise those
transaction boundaries on a disposable migrated database.

These checks do not demonstrate later M3 enrolment, evidence, dashboard or
adaptive-recommendation functionality, nor a complete system test.
