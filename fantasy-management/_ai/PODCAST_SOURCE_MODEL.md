# Podcast Source Model

Purpose: define the simplified source model for podcast extraction and later Fantasy Management use.

This model separates three layers:

1. Podcast episode package — what the podcast said.
2. Knowledge — what remains relevant for our league after interpretation.
3. Analysis — what Mighty Giants should do with that knowledge.

## Core principle

Podcast extraction must not decide final Fantasy Management relevance.

Podcast extraction answers:

> What did the source say?

Knowledge derivation answers:

> Which source statements are relevant for our league, format and current context?

Analysis answers:

> What should Mighty Giants do?

## Podcast episode package

Each processed podcast episode should live as one local package:

```text
fantasy-management/sources/podcasts/{source_id}/episodes/{year}/{episode_id}/
  raw/
    manifest.md
    part01.md
    part02.md
  episode.md
  takes.json
  index.json
```

For small transcripts, `raw/source.md` may replace split raw parts.

## `episode.md`

`episode.md` is the human-readable podcast summary.

It must be written like a clean article that the user could read or publish privately:

- no internal pipeline metadata
- no file inventory
- no take IDs
- no `global_index_update`
- no extraction status blocks
- no Mighty Giants recommendation

It may include source framing and interpretation of the podcast's own logic, but it must stay inside the podcast perspective.

Good:

> The hosts see Jordan Tyson as one of their favorite players in the episode because they expect a fast WR2 path in New Orleans.

Not in `episode.md`:

> Mighty Giants should draft Jordan Tyson.

That belongs in later analysis.

## `takes.json`

`takes.json` contains structured podcast statements from the same episode.

It is still source material, not knowledge.

Use these top-level categories:

```json
{
  "players": [
  ],
  "teams": [
  ],
  "positions": [
  ],
  "nfl": [
  ],
  "fantasy": [
  ],
  "other": [
  ]
}
```

### Category meanings

- `players`: statements about specific players.
- `teams`: statements about NFL teams, depth charts, team environments or team position groups.
- `positions`: statements about positional groups such as WR, RB, TE or QB.
- `nfl`: general NFL, draft, coaching, scheme or league-context statements.
- `fantasy`: fantasy strategy, scoring, redraft, dynasty, rookie draft, bestball, market or format statements.
- `other`: source statements that do not fit cleanly elsewhere.

### Take fields

Keep takes simple and readable:

```json
{
  "id": "sl_0569_player_001",
  "category": "players",
  "type": "player",
  "entity": "Jordan Tyson",
  "team": "NO",
  "position": "WR",
  "formats": [
    "dynasty",
    "redraft",
    "rookie_draft"
  ],
  "podcast_take": "The source statement in plain language.",
  "reasoning": [
    "Reason from the podcast."
  ],
  "risks": [
    "Uncertainty or downside from the podcast."
  ],
  "sentiment": "positive",
  "conviction": "high",
  "evidence": {
    "timestamp_start": "00:45:36",
    "timestamp_end": "00:48:22"
  },
  "tags": [
    "rookie_wr",
    "landing_spot",
    "opportunity"
  ]
}
```

Do not split every take into separate files by default. One `takes.json` per episode is the default.

## `index.json`

`index.json` is the local technical map for the episode package.

It may contain:

- source id
- episode id
- title
- dates
- paths within the package
- counts by take category
- extraction status

Keep technical metadata out of `episode.md`.

## Knowledge layer

Knowledge is derived after podcast extraction.

Knowledge should live outside the podcast source package:

```text
fantasy-management/knowledge/
  players/
  teams/
  positions/
  nfl/
  fantasy/
```

Knowledge derivation may ignore podcast takes that are not useful for our format.

Example:

A podcast take says:

> Player X is a redraft must-have.

If this does not matter for our Dynasty league, it should remain in the podcast episode package but does not need to become active player knowledge.

If it affects market value, it may become fantasy-market knowledge instead of player-quality knowledge.

## Analysis layer

Analyses remain concrete decision documents:

```text
fantasy-management/analyses/{year}/
  players/
  trades/
  roster/
  draft/
```

A player analysis should combine:

1. current league data from `public/data/`
2. player knowledge
3. team knowledge
4. position knowledge
5. relevant source takes as evidence
6. current external context when needed
7. final Mighty Giants recommendation
