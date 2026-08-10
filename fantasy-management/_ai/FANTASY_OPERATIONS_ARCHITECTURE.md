# Fantasy Operations Architecture

## Purpose

Fantasy Operations uses a provider-neutral hybrid architecture. Deterministic repository tooling prepares reusable facts and signals. Current qualitative research and interpretation happen outside the repository. Durable repository changes require explicit human approval.

The repository must not depend on a specific AI provider, AI SDK, hosted model, or paid inference API.

## Runtime layers

### 1. Source refresh

Existing source workflows refresh league, roster, transaction, player, market, ranking, ADP, projection, schedule, game, usage and external activity inputs.

Source refreshers own acquisition and source-local normalization. They do not make roster recommendations.

### 2. Deterministic materialization

Versioned scripts join refreshed inputs into provider-neutral datasets. Materialization may calculate identifiers, ownership, percentiles, deltas, tiers, quality flags, provenance and input fingerprints.

Materialization must not:

- browse the web;
- call an AI or recommendation service;
- infer qualitative role changes from prose;
- create Hold, Shop, Cut, Add, Start or Sit recommendations;
- turn a missing source row into a negative player judgment.

Current published materialized contracts:

```text
fantasy-management/generated/operations/managed-roster-signals.json
fantasy-management/generated/operations/external-signal-relevance.json
fantasy-management/generated/operations/player-signals.json
fantasy-management/generated/operations/free-agent-signals.json
fantasy-management/generated/operations/kicker-streaming-inputs.json
fantasy-management/generated/operations/data-quality.json
```

`managed-roster-signals.json` contains prepared data for the complete Mighty Giants roster.

`external-signal-relevance.json` resolves global external-signal player IDs to current player identity and league ownership. It contains readable add/drop views and complete per-player signal details for:

- Mighty Giants players;
- opponent-rostered players;
- fantasy free agents;
- unresolved player identities.

`data-quality.json` covers both ranking/ADP materialization and external-signal identity/ownership quality.

The central player-signal contract is published by the same deterministic Fantasy Operations materialization workflow from its versioned configuration, schema and builder:

```text
fantasy-management/automation/player-signal-materialization.json
fantasy-management/_ai/schemas/player-signal-dataset.schema.json
fantasy-management/_ai/scripts/build_player_signal_dataset.py
→ fantasy-management/generated/operations/player-signals.json
```

The workflow builds `external-signal-relevance.json` before `player-signals.json`, so the central contract consumes the freshly materialized activity and ownership context from the same run. All generated outputs are staged and published together through the existing retry/rebuild write path.

The central player-signal dataset is league-wide rather than managed-roster-only. Its configured fantasy population is QB/RB/WR/TE/K and includes a player when at least one of these conditions holds:

- the player currently has an NFL team;
- the player is owned in the fantasy league;
- the player is listed in an active normalized external ranking/projection source;
- the player appears in the current external activity signal.

The dataset joins:

- current player identity and app fields;
- league ownership derived from every team’s Roster/Reserve/Taxi union;
- structured injury fields;
- Sleeper nominal depth-chart position/order as a role hint, explicitly not as usage truth;
- Dynasty expert-consensus and market-value signals;
- Redraft ADP including the dedicated Kicker ADP feed;
- provider projections;
- Sleeper Trending add/drop activity;
- source provenance and freshness metadata.

Projection providers remain independent. Comparable rank percentiles may be summarized across projection providers, but provider fantasy-point projections are retained separately and must not be averaged because provider scoring contracts can differ and are not Mighty-Giants scoring.

The complete Fantasy Free-Agent contract is derived from the same current `player-signals.json` without re-reading `Players.json -> IsFreeAgent` as league availability:

```text
fantasy-management/automation/free-agent-materialization.json
fantasy-management/_ai/schemas/free-agent-dataset.schema.json
fantasy-management/_ai/scripts/build_free_agent_dataset.py
→ fantasy-management/generated/operations/free-agent-signals.json
```

The free-agent population is selected exclusively from `ownership.status == fantasy_free_agent`, where ownership itself comes from the union of every league team’s Roster/Reserve/Taxi lists.

