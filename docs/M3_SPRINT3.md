# M3 Sprint 3 handoff

Live GitHub assignments on 2026-11-05: #51 (PR-1 enrolment), #52 (PR-2 progress),
and #53 (PR-3 completion). The older Kickoff Plan puts PR-3 in Sprint 4; the
newer explicit Sprint 3 assignment on #53 is followed for this work. PR-4 through
PR-9 remain outside these changes. The team has confirmed evidence policy is an
unresolved integration; completion's PR must remain draft until it is resolved.

## PR-1 / issue #51

- `POST /api/v1/progress/enrol`, body `{"resource_id": 12}`, returns 201 and
  `progress_id`, `resource_id`, `status: "enrolled"`, `completion_percentage: 0`.
  These fields/states follow SRS Appendix B and TC-F3-01. Invalid, pending and
  inactive resources return 404 (TC-F3-02; approved-only catalogue visibility).
- Real M4 bearer authentication, student role dependency and central `authorize`
  protect the route. Identity comes from the token/profile, never request IDs.
- Repeated enrolment returns the same progress without resetting it. A unique
  student/resource key and PostgreSQL conflict handling protect concurrent retries.
  This is a documented implementation choice where the sources specify no retry
  response. Resource identities are canonical integer IDs, not temporary strings.
- Migration `002_m3_progress` adds only the real M3 progress table from the HLD ER
  diagram, with range/state checks and foreign keys. It changes neither frozen
  skill contracts nor existing tables. Shubhika reviews schema integration.
- Two small public read interfaces keep M3 away from other modules' internals:
  M1 `backend.profile.get_student_id(user_id, db)` and M4
  `backend.catalogue.get_resource(item_id, db)`. They return scalar/dict data and
  perform no writes. No placeholder authentication or fake adapters are used.
- `/progress/12` loads resource 12 through the existing catalogue API and offers
  enrol/resume tracking. Roadmap UI can link to this path when M2's roadmap ships;
  no recommendation algorithm or recommendation-membership rule is invented here.
- Tests: real PostgreSQL/Alembic API cases for TC-F3-01/02, moderation, ownership,
  retries, validation, role/authentication and database bounds, plus UI interaction
  tests. Hosted CI and review results must be checked on the actual PR revision.

Local PR-1 validation on 2026-11-05: Python 3.12.3 / PostgreSQL 16, real Alembic
schema: **280 backend tests passed**, including 17 enrolment cases. Ruff passed.
Frontend PR-1 validation: **38 tests passed**, TypeScript passed as part of the
Next.js production build, and the production build passed. There is no separate
frontend lint script in the current repository; no lint result is invented.

## PR-2 / issue #52

`PATCH /api/v1/progress/{progress_id}` accepts `completion_percentage` as a whole
number from 0 through 100 inclusive (SRS Appendix B; TC-F3-03/04). Invalid values
return 422 naming the field and do not change stored progress. Only the enrollee
can update; nonexistent and other students' progress both return 404.

The sources do not define every transition detail. The implementation keeps 0%
as `enrolled` and positive progress, including 100%, as `in-progress`; only the
separate evidence-aware completion operation may set `completed`. Completed
records reject percentage edits with 409, preventing accidental reopening.
These transition choices need review; no additional persisted states are added.
Row locking serializes edits/completion and prevents races on the same record.

The tracking page displays the saved server response and provides a percentage
editor with field-level validation. No dashboard or completion workflow is added
in this PR. Merge after PR-1 (#51); the branch/PR is based on that feature branch.

Local PR-2 validation on 2026-11-05: **300 backend tests passed**, **95% backend
coverage** (1370/1445 statements), Ruff passed; **42 frontend tests passed** and
`npm run typecheck` passed. Jest excludes generated `.next` modules so running
tests after a production build does not discover the standalone package twice.
