# Fantasy Management Agent Instructions

This folder is the isolated Fantasy Management workspace of the repository.

Read this file first for Fantasy Football, Dynasty, Mighty Giants, Stoned Lack, Down Set Talk, Football Bromance, Relevant Players, roster, trade, draft, free-agent, player evaluation, source-processing, knowledge-layer, league-context or analysis-storage tasks.

## Scope

Fantasy Management work must stay inside this folder unless current application or league data from elsewhere in the repository is required.

Fantasy Management includes:

- Robert / Mighty Giants analysis
- roster, trade, draft and free-agent analysis
- player evaluations
- player analysis and derived Operations player datasets
- podcast and external-source processing
- source take extraction
- player identity resolution and alias handling
- entity-mention coverage auditing
- normalized knowledge-layer updates
- league context, owner profiles and trade negotiation history
- boards and source summaries
- stored AI analyses
- user decisions and decision history

## Required reading order

For Fantasy Management tasks, read these files as needed:

For any trade negotiation, trade outreach, counteroffer, follow-up, manager-tendency or counterparty-communication task, `fantasy-management/_ai/TRADE_NEGOTIATION_RULES.md` is additionally mandatory and must be read before applying owner profiles or negotiation history.

For any Fantasy Operations, Daily Monitoring, Free-Agent Monitoring, Weekly Lineup/Waiver separation or monitoring-triggered watchlist task, `fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md` is additionally mandatory and must be read before evaluating monitoring materiality, proposing durable watch targets or separating monitoring from final roster decisions.

For any `entity-observation` baseline read/write, monitoring-triggered durable observation proposal, approved qualitative baseline persistence or Observation-State repair/migration, `fantasy-management/_ai/OBSERVATION_STATE_STORAGE.md` is additionally mandatory. It is authoritative for the current Base + Target-Shard storage contract and supersedes older procedural text that describes the large `fantasy-management/automation/state/entity-observation.json` file as the normal full-replacement write target.

For any roster audit, cut/drop, Free-Agent Draft, waiver/add/drop, weekly lineup/waiver, roster-capacity or roster-flexibility task, `fantasy-management/_ai/ROSTER_ARCHITECTURE.md` is additionally mandatory and must be read before classifying player roles/security or deciding whether a transaction consumes protected churn capacity.

1. `fantasy-management/AGENTS.md`
2. `.ai-context/manual/work-tracking.yaml` when planning, prioritizing, recording or resuming repository work
3. `fantasy-management/_ai/FANTASY_MANAGEMENT_SOURCES.md`
4. `fantasy-management/_ai/FANTASY_MANAGEMENT_RULES.md`
5. `fantasy-management/_ai/PODCAST_SOURCE_MODEL.md` when podcast/source extraction, source takes, mention coverage, knowledge derivation or structure matters
6. `fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md` when podcast/source extraction matters
7. `fantasy-management/_ai/PODCAST_PACKAGE_STORAGE.md` when podcast package size, splitting, aggregation or storage matters
8. `fantasy-management/_ai/PODCAST_EXTRACTION_PIPELINE.md` for new podcast work packages, Content Maps, Golden Set evaluation, incremental commits or publication architecture
9. `fantasy-management/_ai/PODCAST_PIPELINE_TOOLING.md` when validating, building or publishing a pipeline work package
10. `fantasy-management/_ai/golden-set/README.md` and `fantasy-management/_ai/golden-set/profile-list.json` when selecting, evaluating or extending podcast quality profiles
11. `fantasy-management/_ai/templates/podcast/README.md` and relevant podcast templates when podcast/source extraction matters
12. `fantasy-management/_ai/source-registry.json` when source identity, weighting or comparison matters
13. `fantasy-management/_ai/entity-resolution/player_identity_registry.json` when player names, aliases, transcript errors or source extraction matter
14. `fantasy-management/league-context/owner-registry.json` when owner, team or user-perspective resolution matters
15. `fantasy-management/league-context/owner-profiles.md` when manager tendencies or negotiation context matters
16. `fantasy-management/league-context/trade-negotiation-history.md` when trade talks or counterparty history matters
17. `fantasy-management/league-context/league-format-notes.md` when format interpretation matters
18. `fantasy-management/_ai/WORKFLOWS.md`
19. relevant schema files listed in `fantasy-management/_ai/schema-list.json`
20. relevant source files under `fantasy-management/sources/`
21. relevant source-specific notes under `fantasy-management/sources/podcasts/{source_id}/SOURCE_NOTES.md`
22. relevant knowledge files under `fantasy-management/knowledge/` when such files exist
23. relevant analyses under `fantasy-management/analyses/` when such files exist
24. relevant decisions under `fantasy-management/decisions/` when such files exist

