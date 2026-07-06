# Podcast Templates

Purpose: central reusable templates for all Fantasy Management podcast extractions.

These templates apply to all podcast sources, including:

- StonedLack
- Down Set Talk
- Football Bromance
- future podcast sources

Source-specific guides may add quirks, alias handling or weighting notes, but they should not redefine the common output structure.

## Templates

- `raw_manifest_template.md` — manifest for split raw transcripts.
- `episode_analysis_template.md` — German ai-input-style human-facing episode analysis.
- `episode_metadata_template.json` — episode JSON linking raw status, local companion files and canonical take IDs.
- `episode_player_data_template.json` — player/entity profile data for aggregation.
- `source_take_template.json` — canonical atomic podcast take pattern.
- `take_index_template.md` — German local take index.
- `current_source_view_template.md` — optional current source rollup / working view.

## Default extraction package

A normal podcast extraction should create a local episode package first:

1. Raw transcript or ordered raw parts plus manifest
2. German episode analysis
3. Player/entity data JSON when the episode contains reusable player, team, tier, board, role or ranking content
4. Episode metadata JSON
5. Atomic source takes
6. German take index when many takes are produced
7. Optional current source view when needed for later reuse

Global indexes are intentionally not part of the default package. Rebuild them separately from completed local packages.

## Template rule

When creating new extraction files, start from these central templates unless the user explicitly asks for a different structure.

Source-specific files may add sections, but they should not remove the central concepts:

- German human-facing episode analysis
- local machine-readable episode metadata
- player/entity data for reusable player content
- canonical atomic takes with explicit source statement, entity mapping and AI interpretation
- local take index
- optional current source view
- deferred global indexes

## JSON formatting rule

All AI-created or manually maintained Fantasy Management JSON files must stay human-readable:

- two-space indentation
- one property per line
- arrays on multiple lines, including single-item arrays
- exactly one array item per line
- nested arrays and objects on separate lines
- stable key order where practical
- trailing newline at end of file

Do not commit one-line/minified JSON for podcast episode metadata, player/entity data, source takes, registries or manually maintained indexes.

Do not use inline arrays such as `["tag1", "tag2"]` or `["take_id"]` in Fantasy Management JSON. Empty arrays may remain as `[]`.
