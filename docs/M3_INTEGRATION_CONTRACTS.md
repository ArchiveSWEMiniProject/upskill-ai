# M3 Integration Contracts

## Scope and source gaps

M3 scope follows the SRS and backlog, with ownership/scope cuts from the newer
Kickoff Plan. The upstream repository was subsequently updated to include the
High Level Software Architecture, backlog, test plan, frozen shared contracts,
and the agreed module directory structure. The Jira backlog and test plan still
list PR-8 / REQ-F3-13/14 and the stalled-path cases; the Kickoff Plan cuts those
requirements. PR-8, TC-F3-08 and STC-F3-02 are therefore excluded pending a
later team decision.

The upstream README assigns `backend/progress/`, `backend/evidence/`, and
`backend/dashboard/` to M3; `backend/shared/` contracts are frozen (UA-6), and
`backend/migrations/` is owned by M4. This slice follows the M3 module paths and
does not claim or implement the M4 migration area. The branch keeps
`backend/shared/` unchanged; M3-local enums, ports, exceptions, unavailable
adapters, dependencies and the development identity placeholder live under
`backend/progress/` until the team supplies its shared runtime contracts.

## Alignment items requiring team decision

The updated architecture/contracts expose integration differences from this
prototype. I have not silently changed API or data behavior as part of a
repository-layout update:

- Architecture §5.1 lists `POST /progress/enrol`, `PATCH /progress/{id}`,
  `POST /progress/{id}/complete`, and `GET /progress/dashboard`; this prototype
  uses `/progress/enrolments...` and `/dashboard/progress` and submits evidence
  through a separate endpoint. Confirm the intended route and evidence workflow
  before changing clients or route behavior.
- Architecture §5.2 specifies `apply_vector_update(...) -> SkillVector`; the
  prototype's port expects `{changed: bool}` so it can know whether to request
  recomputation. The frozen contract specifies canonical skill IDs and
  raise-only updates, but not this result flag. M1/M3/M2 need to agree how M3
  detects an actual vector change without reading M1's repository.
- The frozen resource tagging schema defines integer `item_id`; the prototype
  still uses temporary string resource identifiers. Convert those identifiers
  to the frozen M4 key type before catalogue integration.

These are contract-level integration tasks, not repository-layout changes.
`docs/CONTRACTS.md` is an unchanged copy of upstream's frozen contract.

The Kickoff Plan also assigns an M3 share of five UA-7 taxonomy seed records.
No agreed seed file format or taxonomy schema is in the available source
checkout, so these rows are deferred until M4/Yajat's seed contract exists.

## M1 — skill vector

The current M3 prototype expects an adapter implementing
`SkillVectorPort.apply_vector_update`:

```text
apply_vector_update(student_id, skill_id, level, source="completion") -> {changed: bool}
```

`skill_id` is the canonical taxonomy ID and `level` is `beginner`,
`intermediate`, or `advanced`. M1 owns vector storage and source history. It
compares levels by the agreed rank and raises a level only; equal/lower values
are no-ops. M3 calls this port after completion has valid evidence. M3 stores no
student skill-vector rows. Current production adapter is deliberately
unavailable; tests inject a fake.

## M2 — recommendation recomputation

M2 supplies `RecommendationPort.recompute(student_id) -> {status,
roadmap_version?}`. M3 requests recomputation only after M1 reports a vector
change. M2 owns gap computation, ranking, prerequisites, explanation and roadmap
content. Current production adapter is deliberately unavailable; tests inject
a fake. PR-6 end-to-end completion remains integration-pending until M2's
recompute-on-change path is connected. To populate the dashboard's gap-closure
count, M2 must also expose `get_gap_summary(student_id) -> {gaps_closed,
total_gaps}` or include those values in its recompute/read response.

## M4 — catalogue and identity

M4 supplies `LearningCataloguePort.get_learning_item(resource_id)`, returning
the canonical resource ID/title, whether evidence is required, accepted evidence
types and tagged `(canonical_skill_id, coverage_level)` outcomes. This is how
M3 determines affected skills. Unknown/unavailable catalogue records prevent
enrolment and completion. M4 must replace the temporary `X-Student-Id` header
dependency with its authenticated student identity and enforce role checks;
the header is development-only and is not an authentication mechanism.

## Database integration

M3 defines only `progress`, `completion_evidence`, `milestone` and `notification`
tables. Progress change history is kept in a JSON column on the M3-owned
`progress` row, so re-ranking does not erase the student's recorded work.
Student and resource IDs are currently stored as strings without foreign keys
in this prototype; resource IDs must be aligned to the frozen integer
`item_id` contract before M4 catalogue integration. Evidence files are stored
under `EVIDENCE_STORAGE_DIR`; production
deployment must set a durable private storage location and access policy. The
current 5 MiB PDF upload limit is configurable and is an implementation choice
for the SRS's "reasonable size limits" requirement; the test plan does not state
an evidence-file limit. The current `create_m3_tables()` helper is for local
development only. The team
migration owner should create reviewed Alembic migrations after schema freeze.
Certificate `verified` currently means the submitted PDF passed file type and
payload checks; it does not assert issuer authenticity, which the SRS excludes
from version 1.0.

## Dashboard data boundaries

M3 returns enrolments, progress percentages, completion, evidence-associated
status, completion milestones and adaptive update status. Gap closure counts
remain `null` with `pending-m2-integration` until M2 exposes gap summary data.
The supplied documents do not define how qualifying streak activity is counted,
so the API marks streak calculation unavailable rather than inventing a rule.

## Test mapping

| Case | M3-side coverage |
| --- | --- |
| TC-F3-01 | `test_tc_f3_01_enrols_with_initial_state` |
| TC-F3-02 | `test_tc_f3_02_invalid_resource_is_rejected_without_record` |
| TC-F3-03 | `test_tc_f3_03_accepts_percentage_and_sets_in_progress` |
| TC-F3-04 | `test_tc_f3_04_rejects_out_of_range_percentage` and schema boundary validation |
| TC-F3-05 | `test_tc_f3_05_blocks_completion_without_enrolment` |
| TC-F3-06 | `test_tc_f3_06_requires_evidence_before_completion` |
| TC-F3-07 | `test_tc_f3_07_rejects_invalid_quiz_score` |
| TC-F3-08 | Excluded by Kickoff Plan PR-8 cut |
| TC-F3-09 | `test_dashboard_reports_enrolment_progress_completion_and_milestone`; preserves existing rows through recompute |
| TC-F3-10 | `test_tc_f3_10_skill_update_uses_completion_source_and_triggers_recompute` (fake M1) |
| TC-F3-11 | `test_tc_f3_11_recommendation_failure_is_sanitized` (fake M2) |
| TC-F3-12 | M4 role/mentee authorization integration pending; M3 student self-scope tested |
| STC-F3-01 | Manual full-stack system test pending M1, M2, M4 and deployed stack |
| STC-F3-02 | Excluded by Kickoff Plan PR-8 cut |

All test-plan actual-result fields remain unexecuted until manual system testing.
