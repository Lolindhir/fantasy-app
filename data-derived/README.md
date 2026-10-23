# Shared Derived Data

`data-derived/**` is the physical repository owner for deterministic,
reproducible, consumer-neutral **Shared Derived Data** under ADR-037/ADR-038.

It is deliberately separate from:

- `data-source/**`: provider evidence and canonical/normalized NFL or League facts;
- `public/data/**`: generated App delivery/read-model contracts;
- `fantasy-management/**`: consumer-specific Operations, analysis and decisions.

## Global NFL Game

Consumer-neutral product (Issue #1077; daily Derived publication activated after the #1082 acceptance gate):

`data-derived/nfl-games/<season>.json`

Contract: `.ai-context/manual/nfl-games.yaml`.

The product joins `data-source/nfl/schedules`, `game-finality`, and
`schedule-odds` by canonical GameID. It exposes football scores/finality and
market-implied expected team points from **only SpreadLine and TotalLine**.
Moneyline and bookmaker price changes do not enter the product or invalidate
it. A missing entire odds partition is unavailable evidence; nullable fields
are preserved as null.

The generator `tools/nfl_games_materialize.py` is read-only by default.
A dedicated dependent job inside the **existing daily full NFL Source Sync**
(`.github/workflows/sync-nfl-source-data.yml`) validates Source-only
restoration and publishes all seasons via `tools/rebuild_and_publish.py`.
The publisher is restricted to `data-derived/nfl-games/**`, rebuilds from
latest main after publication races and creates **no commit on a no-op**.
The NFL Live Finality scope and targeted source-dataset runs skip this job;
there is no new Scheduler target and no odds-only cadence change.

The 10-minute polling/Spread+Total delta gate activation remains owned by
#471. Source snapshots do not provide historically proven pregame timestamps.

## PlayerWeekFantasy

The first product is:

`data-derived/player-week-fantasy/<CanonicalLeagueID>/<season>/<week>.json`

Canonical contract:

`.ai-context/manual/player-week-fantasy.yaml`

Materializer:

`tools/player_week_fantasy_materialize.py`

The dataset combines the canonical weekly NFL player population, explicit League
`ScoringSettings`, canonical scoring/finality evidence and leak-free historical
usage/scoring history into one league/week player state containing Actual,
V4-C Projection and the V4-C-PI1 Prediction Range.

Writers must be deterministic and preserve semantic no-op behavior. A source or
rule change that affects a documented dependency requires re-derivation; wall-clock
time alone does not.

Consumer-specific publication and identity adaptation happen downstream. The
shared layer remains keyed by `CanonicalPlayerID`; App/Sleeper identity joins
belong to the later App publisher.

The existing weekly `APP • Data • Standings` scheduler target runs a separate
`historical_pwf` job. It re-generates every registered league's **finalized**
PlayerWeekFantasy week from canonical NFL and League inputs using
`tools/historical_pwf_batch.py --write`. The original Standings and current-week
League Live jobs stay independent. A non-final or incomplete historical week
aborts the PWF batch before any write; the publisher scopes the commit to
`data-derived/player-week-fantasy/**` and retries from latest `main` on a
publication race. No new scheduler or special restore system is involved.

## TeamWeekPerformance (historical weekly publisher configured)

Target dataset:

`data-derived/team-week-performance/<CanonicalLeagueID>/<season>/<week>.json`

Canonical contract:

`.ai-context/manual/team-week-performance.yaml`

Domain calculator and deterministic no-op writer:

`tools/team_week_performance.py`

It calculates all-roster hypothetical best-ball potential, actual starter points,
coaching efficiency, missed points and league-wide Best Manager/Best Coach winners
from canonical fantasy week matchups, historical positions and season-specific
slot eligibility. Starter, Bench, Taxi and IR/Reserve are all considered.
The shared result is designed for WeeklyRecaps/Overview, Team History, Season
Awards and other consumers; no consumer should recompute these domain values.

**Historical input adapter:** `tools/team_week_performance_sources.py`
validates both canonical NFL week finality and the League's scored-week
boundary, resolves week-specific player positions and delegates all starter/
FLEX slot eligibility to the existing FantasyRelevance PowerShell helpers
through `public/requests/utils/league/ExportWeeklyPerformanceSlots.ps1`.
Missing target-week positions may fall back to consistent earlier weeks
of the same season, then a finalized same-season NFL roster, then only a
**prior finalized NFL season** with a matching canonical player ID and no
conflicting older finalized season positions. Missing/contradictory historical
position evidence fails closed. Partial weekly team populations are rejected
against the historical league `Settings.num_teams`; actual starters must
fit the historical slot configuration. The fantasy
team's canonical matchup-week Players array is its complete retrospective
candidate pool under ADR-036; no intraweek transfer replay is required.
The adapter does not publish derived records.

**Controlled producer (merged PR #993):**

```shell
# Single-week canonical audit; read-only by default.
python3 tools/team_week_performance_materialize.py --league nfl-reise --season 2026 --week 5 --require-pwf

# All registered leagues and seasons, strict finalized-week PWF parity, read-only.
python3 tools/team_week_performance_materialize.py --all-finalized --require-pwf

# The established weekly update-standings.yml job invokes this behind its
# dedicated rebuild-and-retry publisher, after the historical PWF job succeeds:
python3 tools/team_week_performance_materialize.py --all-finalized --write --require-pwf
```

All target weeks are discovered from canonical `data-meta` / league
manifests, never from the App's existing output inventory. NFL game finality,
league scored-week bounds, historical player positions, real historical
lineup eligibility, official matchup scoring and final PWF parity must pass
for every week before any output is written. The narrowly versioned 2025/W06
exception is accepted without rewriting either score. A blocked candidate
prevents the entire batch write; unchanged output is a semantic no-op.

The existing weekly `APP • Data • Standings` target schedules three jobs:
Standings independently, historical PlayerWeekFantasy, then historical
TeamWeekPerformance (dependent on successful PWF publication). The TWP
publisher uses `tools/rebuild_and_publish.py` with **only**
`data-derived/team-week-performance/**` allowed, rechecks on the latest
`main` after publication races and does not alter Source, App, UI, live League
refresh or Scheduler configuration.

Acceptance baseline: the manual read-only historical Derived preflight
[run #40030010930](https://github.com/Lolindhir/fantasy-app/actions/runs/40030010930)
passed **40/40** completed league weeks, `PWFWouldChange=0`,
`TWPWouldChange=37`, one approved scoring divergence and `SecondPassNoop=true`.
Only 2026 W03-W05 were published on `main` before this weekly writer activation.
A successful first real TWP publication followed by an unchanged no-op run and
a complete 40-file inventory is required for production acceptance. This is
not an App publisher or a second scheduled workflow.
