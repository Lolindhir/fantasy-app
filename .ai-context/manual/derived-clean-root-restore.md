# Shared Derived restore probe (Issue #471)

`tools/derived_clean_root_audit.py` proves that the existing Shared Derived products can be
recreated from canonical `data-source` and `data-meta` alone. It is a read-only diagnostic, not a
publisher, scheduler, product contract or authorization to backfill. It writes nothing in the
repository (only two temporary roots).

Run `python3 tools/derived_clean_root_audit.py [--league <CanonicalLeagueID>]` in a full checkout.
Leagues come from `data-meta`; without `--league` every league is audited. Rebuilding PWF/TWP for
the whole history takes several minutes, and TeamWeekPerformance needs `pwsh` (existing
FantasyRelevance slot bridge).

## Products

The 13 products listed in `PRODUCTS` of `tools/derived_clean_root_audit.py` (per league: PlayerValuation,
LeagueTransactions, LeagueDrafts, PlayerWeekFantasy, TeamWeekPerformance, SeasonStatistics, LeagueStandings,
LeagueRivalry, MatchupContext, WeeklyRecaps; global: NFL Games, NFL Injuries, NFL Player Availability). They are
built with the productive generators (`derived_data.py`, `historical_pwf_batch.py`,
`team_week_performance_materialize.py --all-finalized --require-pwf`, `nfl_games_materialize.py` and the
product materializers); there is no second implementation.

`data-derived/README.md` registers 16 products. Three are deliberately **outside** the probe
(`OUTSIDE_RESTORE_PROBE` in `tools/tests/test_data_derived_inventory.py`): `league-schedule-outlook` (own
materializer with consistency guard, Issue #1519), `team-cap-outlook` (current-season snapshot of the live rosters,
Issue #1571) and `team-injury-impact` (depends on the current PlayerWeekFantasy partition, Issue #1584). Their
coverage is their own materializer tests, not a clean-root replay; this is an accepted, documented exception.

## Three-way comparison

* empty root: only `data-source`, `data-meta` and `public/requests` are visible; each product is built twice.
* productive-like root: a copy of the published `data-derived` plus the published
  `public/data/Standings.json` (historical shadow only); built once. The published Players identity-hold seed was
  retired by ADR-076 and is never copied.
* published: the files in the repository.

| Status | Meaning | Severity |
|---|---|---|
| `ready` | empty = productive-like = published, second empty pass is a no-op | ok |
| `stale-published` | empty = productive-like, published files are behind or orphaned | hint |
| `latent-blocker` | builds only with the transitional Standings input (Issue #987) | hint |
| `restore-defect` | empty differs from productive-like: the product silently depends on earlier output (including a hold seed) | error |
| `nondeterministic` | the second empty pass changed output | error |
| `blocked` | a source is not ready or a build failed (including a missing `pwsh`) | error |

A published file that the productive-like run leaves untouched and the empty run cannot build is an
orphan and is reported as `stale-published`, not as a defect. Exit code 2 means at least one error
status; hints keep exit code 0 (`HintProducts` in the JSON).

## Known open owner decisions

* LeagueDrafts no longer needs `public/data/Standings.json` for the draft order: the order placements come from the
  league-standings product (`derived_data_lib/league_standings.draft_order_placements`, Issue #1263). The probe's
  `latent-blocker` hint for the transitional Standings input stays for a pre-existing path and is reported only if it
  actually occurs.
* Identity hold: since ADR-076 a hold row comes only from persisted PlayerValuation snapshots (no published
  Players.json seed). A hold row no snapshot knows is a visible gap, not a silent carry-over.

## Weekly CI gate (Issue #471, step 2)

The job `restore-gate` ("CI Audit • Derived Restore Gate") in `.github/workflows/build.yml` runs
`python tools/derived_clean_root_audit.py --github-summary` in the weekly full audit
(`scheduler-ci-full-audit`, Thursday 02:15 Europe/Berlin) and in a manual `full` dispatch. It has
`contents: read` only, no writer, no scheduler target and never runs on a pull request or a
Deep-scope dispatch. `CI / Merge Gate` requires it in a full audit and requires it skipped
everywhere else.

* Red: `restore-defect`, `nondeterministic` and `blocked`. `blocked` stays red on purpose: if a
  source is not ready or a build fails, restorability is not proven, and the audit is weekly, so a
  transient source gap surfaces as an alert instead of silently passing.
* Green with hint: `stale-published` and `latent-blocker` (named in the Job Summary only).
* The Job Summary table lists every unit, errors first. Workflow Health already alerts on the
  first failed audit (`build.yml`, category important).
* Timeout 60 minutes (a local full run takes about 23 minutes, almost all PlayerWeekFantasy).
  TeamWeekPerformance needs `pwsh`, which the hosted runner provides.

Not covered: the market product (waits for Issue #988) and any publishing cadence.
