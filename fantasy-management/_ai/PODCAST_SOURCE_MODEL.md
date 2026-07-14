# Podcast Source Model

Purpose: define the source model for podcast extraction and later Fantasy Management use.

This model separates three layers:

1. Podcast episode package — what the source said.
2. Knowledge — what remains relevant after interpretation.
3. Analysis — what Mighty Giants should do.

## Core principle

Podcast extraction must not decide final Fantasy Management relevance.

Podcast extraction answers:

> What did the source say, how did it argue, and which fantasy-relevant entities and statements appeared?

Knowledge derivation answers:

> Which source statements remain relevant for the league, format and current context?

Analysis answers:

> What should Mighty Giants do?

## Podcast episode package

Each current episode package contains:

```text
fantasy-management/sources/podcasts/{source_id}/episodes/{year}/{episode_id}/
  raw/
    manifest.md
    part01.md
    part02.md
  episode.md
  takes.json
  mentions.json
  index.json
```

Legacy packages may lack `mentions.json`. New and fully reworked packages use schema version 2.

## `episode.md`

`episode.md` is detailed reader-facing source preparation.

It must preserve substantive content, arguments, rankings, disagreements, uncertainty, format distinctions and context without requiring the reader to inspect JSON.

Write it like a detailed private article:

- no internal pipeline metadata
- no file inventory
- no take or mention IDs
- no raw-name or alias register
- no entity-resolution or coverage table
- no technical timestamp appendix
- no review or validator status
- no Mighty Giants recommendation
- no arbitrary brevity target

Its structure follows the episode. A mixed episode may require news, ranking, strategy and live-draft sections.

## Reader-facing versus technical completeness

The artifacts have different completeness goals:

- `episode.md` is substantively complete. It contains every ranking subject, news subject, substantive evaluation and the context needed to understand the source.
- `mentions.json` is technically complete. It contains every player mention or possible player mention and other fantasy-relevant named entities found in the independent second pass.

Context-only, historical, comparison and unresolved references do not need to be inserted into `episode.md` merely to prove detection. They may remain audit-only in `mentions.json` with an explanatory coverage note.

Do not turn `episode.md` into a metadata appendix.

## `takes.json`

`takes.json` contains reusable structured source statements.

Use these categories:

```json
{
  "players": [],
  "teams": [],
  "positions": [],
  "nfl": [],
  "fantasy": [],
  "other": []
}
```

Create standalone takes for rankings, substantive evaluations, news subjects, role and injury theses, format and strategy theses, and meaningful disagreement.

Takes preserve claim, reasoning, risks, formats, sentiment, conviction and evidence. They remain source material, not Knowledge.

## `mentions.json`

`mentions.json` is the technical coverage and audit register.

It records:

- raw transcript forms
- canonical identity when resolved
- compact resolution status
- mention role
- occurrences
- reader-facing coverage
- standalone-take requirement
- subject and context take links
- an omission note for intentionally audit-only references

Ranking, substantive and news subjects require a linked take and substantive `episode.md` coverage.

Context-only mentions may remain technical-only when documented.

Unresolved forms remain visible and use `entity: null`.

## Coverage audit

Coverage is produced through a separate full raw-source pass.

The audit asks:

1. Which player names or possible names occur?
2. Which other named entities carry fantasy-relevant context?
3. Which are ranking, substantive or news subjects?
4. Which are comparison, teammate, competitor, scheme, historical or passing references?
5. Does every required subject have a take?
6. Is every required subject in `episode.md`?
7. Are unresolved forms preserved?
8. Are intentional reader-facing omissions documented?
9. Do counts and links reconcile across files?

A schema-version-2 package is complete only when the audit is completed and uncovered mentions equal zero.

## `index.json`

`index.json` is the local technical map. It records identity, paths, counts, raw status, audit status and Knowledge-derivation status.

Keep this metadata out of `episode.md`.

## Knowledge layer

Knowledge is derived after extraction and lives outside source packages:

```text
fantasy-management/knowledge/
  players/
  teams/
  positions/
  nfl/
  fantasy/
```

Knowledge derivation may ignore source takes that are not useful for the league format or current context.

## Analysis layer

Analyses are decision documents under:

```text
fantasy-management/analyses/{year}/
```

A final analysis combines current league data, derived Knowledge, relevant source evidence and current external context. Source takes alone are never the final recommendation.