The active Kicker Streaming input contract is built after the free-agent contract from the held managed-team kicker and all actual fantasy-free-agent kickers:

```text
fantasy-management/automation/kicker-streaming-input-materialization.json
fantasy-management/_ai/schemas/kicker-streaming-inputs.schema.json
fantasy-management/_ai/scripts/build_kicker_streaming_inputs.py
→ fantasy-management/generated/operations/kicker-streaming-inputs.json
```

It carries the existing market, ADP, projection, activity, injury and nominal-role signals into one candidate set and reconciles raw Kicker projection statistics with the current league scoring where source detail permits it. CBS `50+` field goals remain bounded because the league distinguishes 50-59 from 60+; FFToday field-goal totals remain bounded because no distance buckets are supplied. Provider fantasy points remain separate.

The productive materialization dependency order is:

```text
external-signal-relevance.json
→ player-signals.json
→ free-agent-signals.json
→ kicker-streaming-inputs.json
```

Each step consumes the freshly rebuilt upstream output from the same retry/rebuild run before the changed generated artifacts are staged and published together.

### 3. External research and analysis

An external analyst may read the current materialized datasets, perform fresh research and interpret qualitative signals such as injury context, practice participation, role, opportunity, coaching comments and depth-chart changes.

External activity is a prioritization and research trigger. It is not an automatic roster recommendation.

Kicker Streaming belongs in this layer. The deterministic input contract already supplies the held kicker, every current fantasy-free-agent kicker, FFC Kicker ADP, separate FFToday/CBS projections, activity, nominal role and current Mighty-Giants Kicker scoring. The analysis layer adds current weekly schedule, matchup, team scoring environment, field-goal opportunity, weather/stadium, job security and relevant QB/injury context.

The on-demand analysis method is versioned in:

```text
fantasy-management/_ai/kicker-streaming-analysis-config.json
fantasy-management/_ai/schemas/kicker-weekly-context.schema.json
fantasy-management/_ai/schemas/kicker-streaming-analysis.schema.json
fantasy-management/_ai/scripts/analyze_kicker_streaming.py
```

The analysis deliberately has two stages:

1. A baseline ranking uses the currently materialized projection and Kicker-ADP signals to produce a research shortlist. Sleeper add activity is only a research tiebreaker and is not converted into automatic player quality.
2. A weekly decision is allowed only after explicit current context is supplied for the held kicker and researched alternatives. Job security is an eligibility gate. Matchup, offense, field-goal opportunity, weather/stadium and QB/injury context contribute to the weekly score.

Without weekly context the analysis returns `weekly_context_required` and must not manufacture a switch recommendation from preseason or provider-only signals. Repository persistence is not automatic; the script defaults to stdout-only, and any durable analysis write remains subject to the human-approved persistence rule below.

### 4. Notification

Material changes and relevant errors may be delivered automatically. No-change runs remain silent.

A notification does not change repository state.

### 5. Human-approved persistence

A durable write to State, Knowledge, Decisions, boards, baselines or stored reviews requires explicit human approval after the proposed change and supporting evidence are visible.

The approved write is then performed interactively with the normal repository validation and publication rules.

For qualitative observations that use the existing entity-observation profile model, the canonical persisted approved baseline state is:

```text
fantasy-management/automation/state/entity-observation.json
```

This State is durable comparison memory for later monitoring and for other agents. It is not generated data and it is not an authorization for autonomous writes.

An approved interactive observation-State write must:

- persist only the specifically approved target/profile observations;
- normalize `material_state` according to the applicable profile `output_fields` and workflow rules;
- calculate `state_hash` with the existing canonical compact sorted-JSON SHA-256 contract;
- preserve unrelated previous good states and existing input provenance;
- increment the State revision exactly once for the complete logical State change;
- validate the complete replacement State against `automation-observation-state.schema.json` and the repository cross-file validator;
- pin the current target-branch parent commit and current State blob before publication;
- publish only by a non-forced fast-forward and recompute on concurrency conflicts.

A missing target/profile baseline does not activate or authorize autonomous bootstrap work. Scheduled monitoring may form an internal first-observation baseline for comparison during that run, but durable persistence still requires explicit approval unless a later architecture decision deliberately changes this rule.

