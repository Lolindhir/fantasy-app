# Podcast Extraction Rules

Purpose: central extraction rules for all podcast sources in Fantasy Management.

Use these rules for StoneLack/StonedLack, Down Set Talk, Football Bromance and future podcast sources.

## Canonical source configuration

Podcast source identity, weighting and profile comparison are maintained centrally in:

`fantasy-management/_ai/source-registry.json`

Podcast-specific quirks, aliases and interpretation notes belong next to the source in:

`sources/podcasts/{source_id}/SOURCE_NOTES.md`

Do not maintain source weights in multiple places.

## Central template rule

Central podcast templates live under:

`fantasy-management/_ai/templates/podcast/`

Use these templates for all podcast sources unless the user explicitly requests a different structure:

- `raw_manifest_template.md`
- `episode_analysis_template.md`
- `episode_metadata_template.json`
- `episode_player_data_template.json`
- `source_take_template.json`
- `take_index_template.md`
- `current_source_view_template.md`

Source-specific guides may add source quirks, alias notes or weighting guidance, but they must not redefine the common episode, take, player-data or rollup structure.

## Focus rule

Default podcast extraction is episode-local first.

A normal extraction should focus on creating a complete, reusable package for the single episode being processed. Do not try to maintain every global index or cross-source lookup file during the same chat unless the user explicitly asks for an index rebuild.

Required default outputs:

1. raw source material or ordered raw parts plus manifest
2. German ai-input-style episode analysis
3. player/entity data JSON when the episode contains reusable player, team, ranking, tier, board or role content
4. episode JSON linking the local companion files and canonical take IDs
5. atomic source takes with stable IDs and matching file names
6. German take index when many takes are produced
7. current source view only when the extraction should feed reusable later analysis

Global indexes are derived lookup helpers. They are not source of truth. Empty or incomplete global index files are acceptable if they are treated as pending/backfill targets and are not used as complete knowledge.

## Layer model

Process podcast material through these layers:

1. raw source material
2. German ai-input-style episode analysis
3. player/entity data JSON
4. episode JSON
5. atomic source takes
6. episode-local take index
7. optional current source view
8. optional global index rebuild
9. Mighty Giants analysis

## Language and readability rule

Human-facing podcast summaries, episode notes, player profiles, take indexes, board notes, current rollups and source summaries must be written in German unless the user explicitly requests another language.

Machine-readable JSON keys stay stable and may use English field names, but user-facing values such as summaries, arguments, risks and notes should be German where practical.

The target quality for full podcast extraction is the older `ai-input` style: a readable German analysis that the user can understand without opening the raw transcript, plus machine-readable JSON for later agents.

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

Do not write one-line JSON for podcast/source extraction artifacts such as:

- episode JSON
- player/entity data JSON
- source take JSON
- source registry JSON
- owner registry JSON
- manually maintained indexes or rollups

Do not use inline arrays such as `["tag1", "tag2"]` or `["take_id"]` in Fantasy Management JSON. Empty arrays may remain as `[]`.

Compact one-line JSON is only acceptable for generated application/runtime data outside Fantasy Management when the generator owns the format.

## Raw source rule

Store raw transcripts or raw notes unchanged under:

`sources/podcasts/{source_id}/raw_transcripts/YYYY/`

Do not clean, rewrite or normalize the raw source file. If a better transcript becomes available, save a new version instead of overwriting the old trace.

A placeholder raw file is not a completed raw source. If the full transcript cannot be committed, mark the whole extraction as incomplete and do not treat downstream notes or takes as complete.

If a single large raw file cannot be committed, split the raw transcript into ordered parts and create a raw manifest. The episode JSON must then state the split raw status and parts directory. The ordered concatenation of the parts is the raw source for that episode.

## Episode rule

For every processed episode, create:

- a readable German episode analysis under `sources/podcasts/{source_id}/episodes/YYYY/`
- a machine-readable episode JSON under `sources/podcasts/{source_id}/episodes/YYYY/`
- a player/entity data JSON under `sources/podcasts/{source_id}/episodes/YYYY/` when the episode contains reusable player, team, tier, ranking or board content
- a German take index under `sources/podcasts/{source_id}/episodes/YYYY/` when many atomic takes are created

The episode analysis should not be a short summary only. For full draft-review, ranking, rookie-board, player-preview, landing-spot or strategy episodes it should include:

1. source note and cleanup
2. interpretation of the episode type
3. source philosophy / evaluation logic
4. explicit rankings, tiers, boards or category lists when present
5. sleepers, buy/sell/hold/fade/watchlist and caution buckets
6. detailed player/entity profiles with positives, risks and analysis tags
7. strategy and format-dependent notes
8. unresolved entity questions
9. reuse notes for Mighty Giants and the league format where relevant
10. links or references to companion files, player data JSON, take index and atomic takes

The episode JSON must reference every extracted take in `take_ids`. An empty or obviously incomplete `take_ids` list means the episode extraction is incomplete.

## Player/entity data JSON rule

When an episode contains reusable player, team, ranking, tier or board information, create a companion data file such as:

`sources/podcasts/{source_id}/episodes/YYYY/{episode_slug}_player_data.json`

