# StonedLack Repository Structure

StonedLack source data lives under:

`fantasy-management/sources/podcasts/stonedlack/`

## Structure

```text
stonedlack/
  README.md
  STONEDLACK_EXTRACTION_GUIDE.md
  STONEDLACK_REPO_STRUCTURE.md
  schemas/
    stonedlack_take_schema.json
  raw_transcripts/
    YYYY/
      YYYY-MM-DD_sl_EPISODE_slug.raw.md
  episodes/
    YYYY/
      YYYY-MM-DD_sl_EPISODE_slug.md
      YYYY-MM-DD_sl_EPISODE_slug.json
  indexes/
    player_aliases.json
    episode_index.json
    take_index.json
```

## Responsibilities

- `raw_transcripts/` stores the primary transcript trace.
- `episodes/` stores readable Markdown source notes and machine-readable JSON files.
- `schemas/` stores source-specific JSON schemas.
- `indexes/` stores cross-episode lookup data.

## Migration note

Older StonedLack files may have existed under `ai-input/stonedlack/`.

New StonedLack work should be written only under this folder.