## Canonical app data

The central application and league data remains under:

`public/data/`

Current league, roster, player, draft, transaction, salary, scoring and settings information must be derived from current repository data when needed.

Fantasy Management artifacts are working and analysis artifacts. They are not permanent truth.

Dynamic evaluations must be re-derived from current repository data and, when relevant, current external sources.

## Separation rule

The Fantasy Management workspace is separate from the application context.

Do not place Fantasy Management outputs, stored analyses, podcast/source extractions, source summaries, player boards or decisions in the central app AI context.

Store them only under:

`fantasy-management/`

## Work tracking

- GitHub Issues are the canonical operative source of truth for Fantasy Management and Fantasy Operations backlog, progress, handoff and historical work records.
- Follow `.ai-context/manual/work-tracking.yaml` for Issue lifecycle, granularity, mutable priority semantics and drift governance.
- The current Issue body is the canonical mutable work state; comments are supplemental history or communication and must not be required to reconstruct current work state.
- Do not maintain parallel Markdown todo lists; operative repository work belongs in GitHub Issues.
- Classify work by its purpose and owning context, not by whether the implementation uses Python, PowerShell, GitHub Actions, ChatGPT tasks or another technical mechanism.
- A pipeline, materialized dataset or workflow whose purpose is Fantasy Management monitoring, analyses or reviews remains Fantasy Management work even when implementation touches shared repository tooling.
- Application, frontend, generated-app-data and shared technical-platform work remains application/platform work; coordinated cross-context work should use one coherent Issue where appropriate rather than duplicate canonical work.
- Move durable Fantasy Management decisions into the relevant canonical rules, source maps or workflow documentation under `fantasy-management/_ai`; Issues do not replace durable knowledge.
- Questions and analysis alone do not authorize repository mutation. Once the user explicitly authorizes concrete repository work, the administrative Issue maintenance required to track that authorized work is implicitly authorized.
- Durable Fantasy Management State, Knowledge, Decisions, boards, baselines, reviews and similar persisted analysis remain subject to their existing explicit-approval rules; administrative Issue bookkeeping is not such persistence and does not expand those permissions.
- `origin:automation` is reserved in the label contract but does not authorize current scheduled monitoring or automation to create Issues. Automatic Issue creation requires a separate explicit automation contract.

## Source, knowledge and analysis separation

Use this mental model:

```text
Podcast source package = what the podcast said.
Knowledge = what remains relevant for our league after interpretation.
Analysis = what Robert should do.
```

Podcast takes are source material and should stay inside the episode package first. They are not automatically knowledge.

Knowledge should be created only after a separate interpretation step that checks league format, roster context, relevance, freshness and whether the source statement actually applies to Robert's roster context.

Podcast extraction itself is source-centered and entity-neutral. Players remain the primary decision objects of later Knowledge and analysis, but team, coaching, scheme, cap, contract, format and strategy takes must remain independently reusable when the source treats them substantively.

## Entity resolution and mention coverage separation

Player identity resolution and entity-mention coverage are source-processing support and may be reused across podcasts, manual notes and future external source extractions.

The central podcast-independent player identity registry is:

`fantasy-management/_ai/entity-resolution/player_identity_registry.json`

Use the registry to resolve known aliases, transcript errors, phonetic variants, surname-only mentions and missing suffixes.

Do not treat entity-resolution entries as fantasy recommendations, player values or current depth-chart truth.

For new podcast/source extractions, confirmed player identity resolution must be stored inline in the relevant player take and mention entry, not only in a companion overlay file.

