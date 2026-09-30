# UpSkill-AI

An AI-powered upskilling recommendation and automation system for students.
UE24CS341A Software Engineering, Team 18, Project ID 22.

| Member | SRN | Module |
|---|---|---|
| Vansh Sharma | PES2UG24AM179 | M1 Profile & Skill Extraction |
| Yajat Soni | PES2UG24AM185 | M2 Gap Analysis & Roadmap |
| Hemanth Kumar R | PES2UG24AM202 | M3 Progress & Adaptive Adjustment |
| Shubhika Pradeep | PES2UG24AM157 | M4 Catalogue, Auth & RBAC |

Stack: Next.js (TypeScript), FastAPI (Python 3.12), PostgreSQL 16, SQLAlchemy + Alembic, pytest, Jenkins, SonarQube, Docker Compose.

## Repository layout

The layout mirrors module boundaries, so a cross-module import shows up in review as a path crossing a top-level folder.

| Path | Contents | Owner |
|---|---|---|
| `backend/profile/`, `backend/skills/`, `backend/taxonomy/resolver.py` | M1 | Vansh |
| `backend/gap/`, `backend/recommendations/` | M2 | Yajat |
| `backend/progress/`, `backend/evidence/`, `backend/dashboard/` | M3 | Hemanth |
| `backend/auth/`, `backend/catalogue/`, `backend/audit/` | M4 | Shubhika |
| `backend/shared/` | Skill vector type, level enum, shared exceptions. Changes need all four to agree | All |
| `backend/migrations/` | Alembic migrations | Shubhika |
| `frontend/` | Next.js app, one route group per module | Per module |
| `docs/` | SRS, architecture, backlog, test plan, work allocation, frozen contracts | Vansh |
| `docker-compose.yml`, `Jenkinsfile` | Infrastructure | Shubhika / Hemanth |

## Module interaction rules

- **R1** A module calls another only through its published service interface.
- **R2** No module imports another module's repository, model or internal helper.
- **R3** The skill vector format and taxonomy schema are frozen. Changing either needs all four owners.
- **R4** M1 is the only writer of the skill vector. M3 calls `apply_vector_update()`.
- **R5** M4 is the only writer of catalogue and user records.
- **R6** Only M4 calls the external YouTube API.

## Branch and pull request rules

- Branch name: `feature/<module>-<story-id>-<short-slug>`, e.g. `feature/m1-up6-resume-upload`.
- `main` is protected. No direct pushes, by anyone.
- Every PR needs one approving review from a member who does not own that module.
- CI must be green before merge.
- Commit messages say what changed and reference the story ID.
- Every member commits in every sprint.

Review pairs: Vansh → Yajat, Yajat → Hemanth, Hemanth → Shubhika, Shubhika → Vansh (author → reviewer).

## Frozen contracts

Full copies live in [docs/CONTRACTS.md](docs/CONTRACTS.md). Status: **final and frozen** (UA-6). Changes need all four owners.

- Skill vector format
- Skill taxonomy schema
- Resource tagging schema

## Definition of Done

Acceptance criteria met and demonstrated; reviewed PR merged to `main`; unit tests passing in CI; linked test cases passing; SonarQube gate passed; no cross-module internal imports; no unilateral contract change; requirement IDs genuinely satisfied.

## M3 implementation handoff

M3 progress tracking, completion evidence, dashboard, adaptive update triggers,
and the M3 frontend slice are implemented in this feature branch. M3-local
enums, ports, errors, unavailable integration adapters, and the temporary
student identity dependency live under `backend/progress/`; frozen
`backend/shared/` files and contracts are not modified.

For local checks, install `requirements-dev.txt`, then run
`ruff check backend tests` and `pytest --cov=backend --cov-report=term-missing`.
In `frontend/`, run `npm ci`, `npm test`, `npm run lint`, and `npm run build`.
Copy `.env.example` to `.env` and replace the database placeholders for local
use; never commit `.env`.

See [docs/M3_INTEGRATION_CONTRACTS.md](docs/M3_INTEGRATION_CONTRACTS.md) for
the temporary M1/M2/M4 adapters and unresolved contract alignment items. No
Jenkins, SonarQube, or full-system test result is claimed by this local run.
