# Sprint 3 review (28 Oct to 10 Nov 2026)

Draft by Vansh, written 12 Nov 2026 from GitHub PR and CI data. The
"Team discussion" section is filled in at the retro meeting.

Sprint goal: first end-to-end demo (profile in, roadmap out) by Tue 10 Nov.

## Outcome

**The goal was not met.** The demo could not run on `main` by 10 Nov. The
journey needs a target role (#92) and the gap and roadmap endpoints (#87, #91),
and none of the three were merged by then.

## M1 (Vansh): 9 points planned

| Story | Pts | PR | State on 10 Nov |
|---|---|---|---|
| UP-11 Compute and expose the skill vector | 5 | #83 | Merged 3 Nov |
| UP-13 Select a target role | 3 | #92 (API), #94 (UI) | Open since 6 Nov, no approval |
| UP-10 Unresolved skills (reduced) | 1 | #93 | Open since 6 Nov, no approval |

Merged: **5 of 9 points**.

Sprint 2 carry-over merged during Sprint 3: UP-5 and UP-9 (#71), UP-1 (#80),
UP-3 (#74), UP-4 (#75), UP-6 (#81). Still open from Sprint 2: UP-7 and UP-8
(#95).

Other Sprint 3 items:

- **TC-F1-13 (M1 to M2 gap entries):**
  `test_tc_f1_13_gap_analysis_consumes_the_vector` passed in CI on `main` at
  `770f12c` (run 42609299271, 9 Nov: 296 passed, none skipped). Yajat still
  needs to sign off the M2 side.
- **STC-F1-01 walkthrough script:** written after the sprint ended, on 12 Nov
  (#101). It is executed in Hardening.
- **Shared and CI work merged in the sprint:** #8, #9, #11, #15, #16, #72, #73,
  #82.

## Team, by PR state on 10 Nov

| Module | Merged in Sprint 3 | Open |
|---|---|---|
| M1 Vansh | see above | #92, #93, #94, #95 |
| M2 Yajat | RM-1 `compute_gap()` (#84) | RM-3 (#87) and RM-4 (#91), both approved, not merged |
| M3 Hemanth | none | #88, #89, #90, #96 to #100 (most opened on 10 Nov) |
| M4 Shubhika | CA-4, CA-5, CA-11 (#77) | CA-6 (#85), changes requested |

## What blocked the demo

1. **Reviews:** four M1 PRs waited from 6 Nov with no review. Each of us has
   a fixed reviewer, and no time was set aside for reviewing.
2. **Approved but unmerged:** #87 and #91 were approved and still unmerged,
   and the roadmap end of the demo depends on them.
3. **Late PRs:** most of M3's PRs were opened on the last day of the sprint,
   too late to review.

## Proposed actions for Sprint 4

1. Merge in dependency order: #92, then #94, #93 and #95, then #87, then #91.
   Then run STC-F1-01 (#101) as the demo rehearsal.
2. Open the UP-12 PR now. Hemanth's PR-5 (#97) depends on
   `apply_vector_update()`, which is committed on
   `feature/m1-up12-vector-updates` with no PR yet.
3. Review within 24 hours of a PR opening. Raise any unreviewed PR at the next
   standup (the "blocker unmoved for 24 hours" rule).
4. Open PRs as each story is ready, not at the end of the sprint.

## Team discussion (fill in at the retro)

| | |
|---|---|
| Date, attendees | |
| What went well | |
| What did not | |
| Agreed actions and owners | |
| Measured velocity (points merged, whole team) | |
