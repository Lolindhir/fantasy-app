# Fantasy Management Workflows

Purpose: reusable agent workflows for Fantasy Management tasks.

## General workflow

1. Read `fantasy-management/AGENTS.md`.
2. Read source and rule files under `fantasy-management/_ai/`.
3. Read `fantasy-management/_ai/knowledge-layer.yaml` and `fantasy-management/derived/knowledge/PROCESS.md` when source context matters.
4. Read `fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md` and `fantasy-management/_ai/source-registry.json` when podcast/source extraction matters.
5. Identify whether the task needs current app data from `public/data/`.
6. Load only the required current data.
7. Load relevant source, source notes, knowledge, analysis or decision files.
8. Distinguish stable facts from dynamic values.
9. Store outputs in the correct Fantasy Management folder when persistence is requested.

## Player analysis workflow

1. Load current league format and scoring.
2. Identify Mighty Giants context.
3. Load the player's current internal data.
4. Load the current source-derived player view from `derived/knowledge/current/players/` if available.
5. Load take history from `derived/knowledge/takes/by_player/` when evidence or history matters.
6. Check role, production, game history, age, salary and availability context.
7. Add external market context only when current value matters.
8. Produce a recommendation label.
9. Store under `fantasy-management/analyses/YYYY/players/` if requested.

## Trade analysis workflow

1. Resolve every player and pick in the trade.
2. Load current Mighty Giants roster, picks and cap/salary context.
3. Resolve draft-pick metadata through `Drafts.json`.
4. Load current source-derived views for involved players when relevant.
5. Compare win-now points, long-term value, roster construction and liquidity.
6. Check external market context if value calibration matters.
7. Give a clear recommendation.
8. Store under `fantasy-management/analyses/YYYY/trades/` if requested.

## Roster audit workflow

1. Load current `League.json`, `Metadata.json`, roster format and scoring.
2. Identify Mighty Giants by `TeamID = 1`.
3. Map roster, reserve and taxi players to current player records.
4. Load relevant current source-derived player views when useful.
5. Cluster by position.
6. Categorize players into role buckets.
7. Evaluate salary/cap separately from quality.
8. Review picks and trade liquidity.
9. Identify upgrade targets, package pieces, stashes and cut risks.
10. Store under `fantasy-management/analyses/YYYY/roster/` if requested.

## Free-agent board workflow

1. Load current `League.json`.
2. Build the owned-ID set from every team roster, reserve and taxi list.
3. Load `public/data/chat/players-relevant/index.json`.
4. Load required player chunks.
5. Exclude every owned ID.
6. Add current source-derived views for candidate players when relevant.
7. Evaluate remaining candidates by position, production, role, age, format fit and salary.
8. Verify top candidates through player records.
9. Store boards under `fantasy-management/derived/free-agent-boards/YYYY/`.

## Podcast workflow

Use this for StoneLack/StonedLack, Down Set Talk, Football Bromance and later podcast sources.

1. Read `fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md`.
2. Load source identity, weighting and profile context from `fantasy-management/_ai/source-registry.json`.
3. Load source-specific quirks from `sources/podcasts/{source_id}/SOURCE_NOTES.md` when present.
4. Store the unchanged source file under `sources/podcasts/{source_id}/raw_transcripts/YYYY/` when requested.
5. Create an episode note under `sources/podcasts/{source_id}/episodes/YYYY/`.
6. Create an episode JSON under `sources/podcasts/{source_id}/episodes/YYYY/`.
7. Extract atomic takes with source metadata, entity mapping, sentiment, conviction, evidence and freshness fields.
8. Update `derived/knowledge/takes/` by player, team and source when requested.
9. Update `derived/knowledge/current/` as the latest source-derived working view.
10. Keep source statement, entity cleanup and AI interpretation separate.
11. Do not invent missing details.

## Knowledge-layer update workflow

1. Resolve source IDs through `fantasy-management/_ai/source-registry.json`.
2. Resolve player and team aliases through `derived/knowledge/entities/` and source-specific notes.
3. Group takes by player, team and source.
4. Compare new takes against older related takes.
5. Move inactive information out of the current view without deleting history.
6. Refresh current player, team, role, trend and market views under `derived/knowledge/current/`.
7. Keep historical evidence under `derived/knowledge/takes/`.

## Decision logging workflow

When the user makes a decision, log it under the matching file in `fantasy-management/decisions/YYYY/`.

Use a short entry containing date, decision type, involved assets, context, final decision, reason, source analysis link if available and follow-up date or watch condition if relevant.

## File naming

Prefer date-prefixed filenames:

```text
YYYY-MM-DD_short-slug.md
YYYY-MM-DD_short-slug.json
```

## Analysis frontmatter

Use frontmatter for stored Markdown analyses when useful:

```yaml
---
type: player_analysis
scope: fantasy-management
created: YYYY-MM-DD
team_context: Mighty Giants
data_sources:
  - public/data/League.json
status: active
supersedes: null
validity_note: "Dynamic evaluation; re-check current data before reuse."
---
```
