# Podcast Templates

Purpose: central reusable templates for all Fantasy Management podcast source packages.

These templates apply to all podcast sources, including:

- StonedLack
- Down Set Talk
- Football Bromance
- future podcast sources

Source-specific guides may add quirks, alias handling or weighting notes, but they should not redefine the common output structure.

## Current templates

Use these templates for new podcast extractions:

- `episode_summary_template.md` — clean German reader-facing podcast summary without internal metadata.
- `episode_takes_template.json` — categorized source takes for one episode.
- `episode_index_template.json` — local technical package map.
- `raw_manifest_template.md` — manifest for split raw transcripts.

## Legacy templates

The following older templates may remain temporarily for migration compatibility but should not define new extraction structure:

- `episode_analysis_template.md`
- `episode_metadata_template.json`
- `episode_player_data_template.json`
- `source_take_template.json`
- `take_index_template.md`
- `current_source_view_template.md`

## Default episode package

A normal podcast extraction should create:

```text
sources/podcasts/{source_id}/episodes/{year}/{episode_id}/
  raw/
    manifest.md
    part01.md
    part02.md
  episode.md
  takes.json
  index.json
```

`episode.md` is for humans and contains only the podcast's content and source perspective.

`takes.json` is structured source material and uses these categories:

- `players`
- `teams`
- `positions`
- `nfl`
- `fantasy`
- `other`

`index.json` is the local technical package map and keeps metadata out of `episode.md`.

Global indexes and Knowledge files are intentionally not part of the default extraction package.

## JSON formatting rule

All AI-created or manually maintained Fantasy Management JSON files must stay human-readable:

- two-space indentation
- one property per line
- arrays on multiple lines, including single-item arrays
- exactly one array item per line
- nested arrays and objects on separate lines
- stable key order where practical
- trailing newline at end of file

Do not commit one-line/minified JSON or inline arrays such as `["tag1", "tag2"]`, `["take_id"]` or `[]` in Fantasy Management JSON when practical.
