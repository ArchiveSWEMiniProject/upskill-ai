# Verified Jenkins gate-failure excerpt

Source: authenticated Jenkins consoleText response for
`UpSkill-UA4-Gate-Demo/2`, read on 2026-10-04 before Docker Desktop's startup
failure. This is a selected excerpt of the actual response, not a fabricated
run or a complete exported console log.

```text
[2026-10-04T12:07:25.452Z] 12:07:25.193 INFO  EXECUTION SUCCESS
[2026-10-04T12:07:33.052Z] Checking status of SonarQube task 'cf873ace-82c3-43af-a1e4-ffe5f6bd0f82' on server 'SonarQube'
[2026-10-04T12:07:33.754Z] SonarQube task 'cf873ace-82c3-43af-a1e4-ffe5f6bd0f82' status is 'IN_PROGRESS'
[2026-10-04T12:07:57.980Z] SonarQube task 'cf873ace-82c3-43af-a1e4-ffe5f6bd0f82' status is 'SUCCESS'
[2026-10-04T12:07:57.982Z] SonarQube task 'cf873ace-82c3-43af-a1e4-ffe5f6bd0f82' completed. Quality gate is 'ERROR'
[2026-10-04T12:08:02.412Z] Archiving artifacts
ERROR: SonarQube quality gate failed: ERROR
Finished: FAILURE
```

The same Jenkins response reported `building: false`, `number: 2`, and
`result: FAILURE`. The earlier saved `gate-demo-build.json` is a pre-completion
snapshot (`building: true`), not the final result. The saved SonarQube gate
response records actual coverage 77.1%, threshold 100%, comparator LT, ERROR.
The run's 14 tests and Ruff passed before analysis.
