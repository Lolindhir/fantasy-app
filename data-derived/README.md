# Shared Derived Data

`data-derived/**` is the physical repository owner for deterministic,
reproducible, consumer-neutral **Shared Derived Data** under ADR-037/ADR-038.

It is deliberately separate from:

- `data-source/**`: provider evidence and canonical/normalized NFL or League facts;
- `public/data/**`: generated App delivery/read-model contracts;
- `fantasy-management/**`: consumer-specific Operations, analysis and decisions.

## Product inventory

One row per product directory. `tools/tests/test_data_derived_inventory.py`
(Fast) fails when a directory under `data-derived/` is missing here, has no
contract under `.ai-context/manual/`, no existing materializer, or no entry in
the read-only restore probe `tools/derived_clean_root_audit.py`.

<!-- derived-products:start -->
| Product directory | Contract | Materializer | Writer workflows |
|---|---|---|---|
| `nfl-games` | `.ai-context/manual/nfl-games.yaml` | `tools/nfl_games_materialize.py` | `sync-nfl-source-data.yml` |
| `nfl-injuries` | `.ai-context/manual/nfl-injuries.yaml` | `tools/nfl_injuries_phase.py` | `sync-nfl-source-data.yml` |
| `nfl-player-availability` | `.ai-context/manual/nfl-player-availability.yaml` | `tools/nfl_player_availability_materialize.py` | `sync-nfl-source-data.yml` |
| `player-week-fantasy` | `.ai-context/manual/player-week-fantasy.yaml` | `tools/player_week_fantasy_materialize.py` | `league-live.yml`, `update-standings.yml` |
| `team-week-performance` | `.ai-context/manual/team-week-performance.yaml` | `tools/team_week_performance_materialize.py` | `league-live.yml`, `update-standings.yml` |
| `player-valuation` | `.ai-context/manual/player-valuation.yaml` | `tools/derived_data.py` | `update-players.yml` |
| `league-transactions` | `.ai-context/manual/league-history.yaml` | `tools/derived_data.py` | `league-live.yml`, `update-transactions.yml` |
| `league-drafts` | `.ai-context/manual/league-history.yaml` | `tools/derived_data.py` | `league-live.yml`, `update-transactions.yml` |
| `league-standings` | `.ai-context/manual/league-standings.yaml` | `tools/derived_data.py` | `league-live.yml`, `update-standings.yml` |
| `season-statistics` | `.ai-context/manual/season-statistics.yaml` | `tools/derived_data.py` | `league-live.yml`, `update-transactions.yml` |
| `league-rivalry` | `.ai-context/manual/league-rivalry.yaml` | `tools/derived_data.py` | `league-live.yml`, `update-transactions.yml` |
| `league-schedule-outlook` | `.ai-context/manual/league-schedule-outlook.yaml` | `tools/league_schedule_outlook_materialize.py` | `league-live.yml`, `update-transactions.yml` |
| `matchup-context` | `.ai-context/manual/matchup-context.yaml` | `tools/matchup_context_materialize.py` | `league-live.yml`, `update-transactions.yml` |
| `weekly-recaps` | `.ai-context/manual/weekly-recaps.yaml` | `tools/weekly_recaps_materialize.py` | `league-live.yml`, `update-transactions.yml` |
| `team-cap-outlook` | `.ai-context/manual/derived-models.yaml` | `tools/team_cap_outlook_materialize.py` | `league-live.yml` |
| `team-injury-impact` | `.ai-context/manual/team-injury-impact.yaml` | `tools/team_injury_impact_materialize.py` | `league-live.yml`, `update-transactions.yml` |
<!-- derived-products:end -->

## NFL Injury report trajectories

