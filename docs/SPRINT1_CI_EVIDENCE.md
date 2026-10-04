# UA-3 / UA-4 execution evidence

Status: successful real CI build and deliberate quality-gate failure verified.
The automatic-discovery success and final evidence export are still pending.
Saved API responses and logs live in `docs/evidence/sprint1/`; unfinished build
snapshots have `building: true` and must not be presented as completed runs.

## Observed execution (2026-10-04)

- Jenkins 2.580.1 and SonarQube Community Build 26.9.0.129388 started
  successfully on local Docker servers. The Jenkins agent used Python 3.13.5
  and SonarScanner 8.1.0.6389.
- PR #4 head `b0efee07999f102a1a53a3529e4c5330fcbc0f52` was tested as merge
  against main
  `b2c33fb2f0c586729a5d1673dfe8d8f77abb4fff`.
  Build 3's actual analyzed merge revision was
  `2ba174cc6a004bd637368a048bba27382895d9ba`, as recorded in its console log.
- `UpSkill-Sprint1/PR-4/3` finished SUCCESS: Ruff passed, 14 pytest tests
  passed, pytest coverage was 89%, analysis completed, and the SonarQube
  webhook delivered quality gate OK. This build was a manual retry after
  local plugin and server-credential configuration fixes; it is not proof
  of a successful automatically triggered build.
- Local build URL: http://localhost:8080/job/UpSkill-Sprint1/job/PR-4/3/.
  This URL is not reachable by teammates outside this machine. Pytest's 89%
  includes test code and must not be presented as SonarQube's coverage metric.
- `UpSkill-UA4-Gate-Demo/2` finished FAILURE specifically at the quality gate.
  Its tests and Ruff passed and the scanner completed successfully. SonarQube
  returned coverage 77.1%, below the separate demonstration gate's 100%
  threshold, and Jenkins reported `SonarQube quality gate failed: ERROR`.
  The demo analyzed revision `3ee0584e8f030285295d9f25435d54d9dc4b339e`.
  Local URL: http://localhost:8080/job/UpSkill-UA4-Gate-Demo/2/.
  This tests a deliberate policy violation, not an introduced source-code bug.
  The normal project gate was not changed.
- `UpSkill-Sprint1-Automatic-Verified/PR-4/1` was automatically scheduled by
  BranchIndexingCause after a fresh local folder scan. It passed 14 tests and
  Ruff, but its final analysis/gate result remains unverified. Earlier automatic
  and demo attempts failed due to startup/timeout issues, not gate violations.
- Jenkins and SonarQube HTTP requests subsequently timed out; Docker's
  container-list command also stopped responding. An authorized Docker restart
  recovered the services temporarily, but instability recurred. Final log
  export and automatic success verification await recovery. A clean rebuild
  of the latest Dockerfile was stopped after plugin-download requests stalled;
  clean-image reproducibility is not yet verified.
- The subsequent restart failed because Docker Desktop could not access its
  local inference-manager socket. A normal restart and process relaunch did
  not resolve it. No reset, volume deletion, application upgrade, or Windows
  reboot was performed. Local recovery is required before final verification.
- Local scanner execution was limited to `-Xmx384m -XX:ActiveProcessorCount=2`.
  The computer has about 7.4 GiB physical RAM, and Docker's VM has about 3.5 GiB
  shared with other applications. No unrelated project containers were removed.
- After the user's instruction to leave GitHub unchanged, local GitHub status
  listeners and periodic PR scans were disabled. No push, PR edit, branch
  protection change, or manual GitHub status update was made in this pass.
- The normal SonarQube project's recorded gate is OK, but its overall metrics
  include one vulnerability. Gate success is not a claim of zero issues or full
  security validation. Application-source remediation is outside this CI pass.
- PR discovery uses polling. No publicly reachable GitHub webhook has been
  configured. The SonarQube-to-Jenkins internal webhook worked in build 3.
- GitHub main had no branch protection when checked. The user assigned branch
  protection to Vansh; no protection settings were changed. The observed check
  context is `continuous-integration/jenkins/pr-merge`. Merge blocking is not
  verified.
- UA-7 shared-database execution remains pending: the shared migration folder
  contains only a placeholder. The Kickoff Plan assigns UA-5 shared schema work
  to Shubhika. No replacement taxonomy schema or fake migration was created.

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
4. Use a separate local demonstration job and SonarQube project/gate
   for a deliberate threshold violation. Keep lint and tests passing so the observed
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

- Automatically discovered PR build: tests/lint passed; final gate/result pending.
- SonarQube analysis and successful gate: build 3, archived console/API evidence.
- Deliberate quality-gate failure: verified demo build 2; captured final excerpt
  and SonarQube gate JSON saved, full final console export pending.
- Clean image rebuild: plugin-download network failure; not verified.
- PR attachment: pending user push/upload; no GitHub mutation authorized.
- GitHub required-check enforcement: left to Vansh, per user instruction.
- PostgreSQL seed execution and idempotence: pending shared schema availability.
