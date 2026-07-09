# Stoned Lack Extraction Guide

Purpose: source-specific notes for extracting Stoned Lack podcast episodes.

The shared podcast structure is defined centrally in:

- `fantasy-management/_ai/PODCAST_SOURCE_MODEL.md`
- `fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md`
- `fantasy-management/_ai/templates/podcast/`

This guide only adds Stoned Lack-specific extraction notes.

## Core principle

Stoned Lack extraction creates a podcast source package, not active Knowledge and not a Mighty Giants recommendation.

Source package:

```text
sources/podcasts/stoned-lack/episodes/YYYY/sl_XXXX/
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

Store all structured Stoned Lack source takes for the episode in one categorized `takes.json`.

Use the shared categories:

- `players`
- `teams`
- `positions`
- `nfl`
- `fantasy`
- `other`

Do not create one JSON file per take by default.

For player takes, include identity-resolution fields when the transcript does not provide a clearly verified canonical full name:

- `raw_entity_mention`
- `entity`
- `team`
- `position`
- `entity_resolution`

## Stoned Lack extraction focus

When processing a Stoned Lack transcript, extract:

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

Automatic German transcripts often break English NFL player names, and German hosts may also use only last names, shortened names, college references or informal phrasing.

For important entities, preserve uncertainty in `takes.json` using `entity_resolution`, notes, tags or confidence wording.

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

## Stoned Lack player-name quality gate

Do not treat a Stoned Lack player take as complete when the player name is only a surname, a likely mistranscription or a guessed full name.

Bad final entities include examples like:

- `Price` when the take is about a Seattle RB and the full player identity must be resolved.
- `Jeremy Love` when the context indicates a similar but different canonical player name.

In these cases, either verify the canonical full player name from context and external identity sources, or keep the take unresolved.

A resolved player take should make the mapping auditable:

```json
"raw_entity_mention": "Price",
"entity": "Jadarian Price",
"team": "SEA",
"position": "RB",
"entity_resolution": {
  "status": "confirmed",
  "confidence": "high",
  "reason": "Podcast context says Seattle RB / rookie draft; external identity source confirms the canonical full name.",
  "candidates": [
    {
      "name": "Jadarian Price",
      "match_reason": "Seattle RB context matches."
    }
  ],
  "verified_sources": [
    "external identity check required at extraction time"
  ]
}
```

An unresolved player take should not pretend certainty:

```json
"raw_entity_mention": "Price",
"entity": null,
"entity_resolution": {
  "status": "unresolved",
  "confidence": "low",
  "reason": "Surname-only transcript mention; context was insufficient or verification was not completed.",
  "candidates": [
  ],
  "verified_sources": [
  ]
}
```

## Alias handling

Stoned Lack is German-language fantasy content about mostly English player, team and college names. Watch especially for:

- phonetic German transcript variants of English names
- missing suffixes such as `Jr.`
- confused similar first/last names
- college-only references in rookie discussions
- nicknames, shortened names and host-specific wording

Do not change raw transcript wording.

If a mapping is likely but not certain, keep the entity unresolved or mark confidence as low.

If a recurring alias or transcript error is confirmed, store it in the central podcast alias registry defined in `fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md`.

Do not maintain a separate Stoned Lack-only alias index unless the user explicitly asks for source-local aliases.

## Completeness gate

A Stoned Lack episode package is complete when:

1. raw source is present in `raw/` and referenced in `raw/manifest.md` and `index.json`
2. `episode.md` is a clean German source summary without internal metadata
3. `takes.json` exists and uses all six shared categories
4. all high-signal player statements are represented under `players`
5. team/depth-chart statements are represented under `teams`
6. position-group statements are represented under `positions`
7. fantasy strategy and format statements are represented under `fantasy`
8. cautious, negative and uncertainty takes are included, not only positive takes
9. unresolved or low-confidence identities are visible in the summary or takes
10. every important player take has either a verified canonical full player name or explicit unresolved/ambiguous `entity_resolution`
11. recurring transcript aliases were reviewed and confirmed mappings were stored centrally, if any exist
12. `index.json` records package paths, raw status and take counts
13. no active Knowledge or Mighty Giants recommendations are mixed into the source package

## Knowledge handoff

After extraction, a separate Knowledge derivation step may read the episode package and decide what applies to:

- `fantasy-management/knowledge/players/`
- `fantasy-management/knowledge/teams/`
- `fantasy-management/knowledge/positions/`
- `fantasy-management/knowledge/nfl/`
- `fantasy-management/knowledge/fantasy/`

Do not copy every Stoned Lack take into Knowledge. Redraft-only or irrelevant takes may stay only in the source package.
