# Continuous integration (UA-3, UA-4)

Every pull request and every push to `main` runs the repository's `Jenkinsfile`
on a fresh **Jenkins LTS** server with its own **SonarQube**, and so does a
weekly scheduled run on `main` (Mondays, 08:47 IST) that catches breakage from
new dependency releases or removed images before a PR does. The result is
reported on the pull request as the **`Jenkins pipeline`** check, and `main`
only accepts a merge when that check passes.

## How it runs

There is no long-running team server to keep alive. For each run, GitHub
Actions (free for this public repository) provides a machine, and
`ci/run-pipeline.sh` on it:

1. Starts SonarQube (the same pinned image as `ci/compose.yml`), sets a random
   admin password, generates an analysis token and creates the **UpSkill CI**
   quality gate.
2. Builds the Jenkins image from `ci/jenkins/` and starts it with
   `ci/jenkins/casc.yaml` (Jenkins configuration as code): local CI user,
   SonarQube server `SonarQube`, scanner tool `SonarScanner`, and the
   `upskill-ai` pipeline job pointing at the commit under test.
3. Triggers the job, streams its console output into the Actions log, and exits
   with the Jenkins build result.
4. Saves the Jenkins console log, the archived reports and the SonarQube gate,
   measures and issues to `ci-out/`, uploaded as the run's
   `jenkins-build-<n>` artifact (kept 30 days). That artifact is the evidence
   for any given build.

All credentials are generated per run and disappear with the machine; nothing
secret is stored in the repository or in GitHub settings.

## Pipeline stages (Jenkinsfile)

| Stage | What it does | Fails the build when |
|---|---|---|
| Checkout | Checks out the exact commit | |
| Backend checks | Fresh Python 3.12 venv (`uv`), installs requirements, `ruff check backend`, `pytest` with coverage. Database tests run against a throwaway Postgres 16 started for the build, migrated with Alembic | Lint error, failing test, no tests collected, wrong Python |
| SonarQube analysis | Scans `backend/`; test files are classified as tests | Scanner error |
| Quality gate | Polls SonarQube until the analysis is processed, then reads the gate (no webhook needed) | Gate is not OK |
| Docker build | Builds the API and web images | Image build error |
| Deploy smoke test | Starts the whole compose stack with throwaway secrets, no host ports and its own volume (`ci/compose.smoke.yml`), checks `GET /api/v1/health` returns `{"status": "ok"}`, Postgres is ready and the schema is migrated to head, then removes it | Stack does not start or is unhealthy |

The two Docker stages run only when the Jenkins agent can reach a Docker
daemon. A Jenkins without one (for example the interactive local server from
`ci/compose.yml`) skips them with a message.

## Jenkins plugins

The CI Jenkins image installs an exact, checksummed plugin set and never
contacts `updates.jenkins.io`, so an outage of Jenkins' update service (as on
19 October 2026) does not break pull request checks.

| File | Purpose |
|---|---|
| `ci/jenkins/plugins.txt` | The plugins we choose, with versions, and the Jenkins core version |
| `ci/jenkins/plugins.lock` | Generated: every plugin including dependencies, with version, Maven group and SHA-256 |
| `ci/jenkins/lock-plugins.py` | Regenerates the lock from `plugins.txt`, reading only download mirrors and plugin manifests |
| `ci/jenkins/install-plugins.sh` | Image build step: downloads each locked file from Jenkins' Maven repository or a mirror and rejects any checksum mismatch |

To add or upgrade a plugin, edit `plugins.txt`, run `ci/jenkins/lock-plugins.py`,
and commit both files. When changing the Jenkins base image, update the
`jenkins-core` line too, so dependencies are resolved for that core.

## Quality gate: UpSkill CI

A fresh SonarQube has no history, so the built-in gate, which only checks
*new* code, would always pass. **UpSkill CI** checks overall code:

| Condition | Fails when |
|---|---|
| Coverage | below 60% |
| Reliability rating | worse than A (any bug) |
| Security rating | worse than A (any vulnerability) |
| Maintainability rating | worse than A |

The 60% coverage threshold is a starting point that the current code passes.
Raise it in `ci/run-pipeline.sh` once more modules have landed; changing it
affects everyone, so agree it as a team.

## Running it yourself

```
ci/run-pipeline.sh                   # with Docker
DOCKER=podman ci/run-pipeline.sh     # with Podman
CI_KEEP=1 ci/run-pipeline.sh         # keep Jenkins and SonarQube running afterwards
```

It needs about 4 GB of free memory. The Docker stages need the daemon socket
(`/var/run/docker.sock`, or set `DOCKER_SOCK`, for example to the Podman user
socket). Reports go to `ci-out/` (gitignored).

## Database tests locally

Tests that need Postgres use the fixtures in `backend/conftest.py` and are
skipped unless `TEST_DATABASE_URL` is set. The database is dropped and rebuilt
from the migrations, so its name must contain `test`:

```
docker run -d --name upskill-test-db -p 127.0.0.1:55433:5432 \
  -e POSTGRES_USER=upskill -e POSTGRES_PASSWORD=test -e POSTGRES_DB=upskill_test postgres:16-alpine
TEST_DATABASE_URL=postgresql://upskill:test@127.0.0.1:55433/upskill_test pytest
```

## Interactive local server

`ci/compose.yml` still starts a long-running Jenkins and SonarQube on
`localhost` for exploring the UI; see `docs/SPRINT1_CI_EVIDENCE.md`. It is not
needed for pull request checks.
