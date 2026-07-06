# Podcast Templates

Purpose: central reusable templates for all Fantasy Management podcast extractions.

These templates apply to all podcast sources, including:

- StonedLack
- Down Set Talk
- Football Bromance
- future podcast sources

Source-specific guides may add quirks, alias handling or weighting notes, but they should not redefine the common output structure.

## Templates

- `episode_analysis_template.md` — German ai-input-style human-facing episode analysis.
- `episode_metadata_template.json` — episode JSON linking raw status, local companion files and canonical take IDs.
- `episode_player_data_template.json` — player/entity profile data for aggregation.
- `source_take_template.json` — canonical atomic podcast take pattern.
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