Use a stable schema-like shape with:

- `metadata`
- `schema`
- `players` or `entities`
- optional `category_rankings`

For each player/entity, include as applicable:

- rank
- name
- position
- team
- source tier
- sentiment
- source conviction
- main argument
- opportunity / path to touches or targets
- short-term value
- long-term value
- risk
- format dependency
- linked take IDs
- tags
- notes
- confidence or verification status when identity is uncertain

This file should be player-centric and easier to aggregate than atomic takes. Atomic takes remain the evidence layer; player/entity data is the readable structured profile layer.

## Atomic take rule

Extract reusable takes at the smallest useful unit.

A take should usually cover one player, team, role, market point, format note or strategy point.

Do not collapse an entire episode into only a few summary takes when the transcript contains many player evaluations, rankings, tiers, sleepers, fades, buy/sell/hold notes, strategy notes or format notes.

Each take should keep these concepts separate:

- original source statement
- cleaned entity mapping
- AI interpretation
- evidence reference
- freshness / current relevance

For podcast extraction, every new atomic take should use the explicit field names from the current StonedLack 569 take pattern:

- `source_statement`: what the podcast/source said, without turning it into a final recommendation
- `cleaned_entity_mapping`: canonical entity, entity type, team/position when known, raw transcript forms and confidence
- `ai_interpretation`: how the statement should be interpreted for fantasy reuse, Mighty Giants or the league format
- `arguments`: reusable reasons supporting the take
- `risks`: uncertainty, downside or reasons to avoid overuse
- `evidence`: timestamped paraphrase or short excerpt
- `episode_local_scope`: links or metadata for local package context, including `global_index_update: "deferred"` when global indexes are not updated

Do not write one-line JSON takes for new podcast extractions. Every take JSON must be pretty-printed with two-space indentation, readable line breaks and exactly one array item per line.

Use stable take IDs and file names. Prefer `episode_id_tNNN.json` so `take_id` and file name can be matched mechanically. If legacy or descriptive file names exist, the episode JSON must clearly declare the canonical take file pattern.

## Indexing rule

Episode-local indexes are part of the extraction package. Create or update them when useful:

- the episode JSON
- the German take index
- optional episode-local entity map
- optional episode-local board/tier notes

Global indexes and cross-file lookup metadata are separate derived artifacts. Do not update them during normal podcast extraction unless explicitly requested.

Examples of deferred global index work:

- cross-source player index
- source-wide take index
- team-wide signal index
- global `fantasy-management/indexes/` lookup files
- regenerated knowledge-layer lookup tables

If a global index file exists but is empty, treat it as pending/backfill unless it explicitly claims to be current. Do not use an empty global index as evidence that no data exists.

## Current view rule

Historical takes stay in `derived/knowledge/takes/`.

The current working view stays in `derived/knowledge/current/`.

Do not delete older takes just because later context changes the evaluation. Move old context out of the current view instead.

The current view should be derived from the normalized take and player/entity data layers, not only from a loose summary.

Current views are useful but not always mandatory in the same chat. For long podcast episodes, prefer completing the episode-local package first. Update current views when the user requests persistence for later analysis or when the extraction is intended to be reused directly.

## Completeness gate

Before marking an extraction as complete, verify:

1. the raw transcript is present and not a placeholder
2. if raw is split, ordered parts and a raw manifest exist and the episode JSON states the split raw status
3. all meaningful player, team, coach, format and strategy mentions were reviewed
4. every high-signal player in the episode note has at least one atomic take or an explicit reason why no take was created
5. every high-signal player/entity profile is also represented in the player/entity data JSON when such a JSON is required
6. caution, fade, uncertainty and negative takes are extracted, not only positive takes
7. episode JSON `take_ids` matches the canonical take files created
8. episode JSON references the player/entity data JSON when present
9. unresolved names and entity-mapping issues are listed in the episode note or companion entity file
10. the German episode analysis is sufficiently detailed to stand alone without opening the raw transcript
11. current views are updated when required by the task scope, or explicitly deferred
12. global indexes are not required for extraction completeness unless the task is an index rebuild
13. new podcast take files include `source_statement`, `cleaned_entity_mapping`, `ai_interpretation`, `arguments`, `risks`, `evidence` and `episode_local_scope`
14. JSON files created or updated as part of the extraction are pretty-printed with two-space indentation, not one-line JSON
15. non-empty JSON arrays have one item per line, including single-item arrays

If any required item fails, mark the extraction as `incomplete` or `needs_rework` and explain what is missing.

## Entity resolution rule

Use source-specific notes for common aliases and transcript quirks.

If a player, team or claim is uncertain, mark it as uncertain instead of guessing.

When decision-relevant, verify identity and current context against current repo data and fresh external sources if needed.

Do not invent non-mentions. If a prominent player from another episode or board is not clearly mentioned in the current transcript, do not add a profile just to fill a gap. Only add a `not mentioned / not found` note when it is directly useful for the episode's stated scope or the user asks.

## Recommendation rule

Podcast output is source context, not a final recommendation.

Final Mighty Giants recommendations belong under `fantasy-management/analyses/` and must combine current league data, current knowledge view, take history when relevant and external context when needed.
