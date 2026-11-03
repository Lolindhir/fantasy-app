# G5 — League Live early-exit feasibility and job-level evidence (2026-11-03)

**Owner:** [Issue #1263](https://github.com/Lolindhir/fantasy-app/issues/1263), G5. **Mode:** read-only code, run, job and billing-policy investigation; no production guard or schedule activation. This is a bounded follow-up to the [30-day dispatch/no-op baseline](2026-11-03-g5-github-actions-volume-and-noop-baseline.md), **not** a claim that a skip is safe today.

## Exact observed job evidence

GitHub Actions [League Live run #41389288792](https://github.com/Lolindhir/fantasy-app/actions/runs/41389288792), 2026-11-02 UTC, was a successful **no-op in its final App publisher**, not necessarily in every upstream source. The [job API](https://api.github.com/repos/Lolindhir/fantasy-app/actions/runs/41389288792/jobs?per_page=100) reports:

| Executed job | UTC start–finish | Job elapsed |
| --- | --- | ---: |
| `source / validate` | 04:37:39–04:38:21 | 42 s |
| `source / sync` | 04:38:23–04:39:14 | 51 s |
| `standings` | 04:39:16–04:39:58 | 42 s |
| `league` | 04:40:00–04:41:34 | 94 s |
| **Total executed job elapsed** | sequential jobs | **229 s** |

The skipped `historical_preflight` job is not included. **136/229 s (59.4%)** of *executed job elapsed* sit in the two post-source jobs. This is one observed run, **not** an average or a guaranteed saving: a guard itself costs time, skipped jobs need correctness proof, and workflow queue/orchestration time is excluded. The timing API reports 387,000 ms of *run duration*, which must not be substituted for the 229 s of job execution.

Specific log findings: `source / sync` printed `CanonicalFilesChanged: 0` and `No canonical League data-source changes detected.`; `standings` printed `No changes - update skipped` and `Generator produced no repository changes. Nothing to publish.`; `league` printed `AppChanged: false`, `DerivedChanged: false`, `TeamCapOutlook unchanged` and `Generator produced no repository changes. Nothing to publish.` Thus **all three publishing stages were observed as no-op for this run** (the source can still have fetched provider evidence). By contrast [run #41369471490](https://github.com/Lolindhir/fantasy-app/actions/runs/41369471490) published changes. Do not project this sample's outcome onto all League Live runs.

Important overhead: the `standings` job's actual Python rebuild step took only about four seconds in the example; most of its ~42 s job elapsed involved runner setup and repository checkout. The final `league` job also checked out the repository and restored Node's cache before executing its producer chain. Avoiding a job **entirely** can save more than speeding up its generator, but only if the skip is correct.

## Existing-first runtime and ownership trace

- [`.github/workflows/league-live.yml`](../../../.github/workflows/league-live.yml): `source` (reusable `sync-league-source-data.yml`, `current`), then always `standings`, then always `league`. `concurrency.group=league-live`, `cancel-in-progress=false`.
- [`.github/workflows/sync-league-source-data.yml`](../../../.github/workflows/sync-league-source-data.yml) performs a scope-specific provider fetch, raw and canonical publication with rebuild-on-race and a **second-pass semantic no-op validation**. Its `validate` job runs the four current-scope unit-test modules and validates the source registry on *every* tick. These are separate concerns: removing runtime tests is not equivalent to removing essential input validation.
- `standings` calls `tools/league_standings_app_publish.py write`. Its derived season/week basis can change from **NFL game finality independently of League Source**, exactly as the workflow comment explains.
- `league` calls, in order, `tools/league_live_derived_refresh.py`, `tools/player_week_fantasy_refresh.py`, `tools/matchup_context_app_publish.py`, `tools/league_history_app_publish.py`, `tools/weekly_recaps_app_publish.py`, `RequestLeaguePublication.ps1`, and `tools/team_cap_outlook_app_publish.py`. The refresh covers current-season Transactions/Drafts and newest-scored-week TeamWeekPerformance; historical corrections retain independent weekly coverage.
- `tools/league_lifecycle.py` and `tools/decision_windows.py` each resolve with an explicit `AtUtc` (default **current time**). Consequently the same committed source blobs can legitimately produce changed outputs at a kickoff, waiver/lifecycle boundary, or week rollover. `NextWaiverRun` is a concrete clock-dependent App field.
- Other upstream facts and inputs come from NFL schedule/finality, ESPN injury availability, NFL Games odds/market, PlayerWeekFantasy, shared derived products, model selection/metadata and published app dependencies. `public/data/Timestamps.json` stores *semantic publication times*, not a proof that every dependency was freshly checked.
- Existing [`tools/audit_workflow_job_costs.py`](../../../tools/audit_workflow_job_costs.py) (PR #1295) already owns read-only exact run census and sampled **job-time** estimation. Do not create a competing job-cost collector or confuse job elapsed with billing.

## Early-exit decision: NOT YET SAFE

**Provider acquisition must still occur** to determine whether current League facts have changed; a GitHub-only precheck cannot infer an unobserved Sleeper roster, transaction, draft or matchup update.

After successful source publication, a future **shadow-only** (no-skipping) decision could evaluate whether all required *downstream* inputs and temporal boundaries are already satisfied by the most recently validated outputs. It must be per-product or per-stage: `standings` and `league` do **not** share the same dependency set. The existing `main_before_sync` output is useful for correlation but **not** alone a sound freshness cursor, because unrelated writers advance main and a previous target may have failed, been cancelled, or never published.

Required conservative decision (illustrative, not runnable policy):

| Condition | Required action |
| --- | --- |
| Source sync failed, missing/inconsistent input, unknown prior completion or concurrent main change not reconciled | Fail/keep existing safety path; **never** classify as a safe skip |
| Canonical League input changes (league/roster/matchup/draft/transaction/week) | Run affected producers/consumers |
| NFL finality-only change, LeagueScoredWeek change, official score/finality correction | Recompute Standings and affected downstream products even if League Source unchanged |
| NFL schedule/odds/injury/scoring/PlayerWeekFantasy/model/metadata/salary/cap witness changes | Recompute the affected App/Derived consumers as applicable; Standings need not be invalidated by unrelated inputs |
| Temporal boundary (kickoff/lock/waiver/lifecycle/week rollover), or temporal coverage unknown | Run the clock-dependent consumers |
| Prior fail-soft stale product, incomplete/warned run, retry/race/catch-up, missing derived/App artifact, or old-week correction needing independent weekly repair | Do not record a globally clean skip; retain proper producer and recovery ownership |
| All owned dependencies, selected model versions, persisted output validity, last successful processing and temporal window demonstrably unchanged | **Candidate** for an individual downstream skip, subject to negative regressions and shadow parity |

**Do not implement** a one-hash League Source shortcut, a blanket `standings: if source changed`, a time-agnostic commit-diff gate, or a new isolated state branch/writer merely to support caching. Reuse existing source/version and target-product contracts if a guard is subsequently justified.

## Cost and billing interpretation

The [GitHub timing endpoint](https://api.github.com/repos/Lolindhir/fantasy-app/actions/runs/41389288792/timing) reports `billable.UBUNTU.total_ms=0` for sampled runs **#41389288792, #41369471490, #41464554365, #41540883952**. GitHub repository metadata reports `visibility=public`; the observed jobs are ordinary `ubuntu-latest` runners. [GitHub's current billing documentation](https://docs.github.com/en/actions/concepts/billing-and-usage) and [2026 pricing change announcement](https://github.blog/changelog/2026-01-01-reduced-pricing-for-github-hosted-runners-usage/) confirm that *standard GitHub-hosted Actions runners in public repositories are free*. Therefore the measured examples support **zero direct billable runner charge in the current public-standard-runner configuration**. They do **not** measure future private-repository usage, larger runners, storage, other compute or any future billing-policy change. The 30-day aggregated **run wall time** remains unsuitable for pricing.

## Acceptance design for a future shadow gate (not implemented here)

1. **Producer/consumer dependency inventory** at field/product granularity with league, season, week, model/profile identity, source revision and valid-time interval. Reuse canonical source/derived owners; distinguish source no-op from derived/App no-op.
2. **Read-only decision trail:** for sampled successful runs, emit `would-run`/`would-skip` and exact reason **without skipping**; compare each shadow decision to the actual downstream publish/no-op result and consumer validity. No unobserved future provider change may be treated as unchanged.
3. **Fail-closed negative cases:** NFL-finality-only and official-score correction; week/LineupWeek rollover; waiver and kickoff boundaries; injury/odds/market updates; salary/model switch; current vs corrected older TWP/WeeklyRecaps; missing output, fail-soft warnings, failed source, retry and main race, delayed/missed tick and manual repair. Include multi-league/multi-season identities.
4. **Run-level before/after evidence:** job execution seconds, queue, success/failure, source/derived/App freshness and missed invalidations; no billing inference from elapsed time. Only after no false-skip cases and positive reduction evidence should an actual workflow gate be separately evaluated with existing rebuild-and-retry, monitoring and CI Fast/Deep intact.

**Decision at this checkpoint:** **No live Early Exit yet.** The measured opportunity is real (136 s of downstream runner job elapsed in one entirely no-op observed example), but sound invalidation and temporal-cursor evidence is missing. Next *bounded* action should be a shadow evaluator/negative-fixture experiment in the existing test/tooling architecture—not premature removal of jobs/schedules. No files under `.github/workflows`, `data-source`, `data-derived`, `data-meta`, `public/data`, or runtime tools were changed for this report.