Schema-version-2 podcast packages must use a separate second raw-transcript pass to create the mention register, covering every player mention and other fantasy-relevant named entities. The mention register is an audit layer, not Knowledge or analysis.

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
    ROSTER_ARCHITECTURE.md
    TRADE_NEGOTIATION_RULES.md
    PODCAST_SOURCE_MODEL.md
    PODCAST_EXTRACTION_RULES.md
    PODCAST_PACKAGE_STORAGE.md
    PODCAST_EXTRACTION_PIPELINE.md
    PODCAST_PIPELINE_TOOLING.md
    schema-list.json
    source-registry.json
    WORKFLOWS.md
    golden-set/
      README.md
      profile-list.json
      profiles/
      references/
    entity-resolution/
      player_identity_registry.json
    templates/
      podcast/
        README.md
        episode_summary_template.md
        episode_takes_template.json
        episode_mentions_template.json
        episode_index_template.json
        raw_manifest_template.md
    schemas/
      episode-index.schema.json
      episode-takes.schema.json
      episode-mentions.schema.json
      podcast-work-status.schema.json
      podcast-content-map-manifest.schema.json
      podcast-content-map-segment.schema.json
      podcast-take-item.schema.json
      podcast-article-manifest.schema.json
      podcast-mention-segment.schema.json
      podcast-process-review.schema.json
      podcast-publish-request.schema.json
      podcast-golden-profile.schema.json
      podcast-golden-profile-list.schema.json
  podcast-work/
    source_id/
      YYYY/
        episode_id/
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
              content-map/
              takes/
              mentions/
              article/
              process-review/
              episode.md
              takes.json
              mentions.json
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

`podcast-work/`, `knowledge/`, `analyses/`, `decisions/`, `sources/external-rankings/` and `sources/manual-notes/` are created on demand when actual files exist.

## Source of truth rules

- Current league state comes from `public/data/`.
- Fantasy Management files are analysis and working files, not permanent truth.
- Podcast and external-source outputs are source context, not final recommendations.
- Final recommendations for Robert must combine current league data, source context, derived knowledge and current market/news context when relevant.
- Podcast source takes must not be treated as final knowledge until a knowledge derivation step decides whether they apply to the league format and current context.
- The mention register is a completeness and audit artifact; it must not be treated as a ranking or recommendation.
- A Content Map is a source-preservation contract for new pipeline packages; it is not Knowledge or a final recommendation.
- Golden Set profiles evaluate extraction quality and may propose improvements, but canonical rules and profiles change only after explicit user approval.
- `fantasy-management/_ai/golden-set/profile-list.json` is the canonical list of active Golden Set profiles. Unregistered profile files are drafts or proposals, not active extraction requirements.
- The local podcast builder may aggregate and validate authored work-package artifacts, but it must not create new editorial interpretation.
- `fantasy-management/_ai/OBSERVATION_STATE_STORAGE.md` is the canonical storage contract for approved qualitative `entity-observation` baselines. Normal approved baseline writes go to deterministic per-target shards under `fantasy-management/automation/state/entity-observation-targets/`; the large `entity-observation.json` file is the immutable migration-time base snapshot, not the normal replacement-write target.

## GitHub connector large-file guard

- A GitHub connector response with `content: ""` must not be treated as proof that a repository file is empty when the reported file `size` is greater than zero.
- Before classifying a generated, runtime or analysis artifact as empty, cross-check the reported size and, when available, the blob SHA/content or another authoritative materialization/runtime result.
- If the connector cannot return the file body because the file is too large or unsupported, report the body as unavailable through the connector rather than describing the file as empty.
- This guard applies especially to generated operational artifacts such as `fantasy-management/generated/operations/player-signals.json` and `fantasy-management/generated/operations/free-agent-signals.json`.
- Durable state intended for interactive connector writes must remain bounded or sharded so a normal logical update never depends on replacing an unbounded aggregate file. For `entity-observation`, follow `fantasy-management/_ai/OBSERVATION_STATE_STORAGE.md`.

## Language

Use German for human-facing Fantasy Management notes, summaries, Issue bodies, source summaries, rollups and recommendations unless the user explicitly asks otherwise.

Machine-readable JSON keys may remain English.