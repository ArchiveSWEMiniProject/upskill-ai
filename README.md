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

## Continuous integration

Every pull request and push to `main` starts a fresh Jenkins LTS server and
SonarQube on a GitHub-hosted runner. The workflow runs the repository's
`Jenkinsfile` and reports the `Jenkins pipeline` check required by branch
protection. No always-on laptop, external CI VM or temporary webhook tunnel is
needed for these checks.

The pipeline creates a Python 3.12 virtual environment with `uv`, installs the
requirements, runs Ruff and pytest with coverage, and checks the SonarQube gate.
Database tests use a disposable PostgreSQL 16 database rebuilt from the real
Alembic migrations. Docker-capable agents also build the API/web images and
smoke-test the deployed stack. Failing tests, zero collected tests and a failing
quality gate fail the build. Logs and reports are uploaded as workflow artifacts.

See [the current CI setup](docs/CI.md) for execution, gate conditions and local
testing. The optional interactive local servers and older Sprint 1 evidence are
documented in [the historical evidence checklist](docs/SPRINT1_CI_EVIDENCE.md);
their temporary PR-4-only setup is not the current PR-check infrastructure.
Credentials must never be committed.

## Sprint 2 reference data

See [the seed guide](docs/SPRINT2_SEEDS.md) for Hemanth's five taxonomy skills,
aliases/prerequisites and five catalogue resources, load order, idempotence and
real-database regression checks. These are personal contributions to shared
UA-7/UA-8 tasks, not a claim that the full team seed targets are complete.

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
