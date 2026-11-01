# Sprint 2 local validation - 2026-11-01

Validated after merging shared main `873e277` into
`feature/m3-sprint2-seed-ci-hardening` to address PR #79 review feedback.
This report supersedes the October 27 results from base `274e7cd`; those older
results do not validate the current shared taxonomy or merged code.

## Executed checks

| Check | Actual result |
|---|---|
| Full backend suite on PostgreSQL 16 / Python 3.12.3 | 226 passed; no failures, skips or xfails |
| Backend statement coverage, excluding tests/migrations per pyproject.toml | 1080/1156 statements, 93% rounded |
| Ruff: `ruff check backend` | All checks passed |
| All five complete SQL files, including BEGIN/COMMIT, executed twice | Passed; full row values, IDs and timestamps identical after the second cycle |
| `git diff --check` | Passed |

The full suite includes all 13 progress-seed cases, both taxonomy load orders,
shared taxonomy acceptance checks and shared catalogue acceptance checks. The
coexistence test compares the canonical-name union with the current shared seed
instead of assuming the obsolete 25-skill total. Existing M2 gap tests now pass
on current main; the historical six xfails no longer describe this revision.

The existing fixture downgraded/upgraded the actual Alembic migrations on a
new disposable PostgreSQL 16 database whose name contains `test`. Complete SQL
transactions were then run through psycopg2, outside pytest's rollback fixture,
with autocommit enabled outside each file's explicit transaction. Both cycles
loaded `taxonomy_seed.sql`, `taxonomy_seed_profile.sql`,
`taxonomy_seed_progress.sql`, `catalogue_seed.sql`, and
`catalogue_seed_progress.sql`, in that order.

## Observed reference-data counts after both complete cycles

| Table | Rows |
|---|---:|
| skill | 49 |
| career_role | 2 |
| skill_alias | 56 |
| skill_prerequisite | 53 |
| learning_item | 35 |
| learning_item_skill | 52 |
| student_skill | 0 |

The base taxonomy alone now provides 40 skills and two roles. Progress definitions
reuse the existing API Testing row and add four others; the profile seed adds
five more distinct skills. The shared catalogue supplies 30 resources and the
progress catalogue adds five. The shared suite checks the numeric UA-7/UA-8
criteria and related graph, alias and catalogue requirements. These team totals
are not attributed solely to this branch.

## Explicit limits and handoff

- The team's actual shared development/demo database was not modified.
- Local backend and complete-SQL results do not establish hosted Jenkins,
  SonarQube gate, frontend build or full-system success. The previous PR check
  predates the update from main; the pushed revision needs its own hosted check.
- This branch adds no PR-1 through PR-9 functionality or M1/M2/M4 runtime changes.
  Their current implementations come from the merge of shared main.
- Credentials, virtual environments and raw local reports remain ignored under
  `.ci-local/`; they must not be copied into Git.
- Formal review and merge remain outstanding. Shared issue status is a team
  decision; this contribution does not automatically close UA-7 or UA-8.

Reproduction commands and curation details are in [the seed guide](SPRINT2_SEEDS.md).
