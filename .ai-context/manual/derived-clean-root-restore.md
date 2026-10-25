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

PlayerValuation, LeagueTransactions, LeagueDrafts, PlayerWeekFantasy and TeamWeekPerformance per
league, plus the global NFL Games product. They are built with the productive generators
(`derived_data.py`, `historical_pwf_batch.py`, `team_week_performance_materialize.py
--all-finalized --require-pwf`, `nfl_games_materialize.py`); there is no second implementation.

## Three-way comparison

* empty root: only `data-source`, `data-meta` and `public/requests` are visible; each product is built twice.
* productive-like root: a copy of the published `data-derived` plus the published
  `public/data/Standings.json` and `Players.json` (identity-hold seed, as in `update-players.yml`); built once.
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

* LeagueDrafts needs `public/data/Standings.json` only when a current-season draft has no
  Sleeper order (`league_drafts.py`, typically at the next season change). The probe reports this
  as `latent-blocker`; the source-owned predecessor belongs to Issue #987 (LeagueStandings as
  Shared Derived). Do not treat copying Standings as source-only restoration.
* Identity hold: the productive PlayerValuation run seeds holds from `public/data/Players.json`. A
  hold row that only the seed can supply shows up as `restore-defect`; resolving it is an owner
  decision, not a silent model change.

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
