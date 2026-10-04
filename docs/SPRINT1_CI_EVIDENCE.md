# UA-3 / UA-4 execution evidence

Status: execution evidence pending. This file is a checklist, not proof of a run.

## Local servers

Run `docker compose -f ci/compose.yml up -d --build`. Jenkins is available at
http://localhost:8080 and SonarQube at http://localhost:9000. Both ports bind to
loopback only. Named volumes preserve configuration. SonarQube uses its embedded
database here for a local demonstration, not a production deployment.

Unlock Jenkins using its initial admin password from the container, create an
administrator account, and configure a managed SonarScanner installation named
`SonarScanner` under Manage Jenkins > Tools (enable automatic installation).
Add `SonarQube` under System with server URL `http://sonarqube:9000` and a token
stored in Jenkins credentials. Configure SonarQube's webhook as
`http://jenkins:8080/sonarqube-webhook/`. Change SonarQube's initial administrator
password at first login.

The SonarQube container requires the Docker Linux host to satisfy SonarQube's
Elasticsearch prerequisites, including vm.max_map_count of at least 524288.
If startup fails, inspect its logs rather than disabling bootstrap checks.
Configure GitHub PR discovery/polling to detect PR updates; a webhook requires
a Jenkins URL reachable by GitHub. A public tunnel is not configured here.

## Required runs

1. Configure a Jenkins multibranch Pipeline for this repository with GitHub PR
   discovery. Use a Unix agent with Python, venv, and sonar-scanner available.
2. Configure Jenkins's SonarQube installation named `SonarQube` with a server
   URL and a token held in Jenkins credentials. Configure SonarQube's webhook
   to the Jenkins URL ending in `/sonarqube-webhook/`.
3. Test a PR revision containing the backend tests from the shared repository.
   Record the PR number, revision, build URL, automatic trigger cause, console
   log, JUnit results, coverage XML, and SonarQube analysis/gate result.
4. Use an isolated demonstration branch and a separate SonarQube project/gate
   for a deliberate violation. Keep lint and tests passing so the observed
   failure is caused by the quality gate. Record the violated rule/threshold,
   SonarQube failed gate, and Jenkins failed build at the Quality gate stage.
5. Attach the actual logs/screenshots to PR #4. Do not include tokens, passwords,
   authorization headers, or the demonstration violation in the final branch.
6. Ask a repository administrator to make the Jenkins status a required check
   for main. Record the check name and branch-protection evidence; a failed
   Jenkins build alone does not establish that GitHub blocks merging.

## UA-7 validation

Run `taxonomy_seed_progress.sql` after the shared schema is available, using
the same PostgreSQL connection as the team seed. Run it twice to verify
idempotence, then query the five named skills and confirm five rows. This file
only inserts skills; it does not implement taxonomy tables or feature logic.

## Outstanding evidence

- PR-triggered Jenkins build: pending.
- SonarQube analysis and successful gate: pending.
- Deliberate quality-gate failure in Jenkins: pending.
- GitHub required-check enforcement: pending administrator verification.
- PostgreSQL seed execution and idempotence: pending shared schema availability.