## Source catalogs

Ranking, market-value, ADP and projection materialization is declared in:

```text
fantasy-management/_ai/operations-source-catalog.json
```

External signal relevance is declared in:

```text
fantasy-management/_ai/operations-external-signal-catalog.json
```

The catalogs own source identity, provider, dataset identity, paths, timestamps, signal mappings, identity fields, expected absence semantics, freshness and interpretation context. Provider names and source paths must not be embedded in monitoring prompts or recommendation logic.

The active Operations Source Catalog includes the following signal families for central materialization:

- FantasyPros Dynasty expert consensus;
- FantasyCalc Dynasty market value;
- Fantasy Football Calculator Redraft ADP, including the Kicker-only view;
- FFToday Kicker projections;
- CBS Sports Kicker projections.

Rank-based cross-source comparisons use list-length-aware percentiles. Provider-native values remain intact in the source-specific provider view.

The external-signal materializer supports the normalized `top_n_activity_v1` comparison contract. It preserves:

- current top-N membership;
- `entered_top_n` and `left_top_n` changes;
- rank changes;
- count changes;
- silent baseline and material-event eligibility state.

A player absent from a top-N list is not assigned zero activity. The central player-signal dataset preserves the same rule: `not_listed` means outside the current provider top-N result, and rank/count remain null.

## Identity and ownership rule

External signal identity is resolved through the configured stable player ID. Current league ownership is derived only from the union of every team’s `Roster`, `Reserve` and `Taxi` lists in `League.json`.

Permitted ownership states are:

- `mighty_giants`;
- `opponent_rostered`;
- `fantasy_free_agent`;
- `multiple_rosters` as a data-quality error.

An unresolved player remains in the external-signal dataset as an explicit data-quality finding and is never silently discarded. A central player row is keyed by the current app/Sleeper player ID; source join gaps remain quality/coverage information rather than being guessed away.

## NFL roster-status interpretation rule

`public/data/Players.json` contains several source-specific fields that describe different aspects of NFL player status and must not be collapsed into one roster-status inference.

- `IsFreeAgent` is normalized from the Tank01 `isFreeAgent` signal and is the repository's direct structured NFL free-agent signal.
- `Status` is sourced independently from Sleeper player metadata. A value such as `Active` must not be interpreted by itself as proof that the player is currently under contract with an NFL team.
- `TeamID` and `TeamAbbr` are sourced independently from Tank01 team metadata. They may remain populated for a player whose `IsFreeAgent` value is `true`; their presence does not override the free-agent signal or by itself prove a current NFL contract.
- Deterministic Operations materialization must preserve the explicit free-agent signal, for example as `app_data.is_free_agent`, rather than infer NFL roster status only from team or Sleeper-status fields.
- Monitoring and analysis must explicitly consider `IsFreeAgent` when determining current NFL roster status. Do not report a repository data-quality error merely because `TeamAbbr`/`TeamID` or `Status = Active` coexist with `IsFreeAgent = true`.
- When these fields conflict with a decision-relevant current transaction or roster claim, verify the current NFL status against fresh authoritative transaction, league or team evidence and preserve the conflict instead of silently selecting one field.

This rule concerns **NFL roster status only**. Fantasy-league ownership and fantasy-free-agent availability remain derived exclusively from the union of every team's `Roster`, `Reserve` and `Taxi` lists in `League.json`; `Players.json -> IsFreeAgent` must never be used as fantasy-league availability.

## Non-player entity rule

An external source may expose entities that participate in the provider activity feed but are not player entities for the managed league format, such as NFL team defenses.

These entities must be classified declaratively in `operations-external-signal-catalog.json`. A matching entity is excluded from player identity resolution, ownership assignment, free-agent views and player-level monitoring. The source row remains accounted for through separate `excluded_non_player_entities` counts and entity-type metadata.

Invalid classification rules fail closed. A provider-specific non-player pattern must not be embedded directly in monitoring or recommendation logic.

## Injury-data rule

`public/data/Players.json` currently contains a structured secondary injury signal from the existing player refresh pipeline:

