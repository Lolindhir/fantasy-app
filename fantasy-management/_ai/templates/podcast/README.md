# Podcast Templates

Purpose: central reusable templates for all Fantasy Management podcast source packages.

These templates apply to all podcast sources, including:

- Stoned Lack
- Down Set Talk
- Football Bromance
- future podcast sources

Source-specific guides may add quirks, alias handling or weighting notes, but they should not redefine the common output structure.

## Templates

Use these templates for new podcast extractions:

- `episode_summary_template.md` — adaptive, detailed German reader-facing podcast preparation without internal metadata.
- `episode_takes_template.json` — categorized source takes for one episode.
- `episode_mentions_template.json` — complete entity-mention register and cross-file coverage map.
- `episode_index_template.json` — local technical package map with take and mention coverage counts.
- `raw_manifest_template.md` — manifest for split raw transcripts.

## Default episode package

A current schema-version-2 podcast extraction should create:

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

Legacy packages may not contain `mentions.json` until they are fully reworked.

## Human-facing output

`episode.md` is for humans and contains only the podcast's content and source perspective.

It is intentionally detailed rather than concise. The user should be able to read it as the primary preparation of the episode without needing to inspect JSON for substantive content.

The template is a flexible building block, not a mandatory fixed outline. Adapt it to rankings, news episodes, interviews, mock drafts, team-by-team reviews, position discussions or strategy shows.

For ranking or list episodes, preserve complete boards and source-supported alternative views or category rankings. For other formats, preserve the actual debates, themes, reasoning and context of the episode.

End schema-version-2 summaries with a complete entity/mention register that makes comparisons, context-only references and unresolved names visible.

## Machine-readable outputs

`takes.json` is structured source material and uses these categories:

- `players`
- `teams`
- `positions`
- `nfl`
- `fantasy`
- `other`

Takes may remain compact, but every ranking subject, substantive evaluation, news subject and independent fantasy thesis needs suitable structured coverage. One entity may have multiple takes when the source makes distinct claims.

`mentions.json` records all player mentions and other fantasy-relevant named entities found in a separate second raw-transcript pass. It distinguishes substantive subjects from comparisons, competitors, teammates, historical references and passing mentions.

`index.json` is the local technical package map and keeps metadata out of `episode.md`. For schema version 2 it records mention counts and the second-pass coverage-audit status.

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

Do not commit one-line/minified JSON or inline arrays in Fantasy Management JSON when practical.
