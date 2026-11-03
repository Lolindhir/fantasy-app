# G5 — GitHub Actions volume, elapsed time and no-op baseline (observed 2026-11-03)

**Owner:** [Shared Data Platform Issue #1263](https://github.com/Lolindhir/fantasy-app/issues/1263), G5 workflow rationalization. **Mode:** read-only observation of actual GitHub Actions history; historical research, not scheduler policy or a new writer. All calendar dates below are **UTC**. This report does not authorize a runtime change.

## Method, boundaries and reproducibility

- GitHub REST `GET /repos/Lolindhir/fantasy-app/actions/runs` with `event=repository_dispatch` and `created=YYYY-MM-DDT00:00:00Z..YYYY-MM-DDT23:59:59Z`. The complete **2026-11-02** sample was paged at `per_page=100&page=1..9`, yielding **810/810** runs. For 30-day volume, fetch **each UTC date separately** with `per_page=1` and add daily `total_count`: a multi-day request here returned a capped `total_count=2500` and cannot be used as a true 7-/30-day total.
- Run status, workflow path, `run_started_at`, and `updated_at` came from the run listing. **Reported elapsed time = updated_at − run_started_at**, nonnegative, at observation time, including Actions-level orchestration and potential completion metadata delay. This is **not** billed runner duration, CPU time, queue delay, or Source→App SLA. The sum of per-run wall times is a concurrency-overlapping **aggregate**, not elapsed calendar time or a billable total.
- GitHub REST `/actions/runs/{run_id}/jobs?per_page=100` was used for a 12-run **League Live** and 12-run **Odds Refresh** evenly distributed sample across UTC Nov 2; the former also used specific final `league` job logs to classify the actual `rebuild_and_publish.py` result. Exact IDs below. These are **samples**, not a census of all 147 League Live / 144 Odds runs.
- `repository_dispatch` only: PR CI, push, workflow_dispatch, deployments, other events, GitHub Actions priced runner dimensions and GitHub billing exports are **excluded**. A workflow `success` result does **not** prove its generated data was refreshed or that individual jobs performed writes.
- Reproduction date 2026-11-03. The immutable day windows and run/job IDs are provenance. Run log retention and later API access may change.

## 24-hour complete dispatch census — 2026-11-02 UTC

All **810/810** repository_dispatch workflow runs finished with `conclusion=success`, with no concluded failures or cancellations in this window. The following figures measure workflow-run wall time, not runner-billed time.

| Workflow file | Runs | Median run elapsed | Aggregate run elapsed |
| --- | ---: | ---: | ---: |
| `scheduler.yml` | **288** | 1.68 min | **500.6 min** |
| `league-live.yml` | **147** | 4.30 min | **656.3 min** |
| `sync-nfl-player-availability.yml` | **144** | 0.82 min | **124.7 min** |
| `odds-refresh.yml` | **144** | 0.83 min | **156.0 min** |
| `nfl-live.yml` | **37** | 1.57 min | **82.3 min** |
| `workflow-health-snapshot.yml` | **31** | 1.80 min | **56.7 min** |
| `sync-project-fields.yml` | 12 | 0.33 min | — |
| `update-players.yml` | 3 | 1.75 min | — |
| `fm-daily.yml` | 1 | 2.77 min | — |
| `source-data-readiness.yml` | 1 | 5.83 min | — |
| `sync-league-source-data.yml` | 1 | 3.57 min | — |
| `sync-nfl-source-data.yml` | 1 | 19.45 min | — |
| **All 12 workflow paths** | **810** | — | **~1,620 min = 27.0 aggregate run-hours** |

The Scheduler plus League Live account for **435/810 (53.7%) dispatches** and **1,156.9/~1,620 (about 71.4%) of summed *run wall time***. League Live alone comprises ~40.5% of this summed measure. These ratios are **not** a cost or CPU breakdown.

Run volume aligns with the central 5-minute scheduler wake-up (288/day), ten-minute League Live (nominally 144/day; **147 observed**, extra dispatch cause not assigned), and ten-minute Odds + NFL Player Availability (144 each). Other workflows are state/window-gated or lower cadence. Canonical scheduler config: `.github/workflow-schedules.json`, single external scheduler entry `.github/workflows/scheduler.yml`, monitoring safety `.ai-context/manual/workflow-monitoring.yaml`.

Representative scheduler runs across day: [02:00 #41375421433](https://github.com/Lolindhir/fantasy-app/actions/runs/41375421433), [06:00 #41397321751](https://github.com/Lolindhir/fantasy-app/actions/runs/41397321751), [10:00 #41425314317](https://github.com/Lolindhir/fantasy-app/actions/runs/41425314317), [14:00 #41457977215](https://github.com/Lolindhir/fantasy-app/actions/runs/41457977215), [18:00 #41496524234](https://github.com/Lolindhir/fantasy-app/actions/runs/41496524234), [22:00 #41533519225](https://github.com/Lolindhir/fantasy-app/actions/runs/41533519225).

## 7-day and 30-day actual dispatch volume (daily-count API, no truncation)

Exact per-day counts (`repository_dispatch` only):

| UTC date | Oct 4–11 | Oct 12–19 | Oct 20–26 | Oct 27–Nov 2 |
| --- | --- | --- | --- | --- |
| Daily totals, in chronological order | **984, 1,154, 1,188, 1,307, 1,192, 1,150, 1,145, 765** | **574, 611, 607, 610, 641, 609, 672, 626** | **635, 613, 595, 645, 752, 815, 783** | **670, 754, 781, 738, 805, 829, 810** |

- **30 full UTC days, 2026-10-04 through 2026-11-02 inclusive:** **24,060** dispatch runs, average **802.0/day**.
- **7 full UTC days, 2026-10-27 through 2026-11-02:** **5,387** dispatch runs, average **769.6/day**.
- **Earliest seven-day block, Oct 4–10:** **8,120** runs. The latest seven days are **33.7% lower** than that starting block. This is a measured **event-count change**, **not** a causal attribution to a particular migration, source feed, NFL game window or code change.
- The Nov-2 810-run full census is one dated cross-section. The 30-day totals do **not** yet supply workflow-by-workflow run times, no-op rates, queue distributions or billable expenses for all 30 days.

## No-op and publication outcome samples — all on 2026-11-02 UTC

### League Live: 12 evenly spaced production runs, all successful

Sample workflow run IDs in chronological order:
`41369471490`, `41379157645`, `41389288792`, `41400548685`, `41415046077`, `41430963320`, `41446918057`, `41464554365`, `41485723646`, `41504674503`, `41523217744`, `41540883952`.

- **10/12** final `league` jobs explicitly log **`Generator produced no repository changes. Nothing to publish.`**. The other **2/12** report **`Rebuilt generated-data publish succeeded on attempt 1.`** (00:52 run [#41369471490](https://github.com/Lolindhir/fantasy-app/actions/runs/41369471490), final job `125037284257`; 02:42 run [#41379157645](https://github.com/Lolindhir/fantasy-app/actions/runs/41379157645), final job `125066582746`). The two changes are not attributed to any particular product without a separate commit diff.
- Concrete no-op examples: [04:35 #41389288792](https://github.com/Lolindhir/fantasy-app/actions/runs/41389288792) (final job `125098224820`), [08:42 #41415046077](https://github.com/Lolindhir/fantasy-app/actions/runs/41415046077) (final job `125177660278`), [14:42 #41464554365](https://github.com/Lolindhir/fantasy-app/actions/runs/41464554365) (final job `125343615923`), [22:52 #41540883952](https://github.com/Lolindhir/fantasy-app/actions/runs/41540883952) (final job `125605524432`).
- Every sampled League Live run has four **executed** successive jobs: `source / validate`, `source / sync`, `standings`, `league`; the `historical_preflight` job was skipped. In the samples, actual job durations were approximately 0.7–1.0 min validation, 0.8–1.4 min source sync, 0.7–0.8 min standings and 1.3–1.7 min final League job. The upstream source/standings job may have separately changed files; a final League no-op does not assert a **whole-workflow** no-op.
- Thus expensive multi-stage **processing** can still occur even when the final League publisher correctly avoids an unnecessary commit. `10/12` is a structured sample, **not** a 147-run or 30-day no-op rate, nor proof any stage can be safely removed.

### Odds Refresh: 12 evenly spaced production runs, all successful

Sample workflow run IDs:
`41370339690`, `41380874825`, `41391715808`, `41403720403`, `41417454642`, `41433582609`, `41449623986`, `41467687971`, `41487296725`, `41506235120`, `41524713162`, `41542207783`.

Each has an executed, successful `Observe market lines and persist isolated state` job (generally ~0.7–0.9 min) and a **skipped** `Source-validated scoped Odds publication` job. For this sample, **12/12** observer executions avoided the heavier Source publication. This is evidence that the existing conditional path works, **not** proof its observer job is unnecessary. The observer retains technical state and market-change timing responsibilities even when nothing is publishable.

## G5 interpretation and prioritized options (not authorized changes)

1. **P1 — League Live work before the final no-op:** the highest aggregate run elapsed among this day's dispatches, with 10/12 observed final League no-ops. Investigate a **multi-input** precondition before expensive producer/consumer stages, using canonical league source, NFL game finality, matchups, PWF, derived revision and App-dependent inputs. Do **not** gate solely on a League Source hash: Standings can change from NFL finality outside the League Source writer; App projections can change independently, and `league-live.yml` currently encodes important producer-before-consumer and race-safety semantics. Baseline selected job logs before any optimization.
2. **P2 — Scheduler wake-up overhead:** 288 five-minute checks (500.6 aggregate run wall-minutes) are a substantial orchestration signal. Inspect state, dispatch deadlines, observer health starvation bounds, retries and Cloudflare external wake-up before changing cadence; 5-minute reaction time and failure detection are part of the existing contract. Do not collapse/stop the central scheduler by assumption.
3. **P3 — Odds observer:** 144 observer runs (156.0 aggregate run wall-minutes); conditional publishing is already effective in 12/12 samples. Any observation-frequency optimization must preserve live game-window/cooldown/pending state, semantic net-change detection and isolated CAS publication. An observer no-op is **not** evidence that observation can be skipped.
4. **P4 — NFL Player Availability:** 144 runs (124.7 aggregate run wall-minutes), but this audit contains no verified per-run no-op or consumer-freshness classification. No skip recommendation until the update owner and availability windows are inspected.
5. **Lower-cadence/historical repair:** NFL Source's one 19.45-minute full sync is a different category from always-on observers; 24-hour volume does not justify compressing or skipping the weekly all-finalized TWP recovery path proven in PR #1312.

## Required next evidence before changing schedules or declaring G5 complete

- Obtain authenticated Actions **billable/usage** metrics (runner OS, minutes, plan/billing treatment, concurrency) or verified provider billing export. Avoid translating wall minutes into dollars or stating potential savings as fact.
- Expand 7-/30-day **workflow-level** frequency, duration, queue and failure sampling, with normalization by activity windows and event type; determine the cause of 147 versus nominal 144 League Live dispatches and whether repeated observed state is necessary.
- Establish per-stage cost and a **safe negative test** for a proposed League Live early-exit guard, including NFL-finality-only changes, scoring-week rollover, canonical correction, current/old TWP, WeeklyRecaps, matchup context, odds, changed source, retries, race recovery and outage/catch-up. No source hash-only shortcut.
- Preserve classified writer scopes, multi-input freshness, branch-isolated state, exact-head CI, selective Fast/Deep coverage and fallbacks. Separate G6 independent review is still required.

**Status:** One empirical baseline checkpoint, **partial G5**, not a completed scheduler rationalization or billing-cost analysis. No production workflow/data/permission changes; rollback is simply to revert the research-only PR.
