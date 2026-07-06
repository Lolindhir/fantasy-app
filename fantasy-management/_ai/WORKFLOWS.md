# Fantasy Management Workflows

Purpose: reusable agent workflows for Fantasy Management tasks.

## General workflow

1. Read `fantasy-management/AGENTS.md`.
2. Read source and rule files under `fantasy-management/_ai/`.
3. Read `fantasy-management/_ai/knowledge-layer.yaml` and `fantasy-management/derived/knowledge/PROCESS.md` when source context matters.
4. Read `fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md` and `fantasy-management/_ai/source-registry.json` when podcast/source extraction matters.
5. Read `fantasy-management/league-context/` when owner identity, user perspective, league format interpretation, trade talks or negotiation history matter.
6. Identify whether the task needs current app data from `public/data/`.
7. Load only the required current data.
8. Load relevant source, source notes, league context, knowledge, analysis or decision files.
9. Distinguish stable facts from dynamic values.
10. Store outputs in the correct Fantasy Management folder when persistence is requested.

## Player analysis workflow

1. Load current league format and scoring.
2. Identify Mighty Giants context.
3. Load the player's current internal data.
4. Load `fantasy-management/league-context/league-format-notes.md` when format interpretation matters.
5. Load the current source-derived player view from `derived/knowledge/current/players/` if available.
6. Load take history from `derived/knowledge/takes/by_player/` when evidence or history matters.
7. Check role, production, game history, age, salary and availability context.
8. Add external market context only when current value matters.
9. Produce a recommendation label.
10. Store under `fantasy-management/analyses/YYYY/players/` if requested.

## Trade analysis workflow

1. Resolve every owner, player and pick in the trade.
2. Load `fantasy-management/league-context/owner-registry.json` for user, owner and TeamID references.
3. Load `fantasy-management/league-context/owner-profiles.md` for manager tendencies when a counterparty is involved.
4. Load `fantasy-management/league-context/trade-negotiation-history.md` for prior talks or trade references involving the counterparty.
5. Load `fantasy-management/league-context/league-format-notes.md` for stable format interpretation.
6. Load current Mighty Giants roster, picks and cap/salary context.
7. Resolve draft-pick metadata through `Drafts.json`.
8. Load current source-derived views for involved players when relevant.
9. Compare win-now points, long-term value, roster construction, salary impact, liquidity and counterparty fit.
10. Check external market context if value calibration matters.
11. Give a clear recommendation from the Mighty Giants perspective unless another perspective is requested.
12. Store under `fantasy-management/analyses/YYYY/trades/` if requested.

## Roster audit workflow

1. Load current `League.json`, `Metadata.json`, roster format and scoring.
2. Identify Mighty Giants by `TeamID = 1`.
3. Load `fantasy-management/league-context/league-format-notes.md` for format interpretation.
4. Map roster, reserve and taxi players to current player records.
5. Load relevant current source-derived player views when useful.
6. Cluster by position.
7. Categorize players into role buckets.
8. Evaluate salary/cap separately from quality.
9. Review picks and trade liquidity.
10. Identify upgrade targets, package pieces, stashes and cut risks.
11. Store under `fantasy-management/analyses/YYYY/roster/` if requested.

## Free-agent board workflow

1. Load current `League.json`.
2. Build the owned-ID set from every team roster, reserve and taxi list.
3. Load `public/data/chat/players-relevant/index.json`.
4. Load required player chunks.
5. Exclude every owned ID.
6. Load `fantasy-management/league-context/league-format-notes.md` when format interpretation matters.
7. Add current source-derived views for candidate players when relevant.
8. Evaluate remaining candidates by position, production, role, age, format fit and salary.
9. Verify top candidates through player records.
10. Store boards under `fantasy-management/derived/free-agent-boards/YYYY/`.

## Podcast workflow

Use this for StoneLack/StonedLack, Down Set Talk, Football Bromance and later podcast sources.

Default rule: build a complete local episode package first. Do not try to maintain global indexes during normal extraction.

1. Read `fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md`.
2. Load source identity, weighting and profile context from `fantasy-management/_ai/source-registry.json`.
3. Load source-specific quirks from `sources/podcasts/{source_id}/SOURCE_NOTES.md` when present.
4. Store the unchanged source file under `sources/podcasts/{source_id}/raw_transcripts/YYYY/` when requested. If a single large raw write is blocked, create ordered raw parts plus a manifest and reference it from episode JSON.
5. Create a German ai-input-style episode analysis under `sources/podcasts/{source_id}/episodes/YYYY/`.
6. Create a player/entity data JSON under `sources/podcasts/{source_id}/episodes/YYYY/` when the episode contains reusable player, team, tier, ranking, board or role content.
7. Create an episode JSON under `sources/podcasts/{source_id}/episodes/YYYY/` and link the raw manifest/status, local companion files, player/entity data path and canonical take IDs.
8. Extract atomic takes with source metadata, entity mapping, sentiment, conviction, evidence and freshness fields.
9. Every new podcast take should include `source_statement`, `cleaned_entity_mapping`, `ai_interpretation`, `arguments`, `risks`, `evidence` and `episode_local_scope`.
10. Use stable take IDs and matching file names such as `episode_id_tNNN.json`.
11. Create a German episode-local take index when many takes are produced.
12. Optionally update `derived/knowledge/current/` as the latest source-derived working view when requested or when the extraction should feed reusable analysis.
13. Do not update global indexes or cross-source lookup files unless the user explicitly asks for an index rebuild.
14. Run the extraction completeness gate from `PODCAST_EXTRACTION_RULES.md` and any source-specific guide before marking the extraction complete.
15. If raw source is only a placeholder, German analysis is only a short summary, player data is missing for a board-style episode, take coverage is sparse, take files miss the explicit podcast-take fields, or episode JSON does not reference all canonical takes, mark the extraction `incomplete` or `needs_rework`.
16. If current views or global indexes are deferred, state that explicitly in the episode note or final response.
17. Keep source statement, entity cleanup and AI interpretation separate.
18. Do not invent missing details or non-mentions.

## Index rebuild workflow

Use this only when the user explicitly asks to rebuild indexes or when a maintenance task is clearly about indexes.

1. Read the relevant completed local episode packages.
2. Treat episode Markdown, episode JSON, player/entity data JSON and canonical take files as source-of-truth inputs.
3. Rebuild global indexes from existing completed files rather than hand-maintaining them during extraction.
4. Mark rebuilt indexes with generated/backfill status and the input files used.
5. Empty indexes are allowed only if they are clearly marked as pending/backfill or generated from zero inputs.

## League-context update workflow

Use this when the user gives information about manager tendencies, trade talks, negotiation outcomes, owner aliases or league-format interpretation.

1. Resolve owner references through `league-context/owner-registry.json` and current `Metadata.json`.
2. If the update is a stable alias or owner identity note, update `owner-registry.json`.
3. If the update is a manager tendency or recurring behavior, update `owner-profiles.md`.
4. If the update is a concrete trade talk, offer, counter, rejection or completed negotiation, update `trade-negotiation-history.md`.
5. If the update is a stable format interpretation, update `league-format-notes.md` or `_ai/FANTASY_MANAGEMENT_RULES.md` depending on durability.
6. Keep dynamic roster, pick and salary facts out of league-context files unless clearly marked as historical context.

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
