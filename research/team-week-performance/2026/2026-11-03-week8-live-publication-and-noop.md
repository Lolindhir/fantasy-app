# TeamWeekPerformance — Week-8 publication and real League Live no-op evidence (2026-11-03)

**Scope:** G1/G6 historical operational evidence for [Issue #1263](https://github.com/Lolindhir/fantasy-app/issues/1263), read-only inspection of existing Git commits and GitHub Actions logs. This is not a complete proof of historical correction replay or a new runtime policy.

## Scored-week transition and cross-consumer delivery

| Event | CET | Main commit |
| --- | --- | --- |
| Fix to source-side scored-week targeting | before data change | [359fdcc](https://github.com/Lolindhir/fantasy-app/commit/359fdcc7a9f4f168a031be198c0b173fbea09543) |
| Canonical league season score-watermark advanced | 12:04:06 | [4bf306a](https://github.com/Lolindhir/fantasy-app/commit/4bf306a891d6f140d342c1737898ecd866cb3f97) |
| Current TWP Week-08 partition + WeeklyRecaps published in one League Live commit | 12:06:32 | [55edf14](https://github.com/Lolindhir/fantasy-app/commit/55edf142ae0921b53811efd45b595cc0de9de499) |

Canonical `data-source/leagues/nfl-reise/seasons/2026/league.json` `WeekStructure.LastScoredLeg` changed **7→8** (prior blob `e72f4162ac775fc2df8a4387d1754d124c25eefe`; new blob `05189fca5284b8d51bead102137f22f0bc3430f1`). The Week-08 `data-derived/team-week-performance/nfl-reise/2026/08.json` partition **did not exist** at the watermark-commit ref and was created by `55edf14` (blob `82c308f60f446e5517753f910a43bc99f03c6aad`). At the same commit, `public/data/WeeklyRecaps.json` changed from blob `3d0d164914525e603c07bd166a70ad30980a129b` (weeks **1–7**) to `2796bb14e595511dc1a118fb6b9d473ae6c8e19b` (weeks **1–8**, Week-8 `TeamAwards.State=available`). All six Week-8 teams are represented and the awards are the published TWP winner rosters. The canonical watermarked Source→TWP/Recaps commit interval was **146 s**.

This demonstrates initial completed-week publication. The code-path report at `research/team-week-performance/2026/2026-11-03-source-derived-consumer-snapshot.md` separately checks all eight finalized weeks (48 official team score and 16 award-set comparisons). It does **not** show correction-driven invalidation of an existing published Week-8 partition.

## Observed two successful no-op League Live runs

| Workflow run | Started UTC | Completed (approx., UTC) | Run wall time | Job evidence |
| --- | --- | --- | --- | --- |
| [#41673527838](https://github.com/Lolindhir/fantasy-app/actions/runs/41673527838) | 16:22:27 | 16:28:52 | **6 min 25 s** | [league job 126050639329](https://github.com/Lolindhir/fantasy-app/actions/runs/41673527838/job/126050639329) |
| [#41675394726](https://github.com/Lolindhir/fantasy-app/actions/runs/41675394726) | 16:33:22 | 16:46:30 | **13 min 08 s** | [league job 126060726250](https://github.com/Lolindhir/fantasy-app/actions/runs/41675394726/job/126060726250) |

Both complete workflow runs are `completed/success`. Both respective League publisher job logs end with **`Generator produced no repository changes. Nothing to publish.`**, with `MatchupProjections.Changed=false`, unchanged Shared Derived history entries and multiple App writers reporting skipped unchanged files. Hence these executions did **not** make an unnecessary repository data commit. The durations are **end-to-end run wall times from Actions run_started_at/updated_at**, not measured CPU seconds or GitHub billed minutes, and may include orchestration and waiting. A semantic no-op does not mean cost-free execution.

The later [League Live run #41677851701](https://github.com/Lolindhir/fantasy-app/actions/runs/41677851701) was instead a **changed-data** run, using a rebuild-after-race (attempt 2) and publishing `FantasyGameContext.json` after the latest NFL Games Derived revision; see the NFL Games report linked in this checkpoint.

## Open boundaries

- TWP's `FinalityEvidence` is a named canonical reference and `LineupDefinitionHash`/`ScoringProfile.SettingsHash` are stored fingerprints; the current `WeeklyRecaps` consumer validates presence and identity but does **not** recompute Source fingerprints on read. The League Live producer can retain a prior good partition when current TWP generation fails.
- The observed 7→8 publication and two no-op runs do **not** demonstrate a source-correction rollback/rebuild, stale-retention recovery, historical batch restoration, all-families consumer reachability, or a G5 billing baseline.
- Next evidence: a naturally occurring scored-week or correction transition compared with exact versioned Source/TWP/App blobs and job warnings; controlled negative Source mutations belong only in existing read-only temporary-root preflight/restore paths. No new writer or authorization should be inferred from this report.
