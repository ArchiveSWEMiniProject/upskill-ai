# Sprint 2 local validation - 2026-10-27

Base: `274e7cd` from shared main. Branch: `feature/m3-sprint2-seed-ci-hardening`.
This report covers Hemanth's seed contribution, not completion of the shared
team issues or later M3 functionality. Commits use their real execution times.

## Executed checks

| Check | Actual result |
|---|---|
| New seed tests on PostgreSQL 16 / Python 3.12.3 | 13 passed |
| Full backend suite with the disposable PostgreSQL database enabled | 80 collected: 74 passed, 6 xfailed |
| Backend statement coverage, excluding tests/migrations per pyproject.toml | 678/803 statements, 84% rounded |
| Ruff: `ruff check backend` | All checks passed |
| Complete SQL files, including BEGIN/COMMIT, executed twice | Passed; all selected row values, IDs and timestamps identical after the second cycle |
| `git diff --check` | Passed |

The six xfails are the existing documented M2 compute_gap stub tests; none were
added, removed or changed by this branch. Database tests were not skipped.
The existing shared test fixture downgraded/upgraded the actual Alembic migration
on a newly created disposable database whose name contains `test`. No fake
schema, migration, team database, or production data was used.

The initial psql-through-WSL attempt was interrupted by a WSL launcher timeout.
The complete scripts were subsequently executed successfully via psycopg2
against the same real PostgreSQL server, with autocommit enabled outside each
file's own explicit transaction. Both complete cycles and a full row snapshot
comparison passed. This is not a claim that the failed psql attempt passed.

## Observed reference-data counts after both complete cycles

| Table | Rows |
|---|---:|
| skill | 25 |
| career_role | 2 |
| skill_alias | 24 |
| skill_prerequisite | 26 |
| learning_item | 5 |
| learning_item_skill | 6 |
| student_skill | 0 |

These are the shared taxonomy seed plus Hemanth's five-skill contribution and
five-resource catalogue contribution, not a claim of 40 skills/25 resources.
The shared issue's older note saying only one role exists is stale: the current
SQL already inserts Backend Developer and Data Analyst.

## Explicit limits and handoff

- The team's actual shared development/demo database was not modified.
- No new hosted Jenkins/SonarQube run, quality-gate result, frontend test/build,
  deploy smoke test, or end-to-end M3 result is claimed for this branch. The
  normal hosted CI will validate the branch when it is pushed and reviewed.
- UA-7 still needs the other canonical-skill contributions; UA-8 still needs the
  remaining resources. The older Kickoff Plan's 30-skill target conflicts with
  the current issue's 40-skill target; neither was silently changed here.
- PR-1 through PR-9 and M1/M2/M4 runtime behaviour were not implemented or edited.
- Runtime credentials, virtual environments and raw local reports remain
  ignored under `.ci-local/`; they must not be copied into Git.
- No GitHub issue/Project status was changed and no remote push was performed.

Reproduction commands and curation details are in [the seed guide](SPRINT2_SEEDS.md).
