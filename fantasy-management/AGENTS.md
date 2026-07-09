# Fantasy Management Agent Instructions

This folder is the isolated Fantasy Management workspace of the repository.

Read this file first for Fantasy Football, Dynasty, Mighty Giants, Stoned Lack, Down Set Talk, Football Bromance, Relevant Players, roster, trade, draft, free-agent, player evaluation, source-processing, knowledge-layer, league-context or analysis-storage tasks.

## Scope

Fantasy Management work must stay inside this folder unless current application or league data from elsewhere in the repository is required.

Fantasy Management includes:

- Mighty Giants analysis
- roster, trade, draft and free-agent analysis
- player evaluations
- Relevant Players files
- podcast and external-source processing
- source take extraction
- player identity resolution and alias handling
- normalized knowledge-layer updates
- league context, owner profiles and trade negotiation history
- boards and source summaries
- stored AI analyses
- user decisions and decision history

## Required reading order

For Fantasy Management tasks, read these files as needed:

1. `fantasy-management/AGENTS.md`
2. `fantasy-management/_ai/FANTASY_MANAGEMENT_SOURCES.md`
3. `fantasy-management/_ai/FANTASY_MANAGEMENT_RULES.md`
4. `fantasy-management/_ai/PODCAST_SOURCE_MODEL.md` when podcast/source extraction, source takes, knowledge derivation or structure matters
5. `fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md` when podcast/source extraction matters
6. `fantasy-management/_ai/templates/podcast/README.md` and relevant podcast templates when podcast/source extraction matters
7. `fantasy-management/_ai/source-registry.json` when source identity, weighting or comparison matters
8. `fantasy-management/_ai/entity-resolution/player_identity_registry.json` when player names, aliases, transcript errors or source extraction matter
9. `fantasy-management/league-context/owner-registry.json` when owner, team or user-perspective resolution matters
10. `fantasy-management/league-context/owner-profiles.md` when manager tendencies or negotiation context matters
11. `fantasy-management/league-context/trade-negotiation-history.md` when trade talks or counterparty history matter
12. `fantasy-management/league-context/league-format-notes.md` when format interpretation matters
13. `fantasy-management/_ai/WORKFLOWS.md`
14. relevant schema files listed in `fantasy-management/_ai/schema-list.json`
15. relevant source files under `fantasy-management/sources/`
16. relevant source-specific notes under `fantasy-management/sources/podcasts/{source_id}/SOURCE_NOTES.md`
17. relevant knowledge files under `fantasy-management/knowledge/` when such files exist
18. relevant analyses under `fantasy-management/analyses/` when such files exist
19. relevant decisions under `fantasy-management/decisions/` when such files exist

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

## Source, knowledge and analysis separation

Use this mental model:

```text
Podcast source package = what the podcast said.
Knowledge = what remains relevant for our league after interpretation.
Analysis = what Mighty Giants should do.
```

Podcast takes are source material and should stay inside the episode package first. They are not automatically knowledge.

Knowledge should be created only after a separate interpretation step that checks league format, roster context, relevance, freshness and whether the source statement actually applies to Mighty Giants.

## Entity resolution separation

Player identity resolution is source-processing support and may be reused across podcasts, manual notes and future external source extractions.

The central podcast-independent player identity registry is:

`fantasy-management/_ai/entity-resolution/player_identity_registry.json`

Use the registry to resolve known aliases, transcript errors, phonetic variants, surname-only mentions and missing suffixes.

Do not treat entity-resolution entries as fantasy recommendations, player values or current depth-chart truth.

For new podcast/source extractions, confirmed player identity resolution must be stored inline in the relevant `takes.json` player take, not only in a companion overlay file.

## Main structure

Keep only folders that contain real files. Do not commit empty placeholder folders or README-only category folders.

Use this target structure as a logical layout. Create optional folders only when they receive actual content:

```text
fantasy-management/
  AGENTS.md
  README.md
  _ai/
    FANTASY_MANAGEMENT_SOURCES.md
    FANTASY_MANAGEMENT_RULES.md
    PODCAST_SOURCE_MODEL.md
    PODCAST_EXTRACTION_RULES.md
    schema-list.json
    source-registry.json
    WORKFLOWS.md
    entity-resolution/
      player_identity_registry.json
    templates/
      podcast/
        README.md
        episode_summary_template.md
        episode_takes_template.json
        episode_index_template.json
        raw_manifest_template.md
    schemas/
  league-context/
    README.md
    owner-registry.json
    owner-profiles.md
    trade-negotiation-history.md
    league-format-notes.md
  sources/
    podcasts/
      stoned-lack/
        SOURCE_NOTES.md
        STONED_LACK_EXTRACTION_GUIDE.md
        episodes/
          YYYY/
            episode_id/
              raw/
              episode.md
              takes.json
              index.json
      down-set-talk/
        SOURCE_NOTES.md
      football-bromance/
        SOURCE_NOTES.md
  knowledge/
    players/
    teams/
    positions/
    nfl/
    fantasy/
  analyses/
  decisions/
```

`knowledge/`, `analyses/`, `decisions/`, `sources/relevant-players/`, `sources/external-rankings/` and `sources/manual-notes/` are created on demand when actual files exist.

## Source of truth rules

- Current league state comes from `public/data/`.
- Fantasy Management files are analysis and working files, not permanent truth.
- Podcast and external-source outputs are source context, not final recommendations.
- Final Mighty Giants recommendations must combine current league data, source context, derived knowledge and current market/news context when relevant.
- Podcast source takes must not be treated as final knowledge until a knowledge derivation step decides whether they apply to the league format and current context.

## Language

Use German for human-facing Fantasy Management notes, summaries, todo entries, podcast episode summaries, take indexes, rollups and recommendations unless the user explicitly asks otherwise.

Machine-readable JSON keys may remain English.
