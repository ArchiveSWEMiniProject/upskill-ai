# UA-3 / UA-4 execution evidence

Status: real GitHub webhook-triggered PR build and deliberate quality-gate
failure verified on Linux Docker Engine. GitHub webhook configuration and
feature-branch pushes were subsequently authorized. Required-check merge
blocking remains a separate user-managed configuration.
Saved API responses and logs live in `docs/evidence/sprint1/`; unfinished build
snapshots have `building: true` and must not be presented as completed runs.

## GitHub webhook and gate-failure verification (2026-10-04)

- Pushed prepared feature revision `2ba141ec476a3e1fac57c396c4a24c54158490a6`
  to `feature/m3-sprint1-ci-foundation`; no push to main or PR merge.
- GitHub webhook 692060182 delivered genuine `push` and `pull_request`
  (`synchronize`) events with HTTP 200. Delivery IDs and timestamps are saved
  in `docs/evidence/sprint1/webhook-verified/github-deliveries.json`.
- `UpSkill-PR-Webhooks/PR-4/2` finished SUCCESS with `BranchEventCause`,
  description `Pull request #4 updated`. This is webhook-triggered execution,
  not a manual build or periodic scan. The initial discovery scan is excluded
  from successful automatic-trigger evidence.
- Jenkins tested that feature revision merged with main
  `83af45e69405326f6d1249aa2065fe3e679417eb`. Ruff passed; pytest reported
  14 passed and 6 documented expected failures, 76% coverage including tests.
  SonarQube source coverage was 68.0%; its webhook delivered gate OK.
- Jenkins published a real GitHub success status with context
  `continuous-integration/jenkins/pr-merge` on the pushed feature revision.
- `UpSkill-UA4-Gate-Demo/3` finished FAILURE specifically with
  `SonarQube quality gate failed: ERROR`. Its tests/lint and scanner passed;
  source coverage 68.0% violated the isolated demo project's 100% threshold.
  The ordinary project's gate was not changed and no application bug was added.
- Full console logs, completed build metadata, test/coverage reports and Sonar
  gate responses are in `docs/evidence/sprint1/webhook-verified/`.

Operational limits: the signature-validating webhook receiver uses a temporary
Cloudflare Quick Tunnel. It exposes only `/github-webhook/`, not Jenkins UI.
Its URL requires the local receiver, tunnel, Ubuntu Docker and Jenkins to remain
running and changes when the tunnel is recreated. Jenkins links containing
localhost are usable only on the host; repository evidence is shareable.
The multibranch verification job filters to PR #4, so it is not yet a
repository-wide always-on CI service. Before requiring its status for all PRs,
provide a stable team endpoint and enable discovery for the intended PR set.
Branch protection is now handled by the user; it was not changed in this pass.
UA-7 database execution is explicitly deferred by the user.

The sections below retain earlier results and restrictions for provenance;
their "unverified"/"not authorized" statements describe those earlier passes.

## Earlier Linux manual verification (2026-10-04)

- Installed official Docker Engine 29.8.2 and Compose 5.6.0 in the existing
  Ubuntu 24.04 WSL distribution. Docker Desktop's data was neither reset nor
  deleted; its startup problem was bypassed using an independent Linux engine.
- The committed Jenkins Dockerfile built successfully from its pinned base,
  including Python and all required plugins. Standard Jenkins mirror routing
  replaced the archive-server override because the archive route stalled.
  Built image: `sha256:cb7eea916656ffb012cabd797853af7c16d90ca7459d50dfc5e4fccdc5300791`.
- Feature revision: `0bf7aae04baecc41ce61a2135380e3a1872f3467`.
  Current main: `83af45e69405326f6d1249aa2065fe3e679417eb`.
  They merged without conflict into tree
  `f227b05d3f21ca512a1f550cbef01bbe211c4357`.
  A local-only validation commit, `13949879249b20b47f9412da39ef34998287cc4b`,
  contains that tree and both revisions as parents. Neither branch history nor
  GitHub was changed to create this temporary validation commit.
- `UpSkill-Final-Revision/1` executed the actual committed Jenkinsfile via SCM
  from a read-only local Git mirror and finished SUCCESS. It is a manual local
  validation, not evidence of a GitHub webhook or automatic PR trigger.
  Local URL: http://localhost:8080/job/UpSkill-Final-Revision/1/.
- Ruff passed. Pytest collected 20: 14 passed and 6 expected failures from M2's
  documented `compute_gap()` stub. JUnit reports zero errors/failures and six
  skipped/xfail cases. No tests or xfail markers were changed by this CI pass.
- Pytest coverage is 76% (including tests); SonarQube source coverage is 68.0%.
  The older run's 89% pytest / 77.1% Sonar coverage must not be substituted for
  these updated-main results.
- Sonar task `c4484096-2079-46dc-86c4-fe7f49a1d8f6` completed SUCCESS,
  its webhook delivered gate OK, and Jenkins archived JUnit/coverage reports.
  Full actual evidence is in `docs/evidence/sprint1/linux-final/`.
- Sonar reports one existing LOW security finding, rule `docker:S6471`, at
  `backend/Dockerfile:1`: the Python base runs as root. That shared M4-owned
  Dockerfile was not altered in this CI-only task. Gate OK is not zero issues.
- Runtime credentials, bootstrap files, local Git mirror, and keep-alive helper
  remain ignored under `.ci-local/`. No GitHub credential was configured on the
  new server. It does not publish GitHub statuses or configure webhooks.

This evidence records the tested code revision. Any later evidence/documentation
commit must retain that attribution; do not relabel this run as testing a later
commit. Final-HEAD rechecks can be exported separately without a self-referential
evidence commit.

## Earlier execution (2026-10-04; retained for provenance)

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

- Automatically discovered GitHub PR build: final gate/result pending; the
  latest successful Linux job is local/manual, not a substitute for this trigger.
- Latest pipeline, analysis and gate: verified Linux build 1; full evidence saved.
- Deliberate quality-gate failure: verified demo build 2; captured final excerpt
  and SonarQube gate JSON saved, full final console export pending.
- Clean image rebuild: verified with standard mirror routing on Linux Engine.
- PR attachment: pending user push/upload; no GitHub mutation authorized.
- GitHub required-check enforcement: left to Vansh, per user instruction.
- PostgreSQL seed execution and idempotence: pending shared schema availability.
