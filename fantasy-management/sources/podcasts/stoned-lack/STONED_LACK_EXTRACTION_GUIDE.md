# Stoned Lack Extraction Guide

Purpose: source-specific guidance for Stoned Lack podcast packages.

Shared package and coverage rules are canonical in:

- `fantasy-management/_ai/PODCAST_SOURCE_MODEL.md`
- `fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md`
- `fantasy-management/_ai/templates/podcast/`

This guide adds only Stoned Lack-specific behavior.

## Core principle

Stoned Lack extraction creates source evidence, not active Knowledge and not a Mighty Giants recommendation.

## Package

```text
sources/podcasts/stoned-lack/episodes/YYYY/sl_XXXX/
  raw/
    manifest.md
    part01.md
    part02.md
  episode.md
  takes.json
  mentions.json
  index.json
```

## `episode.md`

Create a detailed German preparation that can be read without opening JSON.

Preserve:

- all fantasy-relevant news
- complete safely reconstructable rankings and tiers
- detailed player cases
- positives, risks and uncertainty
- host agreements and disagreements
- team, depth-chart, coach and scheme context
- format distinctions
- rookie-draft and market strategy
- source-derived closing views
- substantive later segments such as a live mock draft

Do not impose a fixed length or one rigid outline.

Do not include:

- raw aliases as a register
- identity-resolution metadata
- complete mention or coverage tables
- take or mention IDs
- package paths or file inventories
- review and validator status
- Mighty Giants recommendations
- league-specific recommendations not stated by the hosts

For ranking episodes, every ranked player receives enough explanation to preserve placement, positive case and risk.

## `takes.json`

Use the six shared categories.

For every player take include:

- `raw_entity_mention`
- canonical `entity` or `null`
- team and position when known
- compact `entity_resolution`
- formats
- source claim
- reasoning
- risks
- sentiment
- conviction
- evidence
- tags

Create takes for rankings, news subjects, substantive evaluations, role and injury theses, format and strategy theses, and meaningful disagreements.

Do not reduce a detailed Stoned Lack argument to a one-sentence take merely for compactness.

## `mentions.json`

Create the register in an independent second pass over the full raw transcript.

Stoned Lack's automated German transcripts frequently distort English names. Search for phonetic and name-like phrases, not only correctly spelled names.

Record:

- every ranked player
- every substantive player
- every news subject
- comparisons
- teammates and depth-chart competitors
- injury and scheme references
- historical examples
- live-draft names
- passing references
- unresolved possible names
- other fantasy-relevant named entities

Classify low-value context separately from recommendations.

Required subjects link to standalone takes and appear substantively in `episode.md`.

Context-only and unresolved mentions may remain audit-only with `coverage.episode_md: false` and an explanatory note.

Do not copy the technical register into `episode.md`.

## Stoned Lack extraction focus

Extract:

1. player evaluations
2. complete rankings, tiers and mock-draft orders when safely reconstructable
3. team and depth-chart context
4. position-group takes
5. rookie-draft strategy
6. Redraft/Dynasty splits
7. buy, sell, hold, fade and watchlist language
8. format-dependent notes
9. caution and uncertainty
10. host disagreement
11. all fantasy-relevant news
12. later live-draft or Q&A segments
13. unresolved transcript names
14. source conviction and sentiment
15. source-supported category views

## Entity resolution

Load the central registry before extraction:

`fantasy-management/_ai/entity-resolution/player_identity_registry.json`

Use position, NFL team, college, draft round, landing spot, teammates, nearby ranking tier and episode context.

Preferred verification order for decision-relevant identities:

1. official NFL or team pages
2. NFL Draft Tracker or official draft material
3. official college pages
4. Pro Football Reference or Sports Reference
5. fantasy sources only as supporting evidence

Do not finalize a surname-only or distorted name without verification.

When uncertain, use `entity: null` and preserve the raw form.

Add confirmed reusable aliases to the central registry with evidence paths.

## Two-pass workflow

### Pass A: content extraction

Read every ordered raw part and create:

- detailed `episode.md`
- complete `takes.json`
- initial identity resolution

### Pass B: independent mention sweep

Read every ordered raw part again and focus only on:

- every player-like name
- every other fantasy-relevant named entity
- recurring distortions
- comparisons and depth-chart context
- live-draft participants
- missing subjects and takes
- unresolved forms
- cross-file links and counts

Do not use the summary as the sole input for Pass B.

## Status gate

Use `active_source_package` only when:

1. raw source is present and fully listed
2. Pass A covers the complete episode
3. Pass B covers the complete raw source
4. `episode.md` is detailed and contains no technical register
5. all substantive segments are represented
6. complete rankings and meaningful live-draft structure are preserved
7. `takes.json` is detailed and categorized
8. all player takes include inline resolution
9. all required subjects have takes
10. `mentions.json` contains all discovered player and relevant entity mentions
11. context-only and unresolved forms remain visible
12. all links and calculated counts reconcile
13. recurring confirmed aliases are in the central registry
14. uncovered mention count is zero
15. JSON files follow repository formatting
16. validator unit tests pass
17. package and coverage validators pass

Otherwise use `needs_review` or `needs_rework` and document the blocker.

## Knowledge handoff

After extraction, a separate step may derive Knowledge under `fantasy-management/knowledge/`.

Do not automatically copy every Stoned Lack take or mention into Knowledge.
