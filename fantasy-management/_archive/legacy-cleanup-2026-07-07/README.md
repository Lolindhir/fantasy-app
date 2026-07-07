# Legacy Cleanup Archive – 2026-07-07

Purpose: temporary archive marker for files removed from the active Fantasy Management structure during the podcast package cleanup.

The active structure is now:

```text
fantasy-management/sources/podcasts/{source_id}/episodes/{year}/{episode_id}/
  raw/
  episode.md
  takes.json
  index.json

fantasy-management/knowledge/
  players/
  teams/
  positions/
  nfl/
  fantasy/
```

## Cleanup principle

Legacy source-extraction files were removed from active folders when their content was superseded by the new episode package structure.

For StonedLack 569, the active source package is now:

`fantasy-management/sources/podcasts/stonedlack/episodes/2026/sl_0569/`

## Removed legacy classes

- flat StonedLack 569 episode files under `episodes/2026/`
- old StonedLack 569 companion markdown files
- old StonedLack 569 player-data and metadata JSON files
- old per-take JSON files under `derived/knowledge/takes/stonedlack/2026/`
- old source rollup files under `derived/knowledge/current/`
- legacy podcast templates replaced by the simplified package templates
- legacy derived knowledge process file replaced by the new source/Knowledge separation model

## Deletion safety

This `_archive/legacy-cleanup-2026-07-07/` folder is intentionally small and can be deleted after the new structure has been reviewed.

Exact historical file contents remain available through Git history if needed.
