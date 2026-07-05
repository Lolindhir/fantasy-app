# Fantasy Management Agent Instructions

This folder is the isolated Fantasy Management workspace of the repository.

Read this file first for Fantasy Football, Dynasty, Mighty Giants, StoneLack/StonedLack, Down Set Talk, Football Bromance, Relevant Players, roster, trade, draft, free-agent, player evaluation, source-processing, knowledge-layer or analysis-storage tasks.

## Scope

Fantasy Management work must stay inside this folder unless current application or league data from elsewhere in the repository is required.

Fantasy Management includes:

- Mighty Giants analysis
- roster, trade, draft and free-agent analysis
- player evaluations
- Relevant Players files
- podcast and external-source processing
- source take extraction
- normalized knowledge-layer updates
- derived boards and source summaries
- stored AI analyses
- user decisions and decision history

## Required reading order

For Fantasy Management tasks, read these files as needed:

1. `fantasy-management/AGENTS.md`
2. `fantasy-management/_ai/FANTASY_MANAGEMENT_SOURCES.md`
3. `fantasy-management/_ai/FANTASY_MANAGEMENT_RULES.md`
4. `fantasy-management/_ai/knowledge-layer.yaml`
5. `fantasy-management/derived/knowledge/PROCESS.md`
6. `fantasy-management/_ai/WORKFLOWS.md`
7. relevant source files under `fantasy-management/sources/`
8. relevant current knowledge files under `fantasy-management/derived/knowledge/current/`
9. relevant take history under `fantasy-management/derived/knowledge/takes/`
10. relevant analyses under `fantasy-management/analyses/`
11. relevant decisions under `fantasy-management/decisions/`

## Canonical app data

The central application and league data remains under:

`public/data/`

Current league, roster, player, draft, transaction, salary, scoring and settings information must be derived from current repository data when needed.

Fantasy Management artifacts are working and analysis artifacts. They are not permanent truth.

Dynamic evaluations must be re-derived from current repository data and, when relevant, current external sources.

## Separation rule

The Fantasy Management workspace is separate from the application context.

Do not place Fantasy Management outputs, stored analyses, podcast/source extractions, Relevant Players files, source summaries, player boards or decisions in the central app AI context.

Store them only under:

`fantasy-management/`

## Main structure

Use this target structure:

```text
fantasy-management/
  AGENTS.md
  README.md
  _ai/
    FANTASY_MANAGEMENT_SOURCES.md
    FANTASY_MANAGEMENT_RULES.md
    knowledge-layer.yaml
    WORKFLOWS.md
    schemas/
      analysis.schema.json
      source-take.schema.json
      source-profile.schema.json
      relevant-player.schema.json
  sources/
    podcasts/
      stonedlack/
      down-set-talk/
      football-bromance/
    relevant-players/
    external-rankings/
    manual-notes/
  derived/
    knowledge/
      README.md
      PROCESS.md
      entities/
      takes/
      current/
      rollups/
    player-boards/
    rookie-boards/
    free-agent-boards/
    trade-value-context/
    source-summaries/
  analyses/
  decisions/
  indexes/
  archive/
    superseded/
```

## Language

Agent-facing instruction files should be written in English.

Human-facing documentation may be written in German.

Stored user-facing analysis outputs should be German unless requested otherwise.

## Output storage rules

Use `sources/` for source material and source-specific extraction artifacts.

Use `derived/knowledge/` for cross-source, normalized, AI-readable source context.

Use `derived/knowledge/current/` for the current source-derived working view after freshness, contradiction and supersession handling.

Use `derived/knowledge/takes/` for historical source-take evidence.

Use `derived/` for boards, rankings, source summaries and intermediate outputs that are not final recommendations.

Use `analyses/` for concrete AI evaluations, reports and recommendations.

Use `decisions/` for user decisions and resulting decision history.

Use `indexes/` for cross-file lookup metadata.

Use `archive/superseded/` for replaced or outdated artifacts that should not be treated as current.
