# StonedLack

This folder contains structured source packages for StonedLack podcast episodes.

StonedLack is a qualitative source perspective. It must not override current league data, current market data or final Mighty Giants recommendations.

## Active structure

For each processed episode, use one episode package:

```text
sources/podcasts/stonedlack/episodes/{year}/{episode_id}/
  raw/
  episode.md
  takes.json
  index.json
```

## File roles

- `raw/` contains the raw transcript or ordered raw transcript parts.
- `episode.md` is the clean German podcast summary from the podcast perspective.
- `takes.json` contains categorized StonedLack source takes.
- `index.json` contains local package metadata and take counts.

Use `STONEDLACK_EXTRACTION_GUIDE.md` for StonedLack-specific extraction notes.

Use central podcast templates under `fantasy-management/_ai/templates/podcast/`.

Do not create one JSON file per take by default.

Do not write StonedLack podcast takes into a separate derived take area by default.
