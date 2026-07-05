# Podcast Extraction Rules

Purpose: central extraction rules for all podcast sources in Fantasy Management.

Use these rules for StoneLack/StonedLack, Down Set Talk, Football Bromance and future podcast sources.

## Canonical source configuration

Podcast source identity, weighting and profile comparison are maintained centrally in:

`fantasy-management/_ai/source-registry.json`

Podcast-specific quirks, aliases and interpretation notes belong next to the source in:

`sources/podcasts/{source_id}/SOURCE_NOTES.md`

Do not maintain source weights in multiple places.

## Layer model

Process podcast material through these layers:

1. raw source material
2. episode note
3. episode JSON
4. atomic source takes
5. current knowledge view
6. Mighty Giants analysis

## Raw source rule

Store raw transcripts or raw notes unchanged under:

`sources/podcasts/{source_id}/raw_transcripts/YYYY/`

Do not clean, rewrite or normalize the raw source file. If a better transcript becomes available, save a new version instead of overwriting the old trace.

## Episode rule

For every processed episode, create:

- a readable episode note under `sources/podcasts/{source_id}/episodes/YYYY/`
- a machine-readable episode JSON under `sources/podcasts/{source_id}/episodes/YYYY/`

The episode note should summarize topics, relevant players, teams, roles, market context and unresolved entity questions.

## Atomic take rule

Extract reusable takes at the smallest useful unit.

A take should usually cover one player, team, role, market point, format note or strategy point.

Each take should keep these concepts separate:

- original source statement
- cleaned entity mapping
- AI interpretation
- evidence reference
- freshness / current relevance

## Entity resolution rule

Use source-specific notes for common aliases and transcript quirks.

If a player, team or claim is uncertain, mark it as uncertain instead of guessing.

When decision-relevant, verify identity and current context against current repo data and fresh external sources if needed.

## Current view rule

Historical takes stay in `derived/knowledge/takes/`.

The current working view stays in `derived/knowledge/current/`.

Do not delete older takes just because later context changes the evaluation. Move old context out of the current view instead.

## Recommendation rule

Podcast output is source context, not a final recommendation.

Final Mighty Giants recommendations belong under `fantasy-management/analyses/` and must combine current league data, current knowledge view, take history when relevant and external context when needed.
