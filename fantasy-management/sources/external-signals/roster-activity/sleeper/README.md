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

## Output files

The first successful execution creates:

```text
raw-latest.json
latest.json
```

`raw-latest.json` stores the latest validated add and drop responses with query configuration, source URLs, response headers, fetch time and attribution.

`latest.json` stores the normalized union of both top-N lists. Each player has separate `add` and `drop` objects.

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

## Retention

Only the newest Raw and normalized state is stored. Git history retains prior committed states.

If long-term trend analysis is added later, it should use a compact aggregate time series rather than duplicating complete daily top-N snapshots.

## Player identity and league joins

The stable source identity is Sleeper `player_id`, normalized as `sleeper_player_id`.

The fetcher intentionally does not read `League.json` or player files. A later materialization layer must join the global signal to current league data and derive one of the following league-facing states:

- `mighty_giants`
- `opponent_rostered`
- `fantasy_free_agent`
- `unresolved`

Unknown player IDs must remain visible as data-quality findings rather than being silently discarded.

## Decision use

Sleeper Trending is an event detector and research trigger. It must not independently cause an add, drop, trade, hold, shop or cut recommendation.

A relevant trend should trigger targeted verification against current injury, role, opportunity, NFL news, Dynasty market and Redraft ADP context.

## Automated workflow

The active workflow is:

```text
.github/workflows/update-sleeper-trending.yml
```

It can be started manually through `workflow_dispatch` and runs daily at:

```text
06:35 Europe/Berlin
```

The scheduled Fantasy Operations Monitoring starts at 07:00 Europe/Berlin. The signal refresh therefore has a planned safety margin of 25 minutes.

GitHub schedules are expressed in UTC. The workflow uses paired UTC cron entries and a Berlin-offset gate so exactly one scheduled run is selected during both CET and CEST:

```text
04:35 UTC during CEST
05:35 UTC during CET
```

Before fetching, the workflow runs the source-specific unit tests. It stages only the Sleeper roster-activity source directory and creates a generated-data commit only after a successful validated fetch.

The broader desired production order remains:

```text
league/source refreshes
→ external ranking refreshes
→ Sleeper signal refresh
→ derived player/ownership materialization
→ scheduled monitoring
```

This workflow establishes the Sleeper-signal step. Coordinated rescheduling or dependency orchestration across all ranking and derived-data workflows remains a separate follow-up.
