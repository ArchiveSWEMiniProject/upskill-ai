# UA-3 / UA-4 webhook verification

Actual server results captured on 2026-10-04. These are Sprint 1 CI checks, not
full-system or completed M3 functionality tests.

## Automatic build

`UpSkill-PR-Webhooks/PR-4/2` finished SUCCESS. The cause is `BranchEventCause`,
`Pull request #4 updated`, not UserIdCause or BranchIndexingCause. There is no
periodic scan trigger on this job. Initial setup indexing is not used as proof.

Pushed feature head: `2ba141ec476a3e1fac57c396c4a24c54158490a6`.
Base main: `83af45e69405326f6d1249aa2065fe3e679417eb`.
Jenkins built their merge using the committed Jenkinsfile. Console logs record
both source SHAs and Jenkins-generated merge SHAs.

`github-deliveries.json` contains GitHub's actual HTTP-200 delivery summaries.
`receiver-deliveries.jsonl` records the corresponding signature-validated events.
`github-commit-status.json` records Jenkins' actual successful
`continuous-integration/jenkins/pr-merge` status on the feature commit.
Build metadata, full console, JUnit, coverage and Sonar gate/metrics are saved
with the `automatic-` prefix.

Ruff passed; 14 pytest tests passed and 6 documented M2 stub tests xfailed.
Pytest coverage including tests: 76%; Sonar source coverage: 68.0%; gate: OK.

## Deliberate gate failure

`UpSkill-UA4-Gate-Demo/3` uses the same feature revision combined with main.
Ruff/tests/scanner succeed, then the separate `upskill-ai-ua4-demo` project's
100% source-coverage condition fails at 68.0%. Sonar's webhook returns ERROR and
Jenkins finishes FAILURE with `SonarQube quality gate failed: ERROR`.
The normal project's gate was not changed and no broken application code was
added. Actual final build/console/test/coverage/gate evidence has `gate-demo-`
prefixes. Demo build 2 failed on missing merge committer identity and is not
claimed as quality-gate evidence; that job-local configuration was corrected.

## Operational limits

The local receiver validates GitHub HMAC signatures and forwards only the
repository's webhook events. Public UI routes and unsigned requests are denied.
Jenkins and Sonar UIs are not exposed through the temporary Cloudflare tunnel.
Localhost build/status links cannot be opened on teammates' machines; share
these committed logs instead.

This verification job filters to PR #4. The temporary URL stops working when
the tunnel stops and changes on recreation. Before making the status mandatory
for all PRs, provision a stable team-hosted endpoint and configure discovery for
the intended PR set. No branch protection settings were changed here. The user
is handling protection, and shared seed execution is deferred.

Sources for the setup:
[Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
and [GitHub webhook signature validation](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries).
