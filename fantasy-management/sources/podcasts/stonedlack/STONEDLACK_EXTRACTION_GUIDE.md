# StonedLack Extraction Guide

Purpose: source-specific notes for extracting StonedLack podcast episodes.

The shared podcast structure is defined centrally in:

- `fantasy-management/_ai/PODCAST_SOURCE_MODEL.md`
- `fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md`
- `fantasy-management/_ai/templates/podcast/`

This guide only adds StonedLack-specific extraction notes.

## Core principle

StonedLack extraction creates a podcast source package, not active Knowledge and not a Mighty Giants recommendation.

Source package:

```text
sources/podcasts/stonedlack/episodes/YYYY/sl_XXXX/
  raw/
    manifest.md
    part01.md
    part02.md
  episode.md
  takes.json
  index.json
```

## `episode.md`

`episode.md` must be a clean German podcast summary.

It should read like a good article about the episode and must not contain:

- internal extraction metadata
- take IDs
- file inventories
- `global_index_update`
- Mighty Giants recommendations

It may contain:

- episode topic
- hosts' central arguments
- board/tier/ranking logic when present
- player sections
- team context
- position-group context
- fantasy strategy from the source perspective
- source-level conclusion

## `takes.json`

Store all structured StonedLack source takes for the episode in one categorized `takes.json`.

Use the shared categories:

- `players`
- `teams`
- `positions`
- `nfl`
- `fantasy`
- `other`

Do not create one JSON file per take by default.

## StonedLack extraction focus

When processing a StonedLack transcript, extract:

1. player evaluations
2. team/depth-chart context
3. position-group takes
4. rookie draft strategy
5. redraft vs dynasty splits
6. buy/sell/hold/fade/watchlist language
7. format-dependent notes
8. caution and uncertainty buckets
9. unresolved transcript names
10. source-level conviction and sentiment

## Entity resolution

Automatic transcripts often break player names.

For important entities, preserve uncertainty in `takes.json` using notes, tags or confidence wording.

Use context to resolve names:

- position
- NFL team
- college
- draft round
- landing spot
- teammates
- competition
- episode section

Verify decision-relevant names before using them for Knowledge derivation or analysis.

Recommended identity-verification priority:

1. official NFL/team pages
2. NFL.com Draft Tracker
3. official college/athletics pages
4. Pro Football Reference / Sports Reference
5. ESPN / Sleeper / FantasyPros / KeepTradeCut for fantasy context, not primary identity

## Completeness gate

A StonedLack episode package is complete when:

1. raw source is present in `raw/` and referenced in `raw/manifest.md` and `index.json`
2. `episode.md` is a clean German source summary without internal metadata
3. `takes.json` exists and uses all six shared categories
4. all high-signal player statements are represented under `players`
5. team/depth-chart statements are represented under `teams`
6. position-group statements are represented under `positions`
7. fantasy strategy and format statements are represented under `fantasy`
8. cautious, negative and uncertainty takes are included, not only positive takes
9. unresolved or low-confidence identities are visible in the summary or takes
10. `index.json` records package paths, raw status and take counts
11. no active Knowledge or Mighty Giants recommendations are mixed into the source package

## Knowledge handoff

After extraction, a separate Knowledge derivation step may read the episode package and decide what applies to:

- `fantasy-management/knowledge/players/`
- `fantasy-management/knowledge/teams/`
- `fantasy-management/knowledge/positions/`
- `fantasy-management/knowledge/nfl/`
- `fantasy-management/knowledge/fantasy/`

Do not copy every StonedLack take into Knowledge. Redraft-only or irrelevant takes may stay only in the source package.
