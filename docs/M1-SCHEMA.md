# M1 Profile & Skill Extraction: table design

Proposal for review by Shubhika, who writes the Alembic migration (UA-5). M1 (Vansh) is the only writer of every table below (rule R4). Field lengths and enums follow SRS Appendix B and `docs/CONTRACTS.md`. Nothing here changes a frozen contract.

## Tables

### `student`
One profile per account (REQ-F1-01, F1-39).

| Column | Type | Notes |
|---|---|---|
| `student_id` | integer PK | |
| `user_id` | integer FK `user_account`, **unique**, not null | Enforces one profile per account |
| `name` | varchar(60) not null | |
| `education_level` | varchar(30) null | |
| `target_role_id` | integer FK `career_role`, null | At most one active role (REQ-F1-32). Changing it marks recommendations stale |
| `target_role_set_at` | timestamptz null | |
| `created_at`, `updated_at` | timestamptz | |

Email is not repeated here. It lives in `user_account`, which M4 owns, to avoid two copies drifting apart.

### `profile_item`
A course or project entry (REQ-F1-02, F1-03).

| Column | Type | Notes |
|---|---|---|
| `profile_item_id` | integer PK | |
| `student_id` | integer FK, not null | Index. Cascade on delete |
| `item_type` | enum `course`, `project` | |
| `title` | varchar(100) not null | Course name or project title |
| `course_code` | varchar(15) null | Course only |
| `grade` | varchar(3) null | Course only. `S A B C D E F` or `0`-`100` (REQ-F1-36) |
| `completion_term` | varchar(10) null | Course only, required for courses |
| `description` | varchar(2000) null | Project only, required for projects (REQ-F1-37) |
| `repository_url` | varchar(255) null | Project only, format-validated |
| `created_at`, `updated_at` | timestamptz | |

`CHECK` constraints per `item_type`: a course needs `grade` and `completion_term`; a project needs `description`. Grade validity is enforced in the API validators and again by a `CHECK`.

### `student_skill` (stored form of the skill vector)
One row per **student, skill and source**, so all contributing sources are kept (REQ-F1-06, F1-24). The vector is derived from this table, not stored as its own thing.

| Column | Type | Notes |
|---|---|---|
| `student_id` | FK | Composite PK with `skill_id` and `source` |
| `skill_id` | FK `skill` | |
| `source` | enum `manual`, `course`, `resume`, `completion` | |
| `level` | enum `beginner`, `intermediate`, `advanced` | Compared by rank, never as a string |
| `confidence` | numeric(3,2) null, `CHECK` 0 to 1 | Null for manual skills |
| `updated_at` | timestamptz | |

Vector rule: group by `(student_id, skill_id)`, take the highest level by rank. The winning row supplies `source` and `confidence`. Every skill therefore appears once in the vector and every source stays recorded.

### `skill_change_history`
Append-only (REQ-F1-07).

| Column | Type | Notes |
|---|---|---|
| `history_id` | integer PK | |
| `student_id`, `skill_id` | FK | Index on both |
| `previous_level` | enum null | Null when the skill is newly added |
| `new_level` | enum null | Null when the skill is removed (STC-F1-02 removes SQL) |
| `source` | enum | Same four values |
| `changed_at` | timestamptz default now | |

### `resume_upload`

| Column | Type | Notes |
|---|---|---|
| `upload_id` | integer PK | |
| `student_id` | FK | |
| `original_filename` | varchar(255) | |
| `stored_path` | varchar(255) | Outside the web root (NFR-SEC-06) |
| `file_type` | enum `pdf`, `docx` | |
| `size_bytes` | integer, `CHECK` <= 5242880 | |
| `status` | enum `uploaded`, `processing`, `extracted`, `unreadable`, `failed` | `unreadable` = under 100 characters of text (REQ-F1-11) |
| `uploaded_at`, `processed_at` | timestamptz | |
| `delete_after` | timestamptz | `processed_at + 30 days` (REQ-F1-18) |
| `deleted_at` | timestamptz null | Set when the cleanup job removes the file |

## Additional tables needed (not in architecture section 4.7)

The five tables above are the ones the architecture document lists. Two more are required by acceptance criteria and would otherwise have nowhere to live. Both are M1-only, so single-writer still holds. **They must go into UA-5**, and section 4.7 of the architecture document should list them.

### `extracted_skill_candidate`
Holds extracted skills awaiting confirmation. Nothing here reaches `student_skill` until the student confirms (REQ-F1-13 to F1-17).

| Column | Type | Notes |
|---|---|---|
| `candidate_id` | integer PK | |
| `upload_id` | FK `resume_upload`, cascade | |
| `skill_id` | FK `skill` | |
| `suggested_level` | enum | |
| `confidence` | numeric(3,2) | |
| `source_sentence` | text | Shown to the student (REQ-F1-14) |
| `status` | enum `pending`, `confirmed`, `rejected` | |
| `decided_at` | timestamptz null | |

Unique on `(upload_id, skill_id)`.

### `unresolved_skill`
Strings the resolver could not match (REQ-F1-22). UP-10 is cut to recording plus asking the student, with no admin screen.

| Column | Type | Notes |
|---|---|---|
| `unresolved_id` | integer PK | |
| `student_id` | FK | |
| `upload_id` | FK null | Null if typed by hand |
| `raw_text` | varchar(120) | As entered |
| `normalised_text` | varchar(120) | Lowercased, trimmed |
| `status` | enum `open`, `mapped` | |
| `mapped_skill_id` | FK `skill` null | Set when the student picks one |
| `created_at` | timestamptz | |

## Questions to settle with the team

1. **How does a course produce skills?** REQ-F1-02 gives a course only a name, code, grade and term, and no skill list. UP-3 says the skills a course implies are captured, and TC-F1-10 has a "course" source at Beginner. Proposal: when adding a course the student picks the taxonomy skills it taught, and level comes from a fixed grade mapping (for example S/A = intermediate, others = beginner). Needs agreement before UP-3 in Sprint 2.
2. **Two extra tables** above: Shubhika to include them in UA-5.
3. **Same skill from two courses.** The primary key allows one `course` row per skill, at the highest level. Confirm that is acceptable.
