# StonedLack Source Notes

This folder contains structured extractions from StonedLack podcast episodes.

## Workflow

For each episode, store three artifacts:

1. raw transcript under `raw_transcripts/YYYY/`
2. readable Markdown source note under `episodes/YYYY/`
3. machine-readable JSON data file under `episodes/YYYY/`

Use `STONEDLACK_EXTRACTION_GUIDE.md` for extraction rules.

Use `schemas/stonedlack_take_schema.json` for StonedLack-specific source-take JSON.

Use `indexes/` for episode, player-alias and take indexes.

StonedLack is a qualitative source perspective. It must not override current league data, current market data or final Mighty Giants recommendations.