- `Injured`
- `InjuryDetails.ReturnDate`
- `InjuryDetails.Description`
- `InjuryDetails.Date`
- `InjuryDetails.Designation`

These fields are useful for candidate detection and prioritization. They are not an official-injury-report source and must not be treated as proof of health when empty. Decision-relevant positive signals require fresh external verification.

## Role-data rule

`public/data/Players.json` may contain Sleeper-backed `SleeperDepthChartPosition` and `SleeperDepthChartOrder` fields. The central player-signal contract may expose them as a nominal role hint.

They do not establish snap share, routes, targets, carries, red-zone work, kicking opportunity or job security. Missing values are valid and do not automatically indicate a data-quality error. Weekly or decision-relevant role conclusions still require stronger usage data or current external verification.

## Generated-data rule

`fantasy-management/generated/**` is reserved exclusively for fully reproducible derived outputs. Every artifact stored there must be rebuildable from versioned source data, configuration and deterministic repository tooling.

Generated artifacts may contain provenance, input fingerprints, joins, normalized views, derived metrics and quality findings. They must not contain manually maintained evaluations, recommendations, decisions, Knowledge, human-authored baselines or stored reviews.

Manually curated or interpretive artifacts remain in their owning Fantasy Management areas such as `knowledge/`, `analyses/`, `decisions/`, source packages or other explicitly documented canonical locations.

Current published generated layout:

```text
fantasy-management/generated/
└── operations/
    ├── managed-roster-signals.json
    ├── external-signal-relevance.json
    ├── player-signals.json
    ├── free-agent-signals.json
    ├── kicker-streaming-inputs.json
    └── data-quality.json
```

`generated/operations/` owns deterministic read models prepared specifically for Fantasy Operations. These files do not replace canonical current league data under `public/data/` or canonical source snapshots under `fantasy-management/sources/`.

If the amount or variety of deterministic generated data grows materially, `fantasy-management/generated/` may be extended with additional domain-specific subdirectories rather than mixing unrelated outputs into `operations/`. Examples include a future `reports/`, `indexes/` or another clearly owned generated domain. A `podcasts/` generated namespace is permitted only for strictly reproducible derived podcast artifacts; authored source packages, editorial extraction, Knowledge and analyses must remain in their existing non-generated locations.

New generated subdirectories must follow the same reproducibility rule and should be created only when real artifacts require them; do not create empty placeholder folders.

## Production order

The intended daily order is:

```text
league/source refreshes
→ external ranking/projection refreshes
→ external signal refreshes
→ deterministic materialization
→ scheduled monitoring
```

The morning workflows are scheduled in Europe/Berlin order before the 07:00 monitoring window. Source pushes trigger `FM • Materialize • Operations Inputs`, which rebuilds managed-roster signals, external-signal relevance, the central player-signal dataset, the complete free-agent dataset and Kicker Streaming inputs in dependency order before publishing changed generated outputs. Downstream Free-Agent and Kicker Streaming analyses should read these materialized contracts rather than reconstructing the same ranking, projection, ownership and activity joins independently.

## Legacy observation runner

The former autonomous State-writing observation runner is retained only as historical configuration while migration is in progress. Its autonomous execution path must operate read-only and must not attempt State, event, Knowledge, Decision or board publication.

The legacy boundary applies to autonomous execution, not to every artifact created by that framework. Until an explicit replacement architecture is approved, the following contracts remain reusable for human-approved persistence and comparison:

- `fantasy-management/automation/state/entity-observation.json` as the canonical approved qualitative observation baseline State;
- target and profile identity plus normalization semantics where they remain applicable;
- `automation-observation-state.schema.json`;
- canonical material-State hashing semantics;
- cross-file validation and optimistic-concurrency publication safeguards.

The following legacy behaviors are not part of scheduled production monitoring and must not be triggered merely because baselines are missing:

- autonomous Observation Bootstrap execution;
- autonomous incremental baseline backfill;
- autonomous State-only checkpoint publication;
- autonomous Replacement-State-Writer execution;
- autonomous Observation Event bundle publication.

Legacy workflow and helper files may remain in the repository as historical implementation contracts while migration is incomplete. Their existence does not override this architecture or the current `runner-config.json` mode.
