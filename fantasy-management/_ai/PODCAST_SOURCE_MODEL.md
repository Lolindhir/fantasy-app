# Podcast Source Model

Purpose: define the source model for podcast extraction and later Fantasy Management use.

This model separates three layers:

1. Podcast episode package — what the podcast said.
2. Knowledge — what remains relevant for our league after interpretation.
3. Analysis — what Mighty Giants should do with that knowledge.

## Core principle

Podcast extraction must not decide final Fantasy Management relevance.

Podcast extraction answers:

> What did the source say, how did it argue, and which fantasy-relevant entities and statements appeared?

Knowledge derivation answers:

> Which source statements are relevant for our league, format and current context?

Analysis answers:

> What should Mighty Giants do?

## Podcast episode package

Each newly processed podcast episode should live as one local package using the current package schema:

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

For small transcripts, `raw/source.md` may replace split raw parts.

Legacy packages created before the mention-coverage model may not contain `mentions.json`. New and fully reworked packages use `package_schema_version: 2` in `index.json` and must contain it.

## `episode.md`

`episode.md` is the detailed human-readable podcast preparation.

It is not intended to be a short executive summary. It should preserve the fantasy-relevant content, arguments, rankings, disagreements, uncertainties and context of the episode in a form the user can read without opening the machine-readable JSON files.

Write it like a detailed article that the user could read or publish privately:

- no internal pipeline metadata
- no file inventory
- no take or mention IDs
- no raw-name or alias register
- no entity-resolution or coverage table
- no timestamps as technical evidence structure
- no extraction, validator or review status blocks
- no machine-readable companion-file references
- no Mighty Giants recommendation
- no arbitrary brevity target

It may include source framing and interpretation of the podcast's own logic, but it must stay inside the podcast perspective.

The structure must adapt to the episode instead of forcing every podcast into one fixed outline. Depending on the content, useful sections may include:

- news and current-context blocks
- rankings, tiers, boards or draft rounds
- detailed player, team or position profiles
- host agreements and disagreements
- positive cases, risks and uncertainty
- fantasy-format distinctions
- team, depth-chart, coach and scheme context
- strategy principles
- category-specific closing rankings or favorite lists

For ranking or list episodes, preserve the complete source board when possible. Every ranked subject should receive enough explanation to retain the source's reasoning, positive case, risk and relevant disagreement or format dependency. When the source material supports it, include additional source-derived views such as highest conviction, best opportunity, best talent/upside, strongest immediate role, sleepers, format-dependent profiles, fades or major disagreements. Do not manufacture these categories when the episode does not support them.

Good:

> The hosts see Jordyn Tyson as one of their favorite players in the episode because they expect a fast WR2 path in New Orleans. They still identify Chris Olave as the main target-competition risk.

Not in `episode.md`:

> Mighty Giants should draft Jordyn Tyson.

That belongs in later analysis.

## Reader-facing versus technical coverage

The human-readable and technical artifacts have deliberately different completeness goals:

- `episode.md` must be substantively complete. It includes every ranking subject, news subject, substantive evaluation and other entity needed to understand the hosts' argument.
- `mentions.json` must be technically complete. It includes every non-false-positive player mention and other fantasy-relevant named entity found in the second raw pass, including passing references, comparisons, depth-chart names, historical references and unresolved transcript forms.

A context-only or unresolved mention does not need to appear in `episode.md` merely to prove that it was detected. It may remain audit-only in `mentions.json` when including it would add no substantive reader value.

Do not turn `episode.md` into a metadata appendix to satisfy coverage. The complete technical register is `mentions.json`.

## `takes.json`

`takes.json` contains structured podcast statements from the same episode.

It is still source material, not Knowledge.

Use these top-level categories:

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

### Category meanings

- `players`: statements about specific players.
- `teams`: statements about NFL teams, depth charts, team environments or team position groups.
- `positions`: statements about positional groups such as WR, RB, TE or QB.
- `nfl`: general NFL, draft, coaching, scheme or league-context statements.
- `fantasy`: fantasy strategy, scoring, redraft, dynasty, rookie draft, bestball, market or format statements.
- `other`: source statements that do not fit cleanly elsewhere.

### Take granularity

Takes should be concise enough for machines but complete enough to preserve the claim, source reasoning, risks and evidence.

Create a standalone take for:

- every ranking or tier subject
- every explicit sleeper, fade, buy, sell, hold or watchlist subject
- every player or entity with a substantive positive, negative or uncertain evaluation
- every independent role, injury, market, strategy or format thesis
- every meaningful host disagreement when it changes the evaluation

A player may have multiple takes when the episode makes materially different claims, for example ranking, role projection and market value. Do not collapse contradictory or independent claims merely to keep the file short.

