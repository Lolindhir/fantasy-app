# Sleeper Trending Players

## Purpose

Sleeper Trending Players is the active platform-wide roster-activity signal for Fantasy Management.

It measures how often players appeared in Sleeper add or drop activity during a rolling time window. It is not a player ranking, ADP, trade value, projection or league-specific ownership source.

## Official source

Documented endpoints:

```text
GET https://api.sleeper.app/v1/players/nfl/trending/add?lookback_hours=<hours>&limit=<int>
GET https://api.sleeper.app/v1/players/nfl/trending/drop?lookback_hours=<hours>&limit=<int>
```

Default repository configuration:

```yaml
sport: nfl
lookback_hours: 24
limit: 100
activity_types:
  - add
  - drop
refresh_target: daily
```

The integration uses only the documented public API. It does not scrape Sleeper pages, use private endpoints, store account credentials or require a paid plan.

## Attribution

Every stored document and every user-facing use of the signal must attribute Sleeper.

Canonical stored attribution:

```text
Trending data provided by Sleeper
```

## Fetcher

Run from the repository root:

```bash
python fantasy-management/_ai/scripts/fetch_sleeper_trending.py
```

Optional parameters:

```bash
python fantasy-management/_ai/scripts/fetch_sleeper_trending.py \
  --lookback-hours 24 \
  --limit 100 \
  --timeout 30 \
  --attempts 3
```

The fetcher performs both required requests before publishing a new successful state.

## Source output files

The first successful execution creates:

```text
raw-latest.json
latest.json
```

`raw-latest.json` stores the latest validated add and drop responses with query configuration, source URLs, response headers, fetch time and attribution.

`latest.json` stores the normalized union of both top-N lists. Each player has separate `add` and `drop` objects. The source-local file intentionally retains stable Sleeper IDs instead of duplicating mutable player and ownership data.

Example:

```json
{
  "sleeper_player_id": "1234",
  "add": {
    "status": "listed",
    "rank": 3,
    "count": 527
  },
  "drop": {
    "status": "not_listed",
    "rank": null,
    "count": null
  }
}
```

`not_listed` never means zero activity. It means only that the player was outside the returned top-N list for that activity type and query configuration.

## Derived readable output

After every successful source refresh, the Fantasy Operations materialization workflow creates:

```text
fantasy-management/generated/operations/external-signal-relevance.json
```

This is the human- and monitoring-facing dataset. It joins the Sleeper ID with current `Players.json` and derives ownership from every `Roster`, `Reserve` and `Taxi` list in `League.json`.

It includes:

- player name;
- position;
- NFL team;
- identity resolution status;
- `mighty_giants`, `opponent_rostered` or `fantasy_free_agent` ownership;
- current Add and Drop rank/count;
- entered/left-top-N, rank and count changes after the baseline;
- readable `views.sleeper-trending.add` and `views.sleeper-trending.drop` arrays ordered by rank.

Sleeper can return NFL team-defense entities whose IDs are uppercase team abbreviations such as `NE` or `CLE`. The external-signal catalog classifies IDs matching `^[A-Z]{2,3}$` as `team_defense` and excludes them from player identity, ownership and free-agent views. They remain auditable through the separate `excluded_non_player_entities` counts in the source state and quality coverage.

Only unmatched player-like source IDs remain visible as information-level `unresolved_external_signal_player` findings. A player appearing on more than one fantasy roster is an error.

Materialize manually with:

```bash
python fantasy-management/_ai/scripts/build_fantasy_operations_inputs.py
python fantasy-management/_ai/scripts/materialize_external_signals.py
```

## Baseline and comparison semantics

The first successful run is a silent baseline:

```yaml
baseline: true
material_event_eligible: false
```

A later snapshot is comparable only when schema version, provider, `lookback_hours` and `limit` match the previous successful snapshot.

Comparable snapshots expose technical changes separately for adds and drops:

- `entered_top_n`
- `left_top_n`
- `rank_changed`
- `count_changed`

These are source deltas, not Fantasy recommendations.

Counts come from overlapping rolling windows. A count delta therefore is not the number of new transactions since the previous fetch.

## Validation and failure behavior

The fetcher fails closed on:

- network failures after bounded retries
- HTTP 429 or server errors after bounded retries
- empty or invalid JSON
- a non-array payload
- empty result lists
- more rows than the requested limit
- missing player IDs
- duplicate player IDs within one activity list
- non-integer or negative counts

Both add and drop payloads must validate before either output is replaced. A failed run leaves the last successful files unchanged and must not create monitoring events.

The downstream materializer also fails closed on invalid catalog configuration, invalid non-player entity regexes, duplicate source identities, invalid row arrays or missing required league/player inputs.

## Retention

Only the newest Raw and normalized source state is stored. Git history retains prior committed states.

If long-term trend analysis is added later, it should use a compact aggregate time series rather than duplicating complete daily top-N snapshots.

## Decision use

Sleeper Trending is an event detector and research trigger. It must not independently cause an add, drop, trade, hold, shop or cut recommendation.

A relevant trend should trigger targeted verification against current injury, role, opportunity, NFL news, Dynasty market and Redraft ADP context.

## Scheduling

Active workflow:

```text
.github/workflows/update-sleeper-trending.yml
```

It targets 06:35 Europe/Berlin. Its generated-data push triggers:

```text
.github/workflows/materialize-fantasy-operations-inputs.yml
```

The intended order is:

```text
Sleeper signal refresh
→ identity and ownership materialization
→ scheduled monitoring at 07:00 Europe/Berlin
```
