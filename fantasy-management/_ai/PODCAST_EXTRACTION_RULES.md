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

A placeholder raw file is not a completed raw source. If the full transcript cannot be committed, mark the whole extraction as incomplete and do not treat downstream notes or takes as complete.

## Episode rule

For every processed episode, create:

- a readable episode note under `sources/podcasts/{source_id}/episodes/YYYY/`
- a machine-readable episode JSON under `sources/podcasts/{source_id}/episodes/YYYY/`

The episode note should summarize topics, relevant players, teams, roles, market context and unresolved entity questions.

The episode JSON must reference every extracted take in `take_ids`. An empty or obviously incomplete `take_ids` list means the episode extraction is incomplete.

## Atomic take rule

Extract reusable takes at the smallest useful unit.

A take should usually cover one player, team, role, market point, format note or strategy point.

Do not collapse an entire episode into only a few summary takes when the transcript contains many player evaluations, rankings, tiers, sleepers, fades, buy/sell/hold notes, strategy notes or format notes.

Each take should keep these concepts separate:

- original source statement
- cleaned entity mapping
- AI interpretation
- evidence reference
- freshness / current relevance

## Completeness gate

Before marking an extraction as complete, verify:

1. the raw transcript is present and not a placeholder
2. all meaningful player, team, coach, format and strategy mentions were reviewed
3. every high-signal player in the episode note has at least one atomic take or an explicit reason why no take was created
4. caution, fade, uncertainty and negative takes are extracted, not only positive takes
5. episode JSON `take_ids` matches the take files created
6. unresolved names and entity-mapping issues are listed in the episode note
7. current views are updated when the extraction is intended to feed reusable knowledge

If any item fails, mark the extraction as `incomplete` or `needs_rework` and explain what is missing.

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
