# Sleeper Trending Players Source Audit

Audit date: 2026-08-06

## Decision

Sleeper Trending Players is approved as an automated external Fantasy Management signal under the documented public API contract.

```yaml
provider: sleeper
source_kind: external_signal
signal_kind: roster_activity
scope: platform_wide
sport: nfl
status: automated_source
cost: free
authentication: none
ranking: false
```

## What the source measures

The source reports platform-wide Sleeper add or drop activity for players during a configurable rolling lookback window.

The documented response exposes:

- `player_id`
- `count`

The list order is retained as source rank within the selected add or drop query, but the signal must not be described as a player-quality ranking.

It does not directly measure:

- Dynasty value
- Redraft value
- ADP
- trade value
- projection
- player quality
- unique managers or unique leagues
- ownership or availability in the Mighty Giants league

## Access audit

The provider publishes an official JSON API endpoint for both activity types:

```text
GET https://api.sleeper.app/v1/players/<sport>/trending/<type>?lookback_hours=<hours>&limit=<int>
```

The integration requires:

- no account
- no API key
- no paid subscription
- no browser session

Only official documented API endpoints may be used. Website scraping, private endpoints and account automation are outside the approved scope.

## Attribution requirement

Sleeper asks users of trending data to provide attribution. Every stored source document and every user-facing use must identify Sleeper as the provider.

Canonical attribution:

```text
Trending data provided by Sleeper
```

## Technical suitability

Strengths:

- documented public endpoint
- machine-readable JSON
- stable Sleeper player IDs
- separate add and drop signals
- configurable rolling lookback window
- configurable top-N result size
- low request volume for daily refreshes

Constraints:

- the result is top-N only
- absence from the list is not zero activity
- counts are rolling-window values
- count deltas are not transaction counts since the previous fetch
- the response does not provide player names, teams or positions
- the response does not provide league context
- the methodology behind count deduplication is not documented

## Approved initial configuration

```yaml
lookback_hours: 24
limit: 100
activity_types:
  - add
  - drop
refresh_target: daily
```

The limit is validated against the actual response. A response larger than the requested limit is rejected.

## Failure policy

The fetcher must fail closed. Both activity types must be fetched and validated before the latest state is replaced.

The previous successful state remains authoritative after:

- network or timeout failure
- exhausted retryable HTTP errors
- invalid JSON
- invalid payload shape
- duplicate player IDs
- missing player IDs
- negative or non-integer counts

A failed or partial refresh must not produce monitoring events.

## Baseline policy

The first successful state is a silent baseline. It cannot generate a material player event.

Later states are comparable only when provider, schema, lookback window and result limit match. Configuration changes deliberately reset the baseline.

## League integration boundary

The source snapshot is global and must remain independent of `League.json`.

A separate downstream layer may join `sleeper_player_id` to current player and league data to derive Mighty Giants, opponent, fantasy-free-agent or unresolved status. That derived layer, not the source fetcher, owns league-specific relevance.

## Operational conclusion

Sleeper Trending Players is suitable as an automated attention and event-detection signal. It is not sufficient evidence for a roster recommendation and must be reconciled with current injury, role, opportunity, market, ADP, news and league ownership context.

The production scheduler should eventually refresh rankings and external signals shortly before scheduled monitoring. That orchestration is intentionally not part of this source implementation and requires a separate approved GitHub Actions change.

## Audit sources

- https://docs.sleeper.com/
- https://sleeper.com/blog/how-to-embed-sleepers-trending-players-on-your-website/
