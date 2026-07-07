# Podcast Extraction Rules

Purpose: central extraction rules for all podcast sources in Fantasy Management.

Use these rules for StoneLack/StonedLack, Down Set Talk, Football Bromance and future podcast sources.

The detailed source/knowledge/analysis separation is defined in:

`fantasy-management/_ai/PODCAST_SOURCE_MODEL.md`

## Core rule

Podcast extraction is source work, not final Fantasy Management analysis.

A podcast extraction answers:

> What did the podcast say?

It must not answer:

> What should Mighty Giants do?

That belongs to later Knowledge derivation and Analysis.

## Canonical source configuration

Podcast source identity, weighting and profile comparison are maintained centrally in:

`fantasy-management/_ai/source-registry.json`

Podcast-specific quirks, aliases and interpretation notes belong next to the source in:

`sources/podcasts/{source_id}/SOURCE_NOTES.md`

Do not maintain source weights in multiple places.

## Episode package rule

Each new processed podcast episode should be stored as one local package:

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

Legacy flat episode files may remain for compatibility, but new extractions should use the package folder.

## Required default outputs

A normal podcast extraction creates:

1. raw source material under the episode package
2. `episode.md` as a clean German human-readable podcast summary
3. `takes.json` as structured source takes grouped by category
4. `index.json` as local technical metadata and package map

Do not update global indexes during normal podcast extraction.

Do not write source takes to `derived/knowledge/takes/` by default. Podcast takes are not Knowledge yet.

## `episode.md` rule

`episode.md` is the clean reader-facing podcast summary.

It should be good enough that the user could read it directly or publish it privately.

It must not contain internal extraction metadata, such as:

- file inventories
- take IDs
- source package paths
- `global_index_update`
- extraction status flags
- machine-readable companion file references
- Mighty Giants recommendations

It may contain:

- episode topic and context
- the hosts' main arguments
- rankings, tiers, boards or categories from the podcast
- player/team/position sections
- podcast-level positives and risks
- source conclusion

Keep it inside the source perspective.

Good:

> The hosts like Jordan Tyson because they see a fast WR2 path in New Orleans.

Not in `episode.md`:

> Mighty Giants should draft Jordan Tyson.

## `takes.json` rule

`takes.json` contains structured podcast statements from the episode.

Top-level categories:

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

Category meanings:

- `players`: specific player statements.
- `teams`: NFL team, depth chart, team environment or team position-group statements.
- `positions`: position-group statements such as WR, RB, TE or QB.
- `nfl`: general NFL, draft, coaching, scheme or league-context statements.
- `fantasy`: fantasy strategy, scoring, redraft, dynasty, rookie draft, bestball, market or format statements.
- `other`: source statements that do not fit cleanly elsewhere.

Default take fields:

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

Do not split every take into a separate JSON file by default.

Use one `takes.json` per episode unless there is a clear practical reason to split it.

## `index.json` rule

`index.json` is the local technical package map.

It may contain:

- source id
- episode id
- episode number
- title
- dates
- local package paths
- raw status
- take counts by category
- extraction status
- migration notes for legacy files

Keep this metadata out of `episode.md`.

## JSON formatting rule

Fantasy Management JSON artifacts that are created or manually maintained by AI must be human-readable and pretty-printed.

Use:

- UTF-8 text
- two-space indentation
- one property per line
- arrays on multiple lines, including single-item arrays
- exactly one array item per line
- nested arrays and objects on separate lines
- stable key order within the same file type when practical
- trailing newline at end of file

Do not use inline arrays such as `["tag1", "tag2"]`, `["take_id"]` or `[]` in Fantasy Management JSON. Empty arrays should also be expanded across lines when practical.

Compact one-line JSON is only acceptable for generated application/runtime data outside Fantasy Management when the generator owns the format.

## Raw source rule

Store raw transcripts or raw notes unchanged under the episode package.

Do not clean, rewrite or normalize the raw source file.

If a single large raw file cannot be committed, split the raw transcript into ordered parts and create `raw/manifest.md`. The ordered concatenation of the parts is the raw source for that episode.

A placeholder raw file is not a completed raw source. If the full raw source is missing, mark the package as incomplete in `index.json`.

## Knowledge separation rule

Do not treat podcast takes as active Knowledge just because they exist.

After extraction, a separate Knowledge derivation step may decide which takes matter for:

- players
- NFL teams
- positions
- NFL context
- fantasy strategy

Knowledge belongs under:

```text
fantasy-management/knowledge/
  players/
  teams/
  positions/
  nfl/
  fantasy/
```

A redraft-only take may stay only in the episode package if it does not matter for our Dynasty league.

If a redraft take affects market value, it may become fantasy-market knowledge rather than player-quality knowledge.

## Completeness gate

Before marking an episode extraction as complete, verify:

1. raw source is present or clearly marked as legacy/pending in `index.json`
2. `episode.md` is a clean German podcast summary without internal metadata
3. `takes.json` exists and uses the six standard categories
4. meaningful player, team, position, NFL, fantasy and other source statements were reviewed
5. high-signal player statements are represented under `players`
6. team/depth-chart statements are represented under `teams`
7. position-group statements are represented under `positions`
8. fantasy strategy and format statements are represented under `fantasy`
9. cautious, negative and uncertainty takes are extracted, not only positive takes
10. `index.json` records counts by take category
11. JSON files are pretty-printed with the formatting rule above
12. any Knowledge derivation is either not started or explicitly stored separately under `knowledge/`

If any required item fails, mark the package as `incomplete` or `needs_rework` in `index.json` and explain what is missing.

## Recommendation rule

Podcast output is source context, not a final recommendation.

Final Mighty Giants recommendations belong under `fantasy-management/analyses/` and must combine current league data, source context, derived Knowledge and current market/news context when relevant.
