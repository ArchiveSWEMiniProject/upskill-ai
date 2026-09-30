# Shared Contracts

**Status: FINAL (frozen).** Agreed by all four owners (backlog UA-6, architecture rule R3). Any change needs all four to agree; do not edit these unilaterally.

## 1. Skill vector format

Produced by M1, consumed by M2, updated by M3 through M1.

| Field | Type | Notes |
|---|---|---|
| `canonical_skill_id` | integer | FK to `skill.skill_id`. Never a free-text skill name |
| `canonical_skill_name` | string(60) | Denormalised for display only. Never matched on |
| `level` | enum | `beginner`, `intermediate`, `advanced`. Ordered; compare by rank, not string |
| `confidence` | decimal(3,2) | 0.00 to 1.00. Null for manually declared skills |
| `source` | enum | `manual`, `course`, `resume`, `completion` |

Rules:

- Level ordering is beginner < intermediate < advanced. Every comparison uses the rank.
- A skill appears at most once in a vector. Where two sources disagree, the highest level wins and both sources are recorded.
- Only M1 writes this structure. M3 requests changes through `apply_vector_update()`.
- `apply_vector_update()` raises a level only if the incoming level is higher. Equal or lower is a silent no-op, not an error.

## 2. Skill taxonomy schema

| Table | Columns | Owner |
|---|---|---|
| `skill` | `skill_id` PK, `skill_name` unique, `category`, `created_at` | M4 |
| `skill_alias` | `alias_id` PK, `skill_id` FK, `alias_text` unique (lowercased, trimmed) | M4 |
| `skill_prerequisite` | `skill_id` FK, `prerequisite_skill_id` FK, composite PK | M4 |
| `career_role` | `role_id` PK, `role_name` unique, `description` | M4 |
| `role_skill_requirement` | `role_id` FK, `skill_id` FK, `required_level` enum, `weight` int, composite PK | M4 |

Rules:

- Alias matching uses a lowercased, whitespace-trimmed form. "ReactJS", "React.js" and " REACT " resolve to the same `skill_id`.
- The prerequisite graph must be acyclic. RM-5 detects and reports a cycle rather than looping.
- `weight` drives RM-2 ranking. Default 1; higher means more important to the role.

## 3. Resource tagging schema

| Column | Type | Notes |
|---|---|---|
| `item_id` | integer PK | |
| `title`, `description` | string | Required |
| `item_type` | enum | `course`, `certification`, `project_idea` |
| `level` | enum | Same three-level enum as the skill vector |
| `source_url` | string(255) | Required, format-validated |
| `moderation_state` | enum | `pending`, `approved`, `inactive`. Only `approved` is visible to students |
| `learning_item_skill` | join table | `item_id` FK, `skill_id` FK, `coverage_level` enum. A resource may cover several skills |

## Internal module interfaces (from the architecture document, section 5.2)

| Operation | Provider | Consumers |
|---|---|---|
| `get_skill_vector(student_id) -> SkillVector` | M1 | M2 |
| `apply_vector_update(student_id, skill_id, level, source) -> SkillVector` | M1 | M3 |
| `compute_gap(vector, role_id) -> GapResult` | M2 | M1, M3 |
| `build_roadmap(student_id) -> Roadmap` | M2 | API layer |
| `mark_stale(student_id) -> None` | M2 | M1 |
| `get_resources_for_skill(skill_ids, level) -> list[Resource]` | M4 | M2 |
| `authorize(user, action, resource) -> bool` | M4 | All |
| `record_audit(actor, action, target, reason) -> None` | M4 | M2, M3, M4 |
