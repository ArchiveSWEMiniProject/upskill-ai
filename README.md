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

## Sprint 1 CI setup

For UA-3, Jenkins checks out the repository, creates a Python virtual environment,
installs `requirements-dev.txt` (and `requirements.txt` when present), and runs
Ruff against `backend/` and pytest with coverage. Tests are discovered alongside
their modules inside `backend/`. Test failures and zero collected tests fail the
build; test and coverage reports are published/archived even after failure.

Use a Unix Jenkins agent with Python 3.12, the Python venv module, and
`sonar-scanner` on PATH. Install the Jenkins JUnit and SonarQube Scanner plugins.
Configure a multibranch Pipeline job for this repository with PR discovery and
the repository webhook so PR updates trigger a build.

For UA-4, configure the Jenkins SonarQube installation as `SonarQube`, with its
server URL and token supplied through Jenkins configuration/credentials. On
SonarQube, configure a webhook to `<Jenkins URL>/sonarqube-webhook/` (including
the trailing slash) so Jenkins can receive the analysis completion event. The
pipeline fails if the quality gate is not OK or the wait times out.

Actual Jenkins and SonarQube execution remains unverified. UA-3/UA-4 completion
requires real evidence of a PR-triggered build and a deliberate violation that
fails the configured quality gate. No server credentials belong in this repo.

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
