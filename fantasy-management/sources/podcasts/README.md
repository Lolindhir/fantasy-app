# Podcast Sources

Structured podcast source material for Fantasy Management.

Each podcast source keeps its own source notes and episode packages.

## Episode package structure

```text
sources/podcasts/{source_id}/episodes/{year}/{episode_id}/
  raw/
  episode.md
  takes.json
  index.json
```

## File roles

- `raw/` contains the raw transcript or ordered raw transcript parts.
- `episode.md` is the clean German podcast summary without internal metadata or recommendations.
- `takes.json` contains structured source takes grouped by `players`, `teams`, `positions`, `nfl`, `fantasy` and `other`.
- `index.json` contains local technical metadata and take counts.

Podcast source material is evidence. It is not active Knowledge and not a Mighty Giants recommendation.
