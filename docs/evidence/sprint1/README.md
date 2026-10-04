# Sprint 1 evidence manifest

All files are from real local Jenkins/SonarQube runs. No credentials or local
bootstrap files are included. These files have not been uploaded to GitHub.
Trailing whitespace on timestamp-only console lines was removed for Git hygiene.

The latest successful verification is under `linux-final/`. It tests feature
`0bf7aae` combined with updated main `83af45e`, with 14 passed, 6 expected
failures, 76% pytest coverage, 68.0% SonarQube source coverage and gate OK.
The exact Jenkinsfile executed from a local-only SCM validation merge; this
does not prove automatic GitHub triggering or required-check enforcement.
The Jenkins image also built cleanly on the independent Ubuntu Docker Engine.
The older files below are retained as historical evidence, not current metrics.

| Prefix | What the saved files prove |
|---|---|
| `pr4-manual-retry-*` | Completed successful Jenkins PR-merge build 3, console, 14-test JUnit report, and 89% pytest coverage report |
| `pr4-sonar-*` | Normal project gate OK; overall SonarQube coverage 77.1% and one reported vulnerability; not a zero-issues claim |
| `gate-demo-sonar-*` | Separate demo project gate ERROR because coverage 77.1% is below the deliberate 100% threshold |
| `gate-demo-verified-excerpt.md` | Actual Jenkins build 2 completed FAILURE specifically because the quality gate returned ERROR |
| `gate-demo-build.json`, `gate-demo-console.log` | Earlier build-2 snapshots, saved before completion; not final result evidence |
| `pr4-automatic-*` | Fresh automatically scheduled PR build 1, BranchIndexingCause; saved snapshot was queued, not completed |

The automatic job is `UpSkill-Sprint1-Automatic-Verified/PR-4`. Later live
inspection showed Ruff and 14 tests passed and analysis started, but no final
result was obtained before Docker failed again. Do not claim this run succeeded.

The tested PR head is `b0efee07999f102a1a53a3529e4c5330fcbc0f52` and main is
`b2c33fb2f0c586729a5d1673dfe8d8f77abb4fff`. Jenkins creates local merge commits;
the manual retry analyzed `2ba174cc6a004bd637368a048bba27382895d9ba`, and the
demo analyzed `3ee0584e8f030285295d9f25435d54d9dc4b339e`.

These are Sprint 1 checks of the shared PR merge revision, not full-system or
completed M3 feature tests. The newer unpushed CI changes are not represented
as a remotely tested revision. Clean-image rebuild remains unverified due to
plugin-download failures. Full console/artifact export should be repeated when
Docker recovers; retain these files as evidence of the observations to date.