`data-derived/nfl-injuries/<season>.json` is the global, league-independent
`nfl-injuries-v1` product (Issue #1421). It is rebuilt solely from the verified
`data-source/nfl/injuries/<season>/` canonical week partitions and manifest by
`tools/nfl_injuries_phase.py --phase derived`; it does not infer player availability,
clinical episodes, missed games or historical pre-kickoff knowledge. The isolated
Injury Source workflow delegates to the existing Source writer and publishes the
Derived result through the independent scoped rebuild-and-retry job. The daily
current-season importer is active; supported historical backfill and weekly
reconciliation remain tracked in #1421. The read-only clean-root audit restores
this product from accepted canonical input and verifies semantic no-op behavior.

## NFL Player Availability

`data-derived/nfl-player-availability/<season>.json` is the global, league-independent
`nfl-player-availability-v1` product (Issue #1590). Per player-week it keeps separate evidence
fields (observed report from `nfl-injuries-v1`, NFL roster status and code, participation from
snap counts or player stats, game/bye/final) and a documented `State`. It is the availability
layer for the player-detail injury history (`public/data/PlayerInjuryHistory.json`) and for
Fantasy Injury Impact (#1584). Contract: `.ai-context/manual/nfl-player-availability.yaml`.

## Global NFL Game

Consumer-neutral product (Issue #1077; daily Derived publication activated after the #1082 acceptance gate):

`data-derived/nfl-games/<season>.json`

Contract: `.ai-context/manual/nfl-games.yaml`.

The product joins `data-source/nfl/schedules`, `game-finality`, and
`schedule-odds` by canonical GameID. It exposes football scores/finality and
market-implied expected team points from **only SpreadLine and TotalLine**.
Each game also carries the additive `KickoffUtc` (canonical GameDay plus Eastern GameTime as a UTC instant, null when GameTime is unknown); it is the one central kickoff conversion for consumers.
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

## NFL GameDetail v2 (dynamic, same existing NFL Games owner)

Issue #1077 owns one versioned GameDetail per canonical GameID at
`data-derived/nfl-games/details/<season>/<GameID>.json`. The independent
compact season index `data-derived/nfl-games/<season>.json` stays
`SchemaVersion=1`.

All indexed, source-backed seasons use the same `SchemaVersion=2` detail
contract. The complete v1 `Game`, `TeamStats` and `SnapCounts` groups
are retained, with a new `PlayByPlayMetrics` group containing up to ten
provisional Competitive Opportunity, EPA, Success and Explosive facts. The
metrics are observed only if the corresponding original PBP Source archive
is accepted and its season-manifest SHA256/size matches; missing PBP history
is explicitly unavailable/null, never fabricated as zero. Source completeness
is never inferred from the existence of a gzip or final game score.

Pure rules live in `tools/derived_data_lib`. The **existing**
`tools/nfl_game_details_materialize.py` remains read-only by default; only
its explicit `--write` mode inside
`sync-nfl-source-data.yml::nfl_games_derived` persists Derived data via the
same classified rebuild-and-retry publisher. Current-season refresh remains
source-dependent. A single bounded historical schema-upgrade run occurs when
existing historical detail files still use v1; thereafter historic updates
run on the established Monday full-Source schedule. Existing source and index
writers, publication destinations, scheduler targets and app consumers are
unchanged. A separate Source acceptance process owns new original PBP seasons;
the GameDetail consumer never guesses that an unsupported season has plays.

The current GameDetail contract, source-availability semantics, release gates,
rollback plan and publication evidence are in
`.ai-context/manual/nfl-games.yaml`. The old `--core-v1` read-only preview
remains available to check unchanged v1 groups. After the first production
write, actual output/No-op verification is still required; tests do not
replace published readback.

## Historical original PBP delivery and weekly replay

Original nflverse PBP bytes are retained as immutable, SHA-addressed GitHub
Release assets, never as generated App data or compact Derived play lists.
The existing daily NFL Source Sync discovers missing historical years dynamically
from official release assets and canonical Source schedules and admits up to
three verified missing seasons per scheduled/manual full run. Current-season
acquisition remains independent and automatic; frozen original revisions are
reported for review, not silently overwritten.

The existing NFL Games Derived publisher performs an immediate GameDetail-v2
history replay when newly accepted historical PBP appears and a complete
recomputation every Monday from the accepted Source originals. GameDetail
algorithms/model versions can therefore change without re-downloading
unmodified originals from the provider. A verified local Actions archive cache
reduces repeated Release fetches and bounds decompressed memory to one season;
a cache restore still transfers its compressed contents. No other product may
read GameDetail as its Source. Additional shared Derived products require a
versioned contract, dependency declaration and an authorized existing writer
before becoming eligible for historical replay. Source acceptance and Derived
publication use distinct classified writers and preserve exact no-op semantics.

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

## TeamWeekPerformance (active historical weekly publisher)

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
FLEX slot eligibility to the shared Python `decision_windows.slot_definitions`
and `decision_windows.slot_eligible` rules (no PowerShell bridge).
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

# The established weekly update-standings.yml historical_twp job invokes
# this independently of historical PWF, behind its scoped rebuild-and-retry writer:
python3 tools/team_week_performance_materialize.py --all-finalized --write
```

All target weeks are discovered from canonical `data-meta` / league
manifests, never from the App's existing output inventory. NFL game finality,
league scored-week bounds, historical player positions, historical lineup
eligibility and official Sleeper matchup scoring must pass for every week
before any output is written. Independent NFL/PWF parity is non-blocking
in the normal writer; strict `--require-pwf` remains available for separate
read-only audits (including the narrowly governed 2025/W06 divergence).
A blocked canonical candidate prevents the entire batch write;
unchanged output is a semantic no-op.

The existing weekly `APP • Data • Standings` target schedules **three
independent jobs**: Standings, historical PlayerWeekFantasy and historical
TeamWeekPerformance. The TWP publisher uses
`tools/rebuild_and_publish.py` with **only**
`data-derived/team-week-performance/**` allowed, rechecks latest
`main` after publication races and does not alter Source, App, UI, live League
refresh or Scheduler configuration. It recalculates every finalized week
each weekly tick; corrections to old canonical matchup facts therefore
rebuild the affected partitions without a Source-diff monitor. The next normal
League Live App writer reprojects WeeklyRecaps from the resulting Derived
snapshots. Recovery after a correction is contingent on a successful weekly
job and is not immediate or revision-atomic.

Historical acceptance baseline: the manual read-only historical Derived
preflight [run #40030010930](https://github.com/Lolindhir/fantasy-app/actions/runs/40030010930)
passed **40/40** completed league weeks, `PWFWouldChange=0`,
`TWPWouldChange=37`, one approved scoring divergence and `SecondPassNoop=true`.
This was a pre-activation result, not the current partition inventory.
Issue #471 was closed after actual historical publication and subsequent
successful no-op runs on 2026-10-31. No new App publisher, extra cron,
fingerprint engine or source-diff scheduler feed was activated.
