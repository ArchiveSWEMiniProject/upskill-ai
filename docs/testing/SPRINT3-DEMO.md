# Sprint 3 demo: profile in, roadmap out

Goal (plan.md §7): one student builds a profile, picks a target role and gets a ranked
roadmap. The same journey is automated in
`backend/integration_tests/test_profile_to_roadmap.py`, which runs on every CI build, so
a green pipeline means this script works.

Needs on `main`: UP-13 target role (#92), RM-3 gap (#87), RM-4 roadmap (#91).

## 1. Start the stack and seed it

```bash
cp .env.example .env            # then set POSTGRES_PASSWORD and JWT_SECRET
docker compose up -d --build   # the API runs the migrations on start
for f in taxonomy_seed.sql taxonomy_seed_*.sql catalogue_seed.sql; do
  docker compose exec -T upskill-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$f"
done
API=http://localhost:8000/api/v1
```

## 2. Run the journey

```bash
# Register and log in
curl -s -X POST $API/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"demo.student@pes.edu","password":"DemoPass2026"}'
TOKEN=$(curl -s -X POST $API/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"demo.student@pes.edu","password":"DemoPass2026"}' | jq -r .access_token)
H="Authorization: Bearer $TOKEN"

# Profile and three skills, typed loosely on purpose (aliases resolve)
curl -s -X POST $API/profile -H "$H" -H 'Content-Type: application/json' -d '{"name":"Demo"}'
for s in 'python3 intermediate' 'sql beginner' 'docker beginner'; do
  set -- $s
  curl -s -X POST $API/profile/skills -H "$H" -H 'Content-Type: application/json' \
    -d "{\"skill\":\"$1\",\"level\":\"$2\"}"
done
curl -s $API/profile/skill-vector -H "$H" | jq

# Target role (Backend Developer's id from the seed)
ROLE=$(docker compose exec -T upskill-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
  "SELECT role_id FROM career_role WHERE role_name = '"'"'Backend Developer'"'"'"')
curl -s -X PUT $API/profile/target-role -H "$H" -H 'Content-Type: application/json' \
  -d "{\"role_id\":$ROLE}" | jq

# Gap and roadmap
curl -s $API/roadmap/gap -H "$H" | jq
curl -s $API/roadmap -H "$H" | jq '.items[] | {rank, skill_name, resources: [.resources[].title]}'
```

## 3. What to see

| Step | Expected |
|---|---|
| Skill vector | Python intermediate, SQL Basics beginner, Docker & Containerization beginner |
| Target role | Backend Developer: `required` 5, `held` 3, `gap` 2 |
| Gap | 1 REST API Design (intermediate, none held), 2 Unit Testing (beginner, none held) |
| Roadmap | At least one approved resource under each gap skill |

Then raise a skill (for example `{"skill":"Unit Testing","level":"beginner"}`) and call
`/roadmap` again: Unit Testing drops out, because the gap is recomputed from the current
vector on every request.

In the browser, the same flow is `/` (register and log in), `/profile`, then `/roadmap`
on http://localhost:3000.
