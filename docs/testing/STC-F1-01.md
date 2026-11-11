# STC-F1-01: Student builds a profile and sees a consistent gap summary

| | |
|---|---|
| Module | M1, Student Profile and Skill Extraction |
| Owner | Vansh Sharma |
| Type | System test, run on the deployed Docker Compose stack |
| Requirements | REQ-F1-01 to F1-07 (profile, courses, projects), F1-08 to F1-18 (resume upload and extraction), F1-19 to F1-24 (normalisation), F1-31 to F1-34 (target role), F1-35 to F1-38 (validation) |
| Related cases | TC-F1-01 to TC-F1-08, TC-F1-12 |
| When it runs | Hardening (25 to 30 Nov), after PRs #92, #93, #94 and #95 are merged |

The journey: register, log in, create a profile, add 2 courses and 1 project,
upload a resume, confirm the extracted skills, choose a target role, and check
that the gap summary agrees with the skill vector.

## Preconditions

1. The stack is up from a clean volume: `docker compose up -d --build`.
   The API listens on `http://localhost:8000`, the web app on `http://localhost:3000`.
2. Migrations have run and `taxonomy_seed.sql` is loaded, so these exist:
   - roles **Backend Developer** and **Data Analyst**, with the requirements in
     section 4 of the seed;
   - skills **Python**, **SQL Basics** (alias `sql`) and **Docker &
     Containerization** (alias `docker`).
3. `RESUME_HIGH_CONFIDENCE_THRESHOLD` is unset, so the bulk-confirm threshold is
   the default **0.80**.
4. The email `stc.f1.01@pes.edu` is not registered yet. If it is, use a new
   address and write it in the run record.
5. `curl` and `jq` are installed on the machine running the script.

## Test data

| Item | Value |
|---|---|
| Account | `stc.f1.01@pes.edu` / `Stc-F1-01-pass` |
| Profile | Name `Asha Rao`, education level `UG` |
| Course 1 | Data Structures, `UE23CS251A`, grade `A`, term `Sem 3` |
| Course 2 | Database Management Systems, `UE23CS252A`, grade `B`, term `Sem 4` |
| Project | Timetable Planner, a 1-line description, `https://github.com/example/timetable-planner` |
| Resume | [fixtures/stc_f1_01_resume.docx](fixtures/stc_f1_01_resume.docx), rebuilt with [fixtures/make_stc_f1_01_resume.py](fixtures/make_stc_f1_01_resume.py) |

The resume text is fixed so the extractor gives a known result:

```text
Asha Rao
B.Tech Computer Science, PES University, 2027
Technical skills: Python at an intermediate level.
Built a timetable planner in Python that reads course data from CSV files.
Comfortable writing SQL queries for coursework.
Currently learning Docker for packaging small apps.
```

Courses and projects do not add skills to the vector yet (open question 1 in
[M1-SCHEMA.md](../M1-SCHEMA.md)). In this run every skill comes from the resume.

## Script

Run the blocks in order from the repository root, in one shell. Each step
states what to check. If any check fails, stop and record the step number.

```bash
API=http://localhost:8000/api/v1
EMAIL=stc.f1.01@pes.edu
PASS=Stc-F1-01-pass
```

### 1. Register

```bash
curl -s -w '\n%{http_code}\n' -X POST $API/auth/register \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\",\"name\":\"Asha Rao\"}"
```

Expect `201`, with `role` = `student`. UI: the Register form on `/`.

### 2. Log in

```bash
TOKEN=$(curl -s -X POST $API/auth/login -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | jq -r .access_token)
AUTH="Authorization: Bearer $TOKEN"
echo "${TOKEN:0:20}..."
```

Expect a non-empty token (not `null`).

### 3. Create the profile, then try a second one

```bash
curl -s -w '\n%{http_code}\n' -X POST $API/profile -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"name":"Asha Rao","education_level":"UG"}'
curl -s -w '\n%{http_code}\n' -X POST $API/profile -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"name":"Asha Rao","education_level":"UG"}'
```

Expect `201` with `target_role_id` = `null` the first time. The second call is
rejected with "Profile already exists" (TC-F1-01).

### 4. Add two courses and one project

```bash
curl -s -w '\n%{http_code}\n' -X POST $API/profile/courses -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"course_name":"Data Structures","course_code":"UE23CS251A","grade":"A","completion_term":"Sem 3"}'
curl -s -w '\n%{http_code}\n' -X POST $API/profile/courses -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"course_name":"Database Management Systems","course_code":"UE23CS252A","grade":"B","completion_term":"Sem 4"}'
curl -s -w '\n%{http_code}\n' -X POST $API/profile/projects -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"title":"Timetable Planner","description":"Plans a weekly timetable from course data.","repository_url":"https://github.com/example/timetable-planner"}'
curl -s $API/profile/courses -H "$AUTH" | jq length
curl -s $API/profile/projects -H "$AUTH" | jq length
```

Expect `201` three times, then `2` courses and `1` project.

Validation check (REQ-F1-36): send course 2 again with `"grade":"Z"`. Expect
`422` naming `grade`, and the course count still `2`.

### 5. Upload the resume

```bash
curl -s -w '\n%{http_code}\n' -X POST $API/profile/resume -H "$AUTH" \
  -F "file=@docs/testing/fixtures/stc_f1_01_resume.docx"
```

Expect `201` with `file_type` = `docx`, `status` = `extracted` and
`skills_found` = `3`. UI: Resume section, "Read successfully".

### 6. Review the extracted skills, before confirming anything

