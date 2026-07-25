# Podcast Extraction Pipeline

Purpose: define the target architecture for robust, incremental and source-faithful podcast extraction.

This document complements:

- `PODCAST_SOURCE_MODEL.md`
- `PODCAST_EXTRACTION_RULES.md`
- `PODCAST_PACKAGE_STORAGE.md`
- `WORKFLOWS.md`

It defines the future working pipeline. Existing episode packages remain valid and are not retroactively required to adopt this architecture unless they are explicitly reworked.

## Core outcome

The pipeline must preserve what the source said, how it argued and how its subjects relate to one another.

Podcast extraction is source-centered and entity-neutral. A source may primarily discuss:

- players
- teams
- position groups
- head coaches
- coordinators or complete coaching staffs
- schemes and systems
- depth charts and units
- front offices
- contracts and cap situations
- injuries
- NFL drafts, free agency or trades
- fantasy formats, markets and strategy

Players remain the primary decision objects of later Fantasy Management analysis. They are not automatically the primary source objects of every episode.

Use this separation:

```text
Podcast extraction = preserve all source subjects, arguments and relationships.
Knowledge derivation = translate relevant context into durable player, team, coach, scheme and fantasy knowledge.
Analysis = decide whether a player should be bought, sold, held, cut, stashed or monitored.
```

## Depth principle

Storage granularity must never reduce content depth.

A small file may contain a detailed take. The required detail follows the source, not the file size, entity type or desired output length.

Use these source-depth levels:

- `passing`: a reference without an independent argument
- `brief`: a short independent statement
- `substantive`: a supported evaluation with at least one meaningful reason, condition or risk
- `deep`: a multi-dimensional argument that must preserve its major reasoning chain
- `structural`: a broader thesis that affects multiple subjects, roles or later decisions

For `deep` and `structural` material, preserving only the final conclusion is incomplete. Preserve every dimension the source materially discusses, such as:

- background or history
- talent or traits
- positive case
- negative case
- role and opportunity
- team and depth-chart context
- coaching and scheme
- contract or cap context
- injury and availability
- market price or ADP
- time horizon
- format distinction
- comparisons
- host agreement or disagreement
- uncertainty, conditions and failure paths

Do not invent dimensions that the source does not support.

## Canonical working area

Incremental extraction work lives outside completed source packages:

```text
fantasy-management/podcast-work/
  {source_id}/
    {year}/
      {episode_id}/
        work-status.json
        raw/
        content-map/
        takes/
          items/
        article/
          manifest.json
          sections/
        mentions/
          segments/
        process-review/
        publish-request.json
```

The working area may contain incomplete commits on `main`. Completed source packages under `fantasy-management/sources/podcasts/**/episodes/**` must remain publishable source records.

## Stable published package

The final published package keeps stable reader and machine entry points:

```text
fantasy-management/sources/podcasts/{source_id}/episodes/{year}/{episode_id}/
  raw/
  content-map/
  takes/
  mentions/
  article/
  process-review/
  episode.md
  takes.json
  mentions.json
  index.json
```

The small files under `content-map/`, `takes/`, `mentions/`, `article/` and `process-review/` are canonical authored inputs.

The following files are deterministic generated entry points:

- `episode.md`
- `takes.json`
- `mentions.json`
- `index.json`

A builder may copy the complete working package into the published location and generate those four entry points. It must not create new editorial interpretation during aggregation.

## Content Map

The Content Map is a required durable planning and completeness artifact for new pipeline packages.

It is created after the full raw source has been read and before detailed takes and article sections are considered complete.

Suggested layout:

```text
content-map/
  manifest.json
  segments/
    segment-001.json
    segment-002.json
    ...
```

The manifest owns:

- episode and source identity
- ordered segment paths
- total segment counts
- content-map status
- referenced Golden Set profiles

Each segment describes at least:

- stable segment ID and source order
- source range, raw parts and timestamps when available
- title and segment type
- source depth
- primary and related subject types
- substantive claims and reasoning obligations
- expected dimensions that must be preserved
- host differences and uncertainty when present
- required take IDs or planned take types
- required article section IDs
- relevant Golden Set profiles
- completion status for takes, article and mention audit

The Content Map is not a summary. It is a preservation contract for the rest of the extraction.

## Take storage

Author one JSON file per independent reusable take:

```text
takes/items/{take_id}.json
```

A take may be short or detailed depending on source depth.

Every take has one primary subject, but may reference related entities and relations. Team, coach, scheme, contract or strategy claims must remain reusable as independent takes when they can affect multiple current or future players. Do not bury them exclusively inside one player take.

Take completeness is driven by:

1. source depth
2. Content Map expectations
3. the matching Golden Set profile
4. actual source evidence

A deep player take may contain background, positives, negatives, risks, role, team context, format distinctions, comparisons, market context and uncertainty. A deep team or coaching take requires equivalent preservation of its source dimensions.

## Article storage

The authored reader-facing article is stored in ordered sections:

```text
article/
  manifest.json
  sections/
    010-introduction.md
    020-news.md
    030-ranking.md
    ...
```

