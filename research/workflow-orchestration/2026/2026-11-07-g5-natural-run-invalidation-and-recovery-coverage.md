# G5 – Natural League Live cohort: real cross-writer invalidation and recovery limits

Date: **2026-11-07**. Parent: [Issue #1263](https://github.com/Lolindhir/fantasy-app/issues/1263). Scope: read-only empirical evidence, **not** a decision to modify or activate League Live. No manual rerun or job dispatch was performed.

## Nine contiguous successful ten-minute runs

Observed the actual native GitHub Actions run/job records and source/standings/league job logs (non-shell-echo messages, commit push lines). The study window spans the nine **completed** scheduled \`repository_dispatch\` League Live runs from **05:42 to 07:06 UTC** (06:42–08:06 CET), 2026-11-07.

| Run | Created UTC | Source canonical | Standings | League | Evidence |
| --- | --- | --- | --- | --- | --- |
| [42343876022](https://github.com/Lolindhir/fantasy-app/actions/runs/42343876022) | 05:42 | Raw + canonical pushed | No-op | Pushed | Source raw \`2d2d65e\`, canonical \`fc722e6\`, League \`5944bff\` |
| [42344538305](https://github.com/Lolindhir/fantasy-app/actions/runs/42344538305) | 05:52 | No-op | No-op | No-op | Every stage completed successfully; no writer commit |
| [42345225336](https://github.com/Lolindhir/fantasy-app/actions/runs/42345225336) | 06:02 | No-op | No-op | No-op | Every stage completed successfully; no writer commit |
| [42345972193](https://github.com/Lolindhir/fantasy-app/actions/runs/42345972193) | 06:12 | No-op | No-op | Pushed | League \`7ed1e32\` after separate NFL Games Derived writer |
| [42346720085](https://github.com/Lolindhir/fantasy-app/actions/runs/42346720085) | 06:22 | No-op | No-op | No-op | Every stage completed successfully; no writer commit |
| [42347468664](https://github.com/Lolindhir/fantasy-app/actions/runs/42347468664) | 06:32 | No-op | No-op | No-op | Every stage completed successfully; no writer commit |
| [42348187472](https://github.com/Lolindhir/fantasy-app/actions/runs/42348187472) | 06:42 | No-op | No-op | No-op | Every stage completed successfully; no writer commit |
| [42348879972](https://github.com/Lolindhir/fantasy-app/actions/runs/42348879972) | 06:52 | No-op | No-op | No-op | Every stage completed successfully; no writer commit |
| [42349568611](https://github.com/Lolindhir/fantasy-app/actions/runs/42349568611) | 07:02 | No-op | No-op | No-op | Every stage completed successfully; no writer commit |

**Observed counts:** Source publication 1/9; Standings publication 0/9; League publication **2/9**; seven complete Source/Standings/League no-op observations. These are one short morning sample, not a statistically established regular-season rate, and should never be generalized across game days.

### Measured job-time proxies

Rounded from native GitHub job \`started_at\`/\`completed_at\` for these nine completed runs:

| Stage | Total job elapsed over 9 runs | Mean elapsed per run |
| --- | ---: | ---: |
| Source sync | 512 s | 57 s |
| Standings | 445 s | 49 s |
| League | 868 s | 96 s |

The seven all-no-op runs consumed approximately **1,010 seconds** of Standings+League job elapsed time. This is an optimistic ceiling for a hypothetical *perfect, free and safe* stage-level early-exit oracle. It excludes orchestration, dependency proof, the preflight's own API/checkout cost and the mandatory absence-of-write / recovery logic, and it is **not a feasible/safe savings claim**. Source acquisition remains necessary for independent provider-freshness evidence.

## Real cross-writer invalidation: run #42345972193

The League Source sync completed at **06:13:42 UTC**, reporting **\`RawFilesChanged=0\`** and \`No canonical League data-source changes detected.\`. Standings completed a no-op at 06:14:34 UTC.

While the League job was running (**06:14:36–06:16:21 UTC**), a separate workflow published [\`a93cbe6d3d9efb86b8f274964183a39810093f1f\`](https://github.com/Lolindhir/fantasy-app/commit/a93cbe6d3d9efb86b8f274964183a39810093f1f), committed at **06:15:07 UTC**, changing \`data-derived/nfl-games/2026.json\`.

At 06:16:18 UTC, the League publisher logged **\`a93cbe6..7ed1e32 HEAD -> main\`**, followed by \`Rebuilt generated-data publish succeeded on attempt 1.\`. Its real output commit [\`7ed1e32b0bb67f719c0fd57bb60b223ff9a0a7ba\`](https://github.com/Lolindhir/fantasy-app/commit/7ed1e32b0bb67f719c0fd57bb60b223ff9a0a7ba) has the NFL Derived commit as its **exact Git parent**, and changed \`public/data/FantasyGameContext.json\` and \`public/data/Timestamps.json\`.

**Provable consequence:** A skip keyed only to unchanged Sleeper/League Source would have omitted a valid later League update. This is a concrete real-life failure mode for a naïve source-noop early exit, not merely a synthetic race test. The genealogy and timestamps prove the order and changed output paths, not the complete field-by-field causal mechanism; no provider polling or runtime alternate execution was performed.

**Other writers matter:** League Live's own concurrency group does not cover independent NFL-derived, odds, metadata or other publication families. Existing rebuild-and-retry publication protects against committing stale generated data; it does **not** make a preflight check-and-skip atomic. All two-point \`main\` observations are finite historical checks.

## Historical recovery coverage sampled at immutable commit

At the previously verified League publication commit \`5944bfff0e402b7ea5407133741aa6884470c7e5\`, examined directories for \`nfl-reise\`:

| Season | PlayerWeekFantasy partitions | TeamWeekPerformance partitions | Source League matchup partitions |
| --- | --- | --- | --- |
| 2024 | Week 01–17 | Week 01–17 | Week 01–18 |
| 2025 | Week 01–17 | Week 01–17 | Week 01–18 |
| 2026 | Week 01–09 | Week 01–08 | Week 01–18 |

The extra source Week 18 **is not evidence of missing derived output**: source partitions may include post-fantasy-season or unscored weeks. The current 2026 PWF Week 09 and TWP Week 08 reflect different current-vs-finalized product responsibilities, as reported in the actual League job. File presence and matching historical partition sets cannot prove byte/content parity with current Source, correction propagation, source completeness or that prior fail-soft recovery debts have been cleared. Do **not** mark \`recoveryClean=true\` from these observations.

The existing \`tools/historical_derived_orchestrate.py\` can run a read-only full historical preflight on a separate checkout; **this cohort check did not execute that preflight** or any provider-freshness request. Running such a full recomputation on every ten-minute tick would conflict with the user goal of minimal necessary work and would need separate cost/security review.

## Decision / bounded next work

| Question | Current disposition |
| --- | --- |
| Source unchanged → skip all downstream jobs? | **NO-GO.** Run #42345972193 is a direct counterexample. |
| Standings always no-op in sampled window → bypass it? | **NO-GO.** It depends on independent NFL game finality, which can advance outside League Source. |
| Prior successful League push/no-op → skip current League? | **NO-GO.** No complete fresh provider / clock / Derived recovery / published output parity attestation or atomic invalidation/requeue exists. |
| Current rebuild-and-retry publication | **Retain.** It reconciled the visible independent NFL Derived commit into the parent ancestry of the League output. |
| More efficient path | Prioritize measured **in-writer** / setup / dependency reuse optimizations over an expensive whole-job remote API precheck; preserve a full eligible generator pass for any changed NFL Derived or clock state. |
| Independent recovery closure | Requires separate read-only historical recomputation and source/derived parity assessment, not directory presence or green job status. |

**Risk/authorization boundary:** This evidence does not authorize new writers, persisted receipts, locks, requeue mechanisms or real stage/job skips. Each would require its own complete scoped impact/rollback assessment and explicit elevated-effect approval under the existing architecture rules. \`safeToSkip=false\`; \`raceFree=false\`; \`recoveryClean=false\`; no workflows or data were changed by the observation.

Rollback of this research-only checkpoint: revert its documentation commit. It has no production side effects.
