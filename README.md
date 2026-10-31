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

Every pull request and every push to `main` runs the `Jenkinsfile` on a fresh
Jenkins LTS server with its own SonarQube (GitHub Actions provides the machine).
The stages are lint, unit tests with coverage, SonarQube analysis and quality
gate, Docker image build, and a deploy smoke test of the full compose stack.
The result is the **Jenkins pipeline** check on the pull request, and `main`
only accepts a merge with that check green and one approving review.

Details, the quality gate, and how to run it yourself: [docs/CI.md](docs/CI.md).
The interactive local Jenkins and SonarQube from `ci/compose.yml`, and the
Sprint 1 verification evidence, are described in
[docs/SPRINT1_CI_EVIDENCE.md](docs/SPRINT1_CI_EVIDENCE.md).

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

## Seed data

Load after `alembic upgrade head`, the taxonomy before the catalogue. Every file is safe to run again.

```
psql "$DATABASE_URL" -f taxonomy_seed.sql            # then any other taxonomy_seed_*.sql
psql "$DATABASE_URL" -f catalogue_seed.sql           # then any other catalogue_seed_*.sql
```

The seed tests load them all into the migrated test database on every CI run.

## Frozen contracts

Full copies live in [docs/CONTRACTS.md](docs/CONTRACTS.md). Status: **final and frozen** (UA-6). Changes need all four owners.

- Skill vector format
- Skill taxonomy schema
- Resource tagging schema

## Definition of Done

Acceptance criteria met and demonstrated; reviewed PR merged to `main`; unit tests passing in CI; linked test cases passing; SonarQube gate passed; no cross-module internal imports; no unilateral contract change; requirement IDs genuinely satisfied.