The article manifest owns section order and maps sections to Content Map segments and take IDs.

The builder concatenates the ordered sections into one continuous `episode.md`.

`episode.md` remains the primary human-readable record and must be understandable without reading JSON. Internal section splitting is only a storage and collaboration mechanism.

## Mention audit

The independent mention sweep remains a separate full raw-source pass.

Mention files may be stored by source segment:

```text
mentions/segments/{segment_id}.json
```

They are aggregated into `mentions.json` during publication.

The mention audit remains the technical entity and coverage register. It does not replace the Content Map, which covers substantive segments, claims and reasoning obligations.

## Golden Set

The Golden Set evaluates the extraction process, not the complete historical archive.

Suggested layout:

```text
fantasy-management/_ai/golden-set/
  profiles/
    player-evaluation.json
    team-evaluation.json
    coaching-staff.json
    scheme-analysis.json
    position-group.json
    ranking.json
    mock-draft.json
    news-segment.json
    market-strategy.json
  references/
    ...
```

### Profiles

Profiles define typical dimensions that should be checked when the source discusses them. They must not require the extractor to invent absent information.

Example player dimensions include:

- background and development
- talent and traits
- positive and negative cases
- role and opportunity
- team, depth chart, coach and scheme
- injury, contract and cap
- short- and long-term horizon
- format and scoring distinctions
- market or ADP
- comparisons, disagreements and uncertainty

Equivalent entity-specific profiles define expectations for teams, coaches, staffs, schemes, rankings, drafts, news and strategy.

### References

Optional reference episodes or excerpts demonstrate desired fidelity and depth for representative formats. They supplement profiles but do not define the entire system.

### Dynamic improvement

Every completed extraction includes a process-review pass that asks whether the episode revealed:

- a missing segment type
- a missing subject or relation type
- a missing Golden Set dimension
- an overly narrow rule
- a useful new reference case
- a storage or workflow improvement

Store proposals under:

```text
process-review/improvement-proposals.json
```

An extractor may propose rule or Golden Set changes. It must not silently change canonical rules or profiles. Permanent changes require explicit user approval.

## Work status and gates

`work-status.json` owns the current pipeline phase.

Recommended phases:

1. `raw_complete`
2. `content_map_complete`
3. `takes_in_progress`
4. `article_in_progress`
5. `mention_audit_in_progress`
6. `quality_review_in_progress`
7. `ready_for_publish`
8. `published`
9. `needs_rework`

A phase may advance only when its required authored artifacts exist and validate.

`ready_for_publish` requires at least:

- complete raw source and manifest
- complete Content Map
- every required segment represented
- every planned substantive take present
- every article section present and ordered
- independent mention audit complete
- Content Map reconciliation complete
- process-review proposals recorded, including an explicit empty proposal set when none exist
- no uncovered required subjects or substantive claims
- no unresolved build or validation blockers

## Incremental commit workflow

Direct commits to `main` are the intended default for podcast work unless the user requests a branch or pull request.

Prefer small focused checkpoints:

1. add raw source
2. add Content Map
3. add takes by segment or topic
4. add article sections by segment or topic
5. add mention audit
6. add quality review and improvement proposals
7. mark ready for publication
8. publish generated package

This allows long extractions to survive interrupted chats and lets multiple agents work on separate files with minimal conflict.

## Publication builder

A future deterministic builder must:

1. trigger only for an explicit `ready_for_publish` request
2. validate work identity, paths, Content Map and authored files
3. aggregate one-file-per-take inputs into `takes.json`
4. aggregate mention segment files into `mentions.json`
5. concatenate article sections into `episode.md`
6. calculate `index.json`
7. run package, coverage and pipeline validation
8. publish only when every blocking check passes
9. write no partial published package on failure
10. prevent recursive workflow triggering
11. use an episode-scoped concurrency group
12. commit the finished package directly to `main`

The builder is deterministic. It must not summarize, rewrite, infer or otherwise create editorial source content.

The publication workflow requires a separately approved GitHub Actions change because it needs narrowly scoped `contents: write` access. Do not implement or modify the workflow until its trigger, path scope, failure behavior, recursion guard and commit identity have been explicitly approved.

## Validation scope

Do not require all historical episode packages to satisfy future Content Map, Golden Set or generated-entry-point rules.

Validation applies to:

- new work packages using this pipeline
- published packages created from those work packages
- historical packages only when explicitly reworked into the new pipeline

Technical schemas still validate their declared schema versions. New editorial quality gates must not force archive-wide migration.

## Implementation sequence

Implement this target in focused phases:

1. Content Map, work-status, take-item, article-manifest and process-review schemas
2. Golden Set profile format and initial general profiles
3. pipeline validation and deterministic local builder
4. tests using synthetic fixtures and selected optional reference cases
5. one manual end-to-end pilot episode
6. publication workflow with explicit approval
7. normal use on new episodes

Do not begin by reworking existing episodes. Build and prove the general pipeline first, then choose a pilot episode deliberately.
