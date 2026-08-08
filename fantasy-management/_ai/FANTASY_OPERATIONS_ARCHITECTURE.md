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
fantasy-management/generated/operations/data-quality.json
```

`managed-roster-signals.json` contains prepared data for the complete Mighty Giants roster.

`external-signal-relevance.json` resolves global external-signal player IDs to current player identity and league ownership. It contains readable add/drop views and complete per-player signal details for:

- Mighty Giants players;
- opponent-rostered players;
- fantasy free agents;
- unresolved player identities.

`data-quality.json` covers both ranking/ADP materialization and external-signal identity/ownership quality.

A central player-signal contract is now prepared in versioned configuration, schema, builder and tests:

```text
fantasy-management/automation/player-signal-materialization.json
fantasy-management/_ai/schemas/player-signal-dataset.schema.json
fantasy-management/_ai/scripts/build_player_signal_dataset.py
→ fantasy-management/generated/operations/player-signals.json
```

Production publication of `player-signals.json` is intentionally not enabled by this implementation. Adding it to a GitHub Actions write path requires separate explicit workflow approval.

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

### 3. External research and analysis

An external analyst may read the current materialized datasets, perform fresh research and interpret qualitative signals such as injury context, practice participation, role, opportunity, coaching comments and depth-chart changes.

External activity is a prioritization and research trigger. It is not an automatic roster recommendation.

A later Kicker Streaming analysis belongs in this layer. It may combine the central player-signal dataset and a complete fantasy-free-agent dataset with current weekly schedule, matchup, team scoring environment, weather/stadium, job security and Mighty-Giants kicker scoring. The deterministic player-signal layer itself must not produce an add/drop recommendation.

### 4. Notification

Material changes and relevant errors may be delivered automatically. No-change runs remain silent.

A notification does not change repository state.

### 5. Human-approved persistence

A durable write to State, Knowledge, Decisions, boards, baselines or stored reviews requires explicit human approval after the proposed change and supporting evidence are visible.

The approved write is then performed interactively with the normal repository validation and publication rules.

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
    └── data-quality.json
```

Prepared next generated contract after explicit publication approval:

```text
fantasy-management/generated/operations/player-signals.json
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

The morning workflows are scheduled in Europe/Berlin order before the 07:00 monitoring window. Source pushes trigger the currently active Fantasy Operations materialization. When `player-signals.json` is approved for production publication, it should be built after the source and external-signal states it consumes and before analyses such as Free-Agent or Kicker Streaming evaluation.

## Legacy observation runner

The former autonomous State-writing observation runner is retained only as historical configuration while migration is in progress. It must operate read-only and must not attempt autonomous State publication.