Pure comparisons, depth-chart names, historical references and passing mentions do not automatically need standalone takes. They remain documented in `mentions.json` and link to the surrounding take when useful.

### Take fields

Keep takes readable and source-focused:

```json
{
  "id": "sl_0569_player_001",
  "category": "players",
  "type": "player",
  "raw_entity_mention": "Jordan Tyson",
  "entity": "Jordyn Tyson",
  "team": "NO",
  "position": "WR",
  "entity_resolution": {
    "status": "confirmed",
    "method": "registry",
    "confidence": "high"
  },
  "formats": [
    "dynasty",
    "redraft",
    "rookie_draft"
  ],
  "podcast_take": "The source statement in plain language.",
  "reasoning": [
    "Reason from the podcast."
  ],
  "risks": [
    "Uncertainty or downside from the podcast."
  ],
  "sentiment": "positive",
  "conviction": "high",
  "evidence": {
    "timestamp_start": "00:45:36",
    "timestamp_end": "00:48:22"
  },
  "tags": [
    "rookie_wr",
    "landing_spot",
    "opportunity"
  ]
}
```

Do not split every take into separate files by default. One `takes.json` per episode is the default.

## `mentions.json`

`mentions.json` is the episode-level coverage and audit register.

Its main purpose is to make omissions visible. It records each unique player mention and other fantasy-relevant named entity found during a separate second pass over the raw transcript.

Each mention records:

- the raw transcript form or forms
- the canonical entity when resolved
- compact entity-resolution status
- how the entity was used in the episode
- one or more occurrences and timestamps
- whether the entity is substantively represented in `episode.md`
- whether a standalone take is required
- which take IDs cover it
- an optional note when the mention is intentionally audit-only

Common mention types include:

- `ranking_subject`
- `substantive_take`
- `news_subject`
- `player_comparison`
- `depth_chart_context`
- `injury_context`
- `scheme_context`
- `historical_reference`
- `passing_reference`
- `unresolved`
- `false_positive`

Every player mentioned in the raw source must be represented, even when the player appears only as a comparison, teammate, competitor or passing reference. Non-player entities should be included when they carry fantasy-relevant source context.

A mention classified as a ranking subject, substantive take or news subject requires a linked standalone take and substantive reader-facing coverage in `episode.md`.

Context-only mentions may link to the surrounding take or have no take link when no structured claim is needed. They may use `coverage.episode_md: false` when they are intentionally retained only for technical audit. In that case, `coverage.note` should briefly explain the omission from the reader-facing note.

Unresolved transcript forms must remain visible in `mentions.json`. They do not need to be inserted into `episode.md` unless the unresolved reference is itself important for understanding a substantive argument.

## Coverage audit

Mention coverage is produced in a second pass that is separate from the main content extraction.

The audit asks:

1. Which player names or possible player names occur in the raw transcript?
2. Which other named entities carry fantasy-relevant content?
3. Which are ranking subjects, substantive evaluations or news subjects?
4. Which are comparisons, competitors, teammates, historical references or passing references only?
5. Does every required subject have a matching standalone take?
6. Does every required subject appear substantively in `episode.md`?
7. Are context-only and unresolved identities preserved in `mentions.json` rather than silently discarded?
8. Are intentional reader-facing omissions documented in the mention's coverage note?

For coverage counting, a non-false-positive mention is uncovered only when:

- a required ranking, substantive or news subject lacks a valid subject take; or
- a required ranking, substantive or news subject lacks reader-facing coverage; or
- the mention is neither reader-covered nor explicitly documented as an intentional audit-only context mention.

A package using schema version 2 is complete only when the audit status is `completed` and uncovered mentions equal zero.

## `index.json`

`index.json` is the local technical map for the episode package.

It may contain:

- package schema version
- source id
- episode id
- title
- dates
- paths within the package
- counts by take category
- mention coverage counts
- entity-resolution status
- coverage-audit status
- extraction status

Keep technical metadata out of `episode.md`.

## Knowledge layer

Knowledge is derived after podcast extraction.

Knowledge should live outside the podcast source package:

```text
fantasy-management/knowledge/
  players/
  teams/
  positions/
  nfl/
  fantasy/
```

Knowledge derivation may ignore podcast takes that are not useful for our format.

Example:

A podcast take says:

> Player X is a redraft must-have.

If this does not matter for our Dynasty league, it should remain in the podcast episode package but does not need to become active player knowledge.

If it affects market value, it may become fantasy-market knowledge instead of player-quality knowledge.

## Analysis layer

Analyses remain concrete decision documents:

```text
fantasy-management/analyses/{year}/
  players/
  trades/
  roster/
  draft/
```

A player analysis should combine:

1. current league data from `public/data/`
2. player knowledge
3. team knowledge
4. position knowledge
5. relevant source takes as evidence
6. current external context when needed
7. final Mighty Giants recommendation
