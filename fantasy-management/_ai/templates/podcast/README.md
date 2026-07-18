# Podcast Templates

Purpose: reusable templates for Fantasy Management podcast source packages.

These templates apply to Stoned Lack, Down Set Talk, Football Bromance and future sources.

Source-specific guides may add quirks and interpretation notes, but they must not redefine the common package model.

## Templates

- `episode_summary_template.md` — adaptive, detailed German reader-facing preparation without internal metadata
- `episode_takes_template.json` — categorized source takes
- `episode_mentions_template.json` — complete technical entity and coverage register
- `episode_index_template.json` — technical package map and audit status
- `raw_manifest_template.md` — manifest for split raw transcripts

## Default schema-version-2 package

```text
sources/podcasts/{source_id}/episodes/{year}/{episode_id}/
  raw/
    manifest.md
    part01.md
    part02.md
  episode.md
  takes.json
  mentions.json
  index.json
```

Legacy packages may omit `mentions.json` until fully reworked.

## Human-facing output

`episode.md` contains only the podcast's substantive content and source perspective.

It is intentionally detailed rather than concise. Adapt its structure to rankings, news episodes, interviews, mock drafts, team reviews, position discussions, strategy shows and mixed formats.

For ranking or list episodes, preserve complete safely reconstructable boards and source-supported alternative views.

For mixed episodes, continue through the complete raw source. A later live draft or strategy block is not optional merely because it follows the headline segment.

Do not append an entity, alias, mention or coverage register to `episode.md`.

## Machine-readable outputs

`takes.json` stores structured claims under:

- `players`
- `teams`
- `positions`
- `nfl`
- `fantasy`
- `other`

`mentions.json` is created from a separate full raw-source pass. It records every player mention or possible player mention and other fantasy-relevant named entities, including comparisons, competitors, historical references and unresolved forms.

For split mention storage, part files validate their envelope while the aggregated payload is validated against the same canonical mention definition as inline storage. Do not duplicate the complete mention definition in a second schema.

`index.json` stores technical metadata, calculated counts and the audit status.

## JSON formatting rule

All AI-created or manually maintained Fantasy Management JSON files must be human-readable:

- UTF-8
- two-space indentation
- one property per line
- arrays on multiple lines
- exactly one array item per line
- nested objects on separate lines
- stable key order where practical
- trailing newline

Do not commit minified JSON or one complete object per line.
