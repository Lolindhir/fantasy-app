# Fantasy Management Agent Instructions

This folder is the isolated Fantasy Management workspace of the repository.

Agents must read this file first for any Fantasy Football, Dynasty, Mighty Giants, StonedLack, Relevant Players, roster, trade, draft, free-agent, player evaluation, source-processing or analysis-storage task.

## Scope

All Fantasy Management work must stay inside this folder unless explicitly required to read current application or league data from elsewhere in the repository.

Fantasy Management includes:

- Mighty Giants analysis
- roster analysis
- player evaluations
- trade evaluations
- draft analysis
- free-agent analysis
- Relevant Players files
- StonedLack podcast processing
- other podcast/source processing
- derived player boards
- rookie boards
- trade-value context
- stored AI analyses
- user decisions and decision history

## Required reading order

For Fantasy Management tasks, read these files as needed:

1. `fantasy-management/AGENTS.md`
2. `fantasy-management/_ai/FANTASY_MANAGEMENT_SOURCES.md`
3. `fantasy-management/_ai/FANTASY_MANAGEMENT_RULES.md`
4. `fantasy-management/_ai/WORKFLOWS.md`
5. relevant files under `fantasy-management/sources/`
6. relevant files under `fantasy-management/derived/`
7. relevant files under `fantasy-management/analyses/`
8. relevant files under `fantasy-management/decisions/`

## Canonical app data

The central application and league data remains under:

`public/data/`

Current league, roster, player, draft, transaction, salary, scoring and settings information must be derived from the current repository data when needed.

Fantasy Management artifacts are working and analysis artifacts. They are not permanent truth.

Dynamic evaluations must be re-derived from current repository data and, when relevant, current external sources.

## Separation rule

The Fantasy Management workspace is separate from the application context.

Do not place Fantasy Management outputs, stored analyses, podcast extractions, Relevant Players files, source summaries, player boards or decisions in the central app AI context.

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
    WORKFLOWS.md
    templates/
      player-analysis-template.md
      trade-analysis-template.md
      roster-audit-template.md
    schemas/
      analysis.schema.json
      source-take.schema.json
      relevant-player.schema.json

  sources/
    podcasts/
      stonedlack/
        README.md
        STONEDLACK_EXTRACTION_GUIDE.md
        STONEDLACK_REPO_STRUCTURE.md
        schemas/
        raw_transcripts/
        episodes/
        indexes/

    relevant-players/
    external-rankings/
    manual-notes/

  derived/
    player-boards/
    rookie-boards/
    free-agent-boards/
    trade-value-context/
    source-summaries/

  analyses/
    2026/
      roster/
      players/
      trades/
      draft/
      free-agents/
      strategy/
      league-meta/
      reports/

  decisions/
    2026/
      trade-decisions.md
      cut-decisions.md
      draft-decisions.md
      watchlist-decisions.md

  indexes/
    player_index.json
    source_index.json
    analysis_index.json
    decision_index.json

  archive/
    superseded/
```

## Language

Agent-facing instruction files should be written in English.

Human-facing documentation may be written in German.

Recommended language split:

- `AGENTS.md`: English
- `_ai/*.md`: English
- schemas: English
- `README.md`: German or bilingual
- stored user-facing analysis outputs: German, unless requested otherwise

## Output storage rules

Use `sources/` for source material and source-specific extraction artifacts.

Use `derived/` for boards, rankings, source summaries and intermediate outputs derived from one or more sources but not yet framed as a final recommendation.

Use `analyses/` for concrete AI evaluations, reports and recommendations.

Use `decisions/` for user decisions and resulting decision history.

Use `indexes/` for cross-file lookup metadata.

Use `archive/superseded/` for replaced or outdated artifacts that should not be treated as current.