```bash
curl -s $API/profile/resume/extracted -H "$AUTH" \
  | jq '{threshold, candidates: [.candidates[] | {candidate_id, skill_name, suggested_level, confidence, status}]}'
curl -s $API/profile/skill-vector -H "$AUTH" | jq '.entries | length'
```

Expect `threshold` = `0.8` and exactly these candidates, all `pending`:

| skill_name | suggested_level | confidence | source_sentence |
|---|---|---|---|
| Python | intermediate | 0.85 | Technical skills: Python at an intermediate level. |
| SQL Basics | beginner | 0.5 | Comfortable writing SQL queries for coursework. |
| Docker & Containerization | beginner | 0.5 | Currently learning Docker for packaging small apps. |

The skill vector still has `0` entries, because nothing is stored before the
student confirms it (REQ-F1-15).

### 7. Bulk-confirm the high-confidence skills

```bash
curl -s -X POST $API/profile/skills/confirm-high-confidence -H "$AUTH" \
  | jq '[.confirmed[] | {skill_name, level}]'
```

Expect only Python, at `intermediate` (0.85 ≥ 0.80; the other two are below).

### 8. Confirm the rest, editing one level

```bash
EXTRACTED=$(curl -s $API/profile/resume/extracted -H "$AUTH")
SQL_ID=$(echo "$EXTRACTED" | jq '.candidates[] | select(.skill_name=="SQL Basics") | .candidate_id')
DOCKER_ID=$(echo "$EXTRACTED" | jq '.candidates[] | select(.skill_name=="Docker & Containerization") | .candidate_id')
curl -s -w '\n%{http_code}\n' -X POST $API/profile/skills/confirm -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"decisions\":[{\"candidate_id\":$SQL_ID,\"action\":\"confirm\"},{\"candidate_id\":$DOCKER_ID,\"action\":\"confirm\",\"level\":\"intermediate\"}]}"
```

Expect `200`. SQL Basics is confirmed at `beginner` (the suggested level kept)
and Docker at `intermediate` (the edited level).

### 9. Check the skill vector

```bash
curl -s $API/profile/skill-vector -H "$AUTH" \
  | jq '[.entries[] | {canonical_skill_name, level, source}] | sort_by(.canonical_skill_name)'
```

Expect exactly 3 entries, each with `source` = `resume`: Docker &
Containerization `intermediate`, Python `intermediate`, SQL Basics `beginner`.
There is one entry per canonical skill, even though Python appears twice in
the resume (REQ-F1-19 to F1-21).

### 10. List the roles

```bash
curl -s $API/profile/roles -H "$AUTH" | jq .
ROLE_BE=$(curl -s $API/profile/roles -H "$AUTH" | jq '.[] | select(.role_name=="Backend Developer") | .role_id')
ROLE_DA=$(curl -s $API/profile/roles -H "$AUTH" | jq '.[] | select(.role_name=="Data Analyst") | .role_id')
```

Expect at least Backend Developer and Data Analyst.

### 11. Choose Backend Developer and read the summary

```bash
curl -s -X PUT $API/profile/target-role -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"role_id\":$ROLE_BE}" | jq '{role_name, required, held, gap}'
curl -s $API/profile/target-role -H "$AUTH" | jq '{role_name, required, held, gap}'
```

Both calls return the same counts: **required 5, held 3, gap 2**. UI: Target
role section, after picking Backend Developer.

### 12. Check the counts by hand

Compare the step 9 vector with the Backend Developer requirements in
`taxonomy_seed.sql`. A skill is held when the vector has it at or above the
required level:

| Required skill | Required level | Vector level | Held? |
|---|---|---|---|
| Python | intermediate | intermediate | yes |
| REST API Design | intermediate | none | no |
| SQL Basics | beginner | beginner | yes |
| Docker & Containerization | beginner | intermediate | yes |
| Unit Testing | beginner | none | no |

The counts are consistent when all of these hold:

- `required` equals the number of requirement rows (5);
- `held` equals the rows marked "yes" (3);
- `held + gap = required` (3 + 2 = 5);
- the PUT and GET replies match.

### 13. Change the role and check again

```bash
curl -s -X PUT $API/profile/target-role -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"role_id\":$ROLE_DA}" | jq '{role_name, required, held, gap}'
curl -s $API/profile -H "$AUTH" | jq .target_role_id
```

Expect **required 5, held 1, gap 4**. Only Python is held (needed at beginner).
SQL Basics is in the gap because it is held at beginner and the role needs
intermediate. `target_role_id` now equals `$ROLE_DA`, which shows there is
still only one active role (REQ-F1-32).

## Pass criteria

STC-F1-01 passes when every step's check holds. In particular:

- the second profile create is rejected and the invalid grade is not saved;
- no skill reaches the vector before confirmation (step 6);
- the vector after confirmation is exactly the 3 entries in step 9;
- the gap summary is 5/3/2 for Backend Developer and 5/1/4 for Data Analyst,
  and `held + gap = required` in both.

## Run record

Fill this in from the real run and copy it into the test plan's Actual Result
and Test Result columns.

| Field | Value |
|---|---|
| Date and time | |
| Commit on `main` | |
| Run by / witnessed by | |
| Steps passed | / 13 |
| Actual result | |
| Test result | Pass / Fail |
| Defects raised | |

## Out of scope here

- Stale recommendations and the refreshed roadmap after a skill is removed:
  STC-F1-02.
- One student reading another's profile: TC-F1-15 and STC-F4-02.
- Confirming skills in the web app. There is no confirm screen yet, so steps 6
  to 8 use the API.
