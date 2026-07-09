# Fantasy Management Workflows

Purpose: reusable agent workflows for Fantasy Management tasks.

## General workflow

1. Read `fantasy-management/AGENTS.md`.
2. Read source and rule files under `fantasy-management/_ai/`.
3. Read `fantasy-management/_ai/PODCAST_SOURCE_MODEL.md` when podcast source packages, source takes or Knowledge derivation matter.
4. Read `fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md` and `fantasy-management/_ai/source-registry.json` when podcast/source extraction matters.
5. Read `fantasy-management/_ai/entity-resolution/player_identity_registry.json` when player names, aliases, transcript errors or source extraction matter.
6. Read `fantasy-management/league-context/` when owner identity, user perspective, league format interpretation, trade talks or negotiation history matter.
7. Identify whether the task needs current app data from `public/data/`.
8. Load only the required current data.
9. Load relevant source packages, source notes, league context, Knowledge, analysis or decision files.
10. Distinguish stable facts from dynamic values.
11. Store outputs in the correct Fantasy Management folder when persistence is requested.

## Player analysis workflow

1. Load current league format and scoring.
2. Identify Mighty Giants context.
3. Load the player's current internal data.
4. Load `fantasy-management/league-context/league-format-notes.md` when format interpretation matters.
5. Load player Knowledge from `fantasy-management/knowledge/players/` if available.
6. Load team Knowledge from `fantasy-management/knowledge/teams/` for the player's NFL team if available.
7. Load position Knowledge from `fantasy-management/knowledge/positions/` if available.
8. Load relevant podcast source package takes as evidence when needed.
9. Check role, production, game history, age, salary and availability context.
10. Add external market context only when current value matters.
11. Produce a recommendation label.
12. Store under `fantasy-management/analyses/YYYY/players/` if requested.

## Trade analysis workflow

1. Resolve every owner, player and pick in the trade.
2. Load `fantasy-management/league-context/owner-registry.json` for user, owner and TeamID references.
3. Load `fantasy-management/league-context/owner-profiles.md` for manager tendencies when a counterparty is involved.
4. Load `fantasy-management/league-context/trade-negotiation-history.md` for prior talks or trade references involving the counterparty.
5. Load `fantasy-management/league-context/league-format-notes.md` for stable format interpretation.
6. Load current Mighty Giants roster, picks and cap/salary context.
7. Resolve draft-pick metadata through `Drafts.json`.
8. Load current Knowledge and relevant source package takes for involved players when relevant.
9. Compare win-now points, long-term value, roster construction, salary impact, liquidity and counterparty fit.
10. Check external market context if value calibration matters.
11. Give a clear recommendation from the Mighty Giants perspective unless another perspective is requested.
12. Store under `fantasy-management/analyses/YYYY/trades/` if requested.

## Roster audit workflow

1. Load current `League.json`, `Metadata.json`, roster format and scoring.
2. Identify Mighty Giants by `TeamID = 1`.
3. Load `fantasy-management/league-context/league-format-notes.md` for format interpretation.
4. Map roster, reserve and taxi players to current player records.
5. Load relevant player, team and position Knowledge when useful.
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
7. Add player/team/position Knowledge for candidate players when relevant.
8. Evaluate remaining candidates by position, production, role, age, format fit and salary.
9. Verify top candidates through player records.
10. Store boards under `fantasy-management/analyses/YYYY/free-agent-boards/` if requested.

## Podcast workflow

Use this for Stoned Lack, Down Set Talk, Football Bromance and later podcast sources.

Default rule: keep each podcast episode as one local source package. Do not create active Knowledge or global indexes during normal extraction.

1. Read `fantasy-management/_ai/PODCAST_SOURCE_MODEL.md`.
2. Read `fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md`.
3. Read central podcast templates under `fantasy-management/_ai/templates/podcast/` and use them as the default structure.
4. Load source identity, weighting and profile context from `fantasy-management/_ai/source-registry.json`.
5. Load podcast-independent player aliases and previous identity mappings from `fantasy-management/_ai/entity-resolution/player_identity_registry.json`.
6. Load source-specific quirks from `sources/podcasts/{source_id}/SOURCE_NOTES.md` when present.
7. Create or update the episode package under `sources/podcasts/{source_id}/episodes/{year}/{episode_id}/`.
8. Store unchanged raw source under the package's `raw/` folder. If the raw source is split, create `raw/manifest.md`.
9. Create `episode.md` as a clean German podcast summary without internal metadata, file lists, take IDs or Mighty Giants recommendations.
10. Create `takes.json` with categorized source takes under `players`, `teams`, `positions`, `nfl`, `fantasy` and `other`.
11. For every player take in `takes.json`, include inline `raw_entity_mention`, canonical `entity`, and `entity_resolution`.
12. Do not use a companion `entity_resolution.json` file as a substitute for inline player resolution in `takes.json`. Companion files are allowed only as temporary migration overlays for legacy packages and must keep the package from being marked fully complete.
13. Add confirmed reusable aliases or transcript-error mappings to `fantasy-management/_ai/entity-resolution/player_identity_registry.json`.
14. Create `index.json` with local package metadata, paths, raw status, take counts, identity-resolution status and extraction status.
15. Write all Fantasy Management JSON artifacts as readable, pretty-printed JSON with two-space indentation, one property per line and arrays split across lines.
16. Run the extraction completeness gate from `PODCAST_EXTRACTION_RULES.md` before marking the package complete.
17. Do not update `fantasy-management/knowledge/` unless the user explicitly asks for Knowledge derivation.
18. Do not invent missing details or non-mentions.

## Knowledge derivation workflow

Use this after one or more source packages are complete.

1. Read relevant podcast source packages under `sources/podcasts/{source_id}/episodes/{year}/{episode_id}/`.
2. Treat `episode.md` and `takes.json` as source evidence, not final truth.
3. If a legacy package has a temporary entity-resolution overlay, merge that identity context explicitly and treat the package as not fully normalized until `takes.json` is fixed inline.
4. Load current league format, Mighty Giants context and current app data when relevance depends on them.
5. Decide whether each relevant source take applies to our Dynasty league, 6-team format, 2QB/2TE/4Flex settings, roster context and current market context.
6. Ignore or de-prioritize source takes that are purely redraft and have no Dynasty, market or strategy relevance.
7. Store derived Knowledge under:

```text
fantasy-management/knowledge/players/
fantasy-management/knowledge/teams/
fantasy-management/knowledge/positions/
fantasy-management/knowledge/nfl/
fantasy-management/knowledge/fantasy/
```

8. Link back to source packages and take IDs for evidence.
9. Keep Knowledge separate from final recommendations.

## Index rebuild workflow

Use this only when the user explicitly asks to rebuild indexes or when a maintenance task is clearly about indexes.

1. Read the relevant completed local episode packages.
2. Treat episode package files as source-of-truth inputs for source material.
3. Rebuild global indexes from completed source packages or Knowledge files rather than hand-maintaining them during extraction.
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

## Decision logging workflow

When the user makes a decision, log it under the matching file in `fantasy-management/decisions/YYYY/`.

Use a short entry containing date, decision type, involved assets, context, final decision, reason, source analysis link if available and follow-up date or watch condition if relevant.

## File naming

Prefer date-prefixed filenames for analyses and decisions:

```text
YYYY-MM-DD_short-slug.md
YYYY-MM-DD_short-slug.json
```

Podcast episode packages should use stable episode IDs such as:

```text
sl_0569/
dst_2026-07-01_short-topic/
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
