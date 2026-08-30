# Fantasy Operations Architecture

## Purpose

Fantasy Operations uses a provider-neutral hybrid architecture. Deterministic repository tooling prepares reusable facts and signals. Current qualitative research and interpretation happen outside the repository. Durable repository changes require explicit human approval.

The repository must not depend on a specific AI provider, AI SDK, hosted model, or paid inference API.

## Runtime layers

### 1. Source refresh

Existing source workflows refresh league, roster, transaction, player, market, ranking, ADP, projection, schedule, game, usage and external activity inputs.

Source refreshers own acquisition and source-local normalization. They do not make roster recommendations.

The productive morning refresh path uses independent source-triggered materialization around the 07:00 Europe/Berlin monitoring window:

- every successful relevant external ranking, projection, activity or Success-Heartbeat push on `main` may materialize immediately, including pushes between 05:00 and 06:45 Europe/Berlin;
- relevant `League.json`, `Players.json` and `Timestamps.json` input changes remain immediate materialization triggers;
- materialization code, configuration, schema and workflow changes remain immediate triggers;
- the DST-safe scheduled 06:45 Europe/Berlin materializer remains only as an additional catch-up and is never the sole normal morning consolidation path;
- a manual `workflow_dispatch` of the materializer always runs immediately;
- generated Operations-only commits do not recursively trigger the materializer, and PR-only validation must not publish production heartbeats or production materialization.

The trigger decision is versioned and testable in `fantasy-management/_ai/scripts/resolve_fantasy_operations_materialization_trigger.py`. `FM • Materialize • Operations Inputs` separates its lightweight `gate` job from the expensive `materialize` job. Push-triggered materializations may supersede older push-triggered materializations, while the scheduled 06:45 catch-up is not allowed to cancel an already running source-triggered materialization.

Correctness does not depend on GitHub Actions starting the scheduled 06:45 catch-up on time or completing it before the 07:00 consumer. The latest successfully published canonical Operations state is authoritative, and its `source-freshness.json` contract determines whether monitoring may proceed, proceed in degraded mode or block.

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
fantasy-management/generated/operations/source-freshness.json
fantasy-management/generated/operations/managed-roster-signals.json
fantasy-management/generated/operations/external-signal-relevance.json
fantasy-management/generated/operations/player-signals.json
fantasy-management/generated/operations/free-agent-signals.json
fantasy-management/generated/operations/free-agent-movement-signals.json
fantasy-management/generated/operations/free-agent-movement-events.json
fantasy-management/generated/operations/kicker-streaming-inputs.json
fantasy-management/generated/operations/data-quality.json
```

`source-freshness.json` is the canonical monitoring-readiness gate for the configured source cycle. It distinguishes successful current refresh confirmation from source content changes and exposes `proceed`, `proceed_degraded` or `block`, including whether a no-event conclusion is permitted and which source/signal families are affected.

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

The workflow builds `source-freshness.json` first and `external-signal-relevance.json` before `player-signals.json`, so the central contracts consume the latest successfully materialized readiness, activity and ownership context from the same run. All generated outputs are staged and published together through the existing retry/rebuild write path.

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

The position-inclusive Free-Agent Movement Discovery contract is built from the complete current free-agent population and the existing normalized ranking/projection snapshot histories:

```text
fantasy-management/automation/free-agent-movement-materialization.json
fantasy-management/_ai/schemas/free-agent-movement-dataset.schema.json
fantasy-management/_ai/scripts/build_free_agent_movement_dataset.py
→ fantasy-management/generated/operations/free-agent-movement-signals.json
```

The Movement contract evaluates every current fantasy free agent at QB, RB, WR, TE and K through one shared Discovery-, Materiality- and Prioritization architecture. Kicker is not a separate discovery population or workflow. Position-specific sources, normalizations and thresholds remain valid features inside the common pipeline.

The deterministic Movement layer currently prepares:

- historical 1/3/7/14/30-day ADP changes using the position-appropriate feed;
- Dynasty expert-consensus rank/position-rank/tier changes and market-value movement;
- Season Projection consensus/provider/core-points movement where source detail permits league-scoring recalculation;
- cross-signal confirmation and divergence across Redraft ADP, Dynasty market and Season Projections;
- a position-specific small-league replacement-proximity proxy from currently league-owned player percentiles, keeping signal families separate instead of collapsing them into one player value;
- exact day-over-day changes in NFL team, structured injury fields and nominal Sleeper depth-chart role when the previous successful `free-agent-signals.json` is available;
- Sleeper Activity only as corroboration/research context, never as a discovery prerequisite or player-quality score.

Materiality thresholds are read from the existing versioned `redraft-adp-movement`, `market-movement`, `season-projection-movement` and Kicker movement profiles instead of being copied into a second rule set. The Movement output is a research-prioritization contract and explicitly does not emit a final roster recommendation.

The first productive run on 2026-08-17 evaluated 1,201 actual fantasy free agents and emitted 322 current research discoveries. Their distribution was K 19, QB 54, RB 71, TE 59 and WR 119; 141 were high-priority and 181 medium-priority. Material-family coverage in that initial state was dominated by `dynasty_market` (299), while `redraft_adp` and `season_projection` appeared in 4 discoveries each. This is a calibration observation, not a reason to discard the broader signal families or to infer that all 322 players need daily research.

Because long comparison windows intentionally keep a material Movement state alive for more than one day, the compact Free-Agent Movement Event contract is built immediately after the Movement state:

```text
fantasy-management/automation/free-agent-movement-event-materialization.json
fantasy-management/_ai/schemas/free-agent-movement-events.schema.json
fantasy-management/_ai/scripts/build_free_agent_movement_events.py
→ fantasy-management/generated/operations/free-agent-movement-events.json
```

The event layer compares the current `free-agent-movement-signals.json` with the previous successful Movement state and emits only:

- `new` when a player enters the material Discovery state;
- `changed` when the stable material state changes;
- `structural_change` when a new exact day-over-day injury/team/nominal-role edge appears while the stable material state otherwise remains the same;
- `resolved` when a previously material Discovery is no longer present.

The first-ever event materialization is a silent baseline. Stable material state intentionally normalizes away comparison-window churn: a material signal remaining present while moving from a 7-day to a 14-day view is not a new event by itself. Structural changes are edge events and their absence on the following run does not manufacture a synthetic reverse event. Kicker is part of the same QB/RB/WR/TE/K event contract and receives no separate discovery or event pipeline.

The first productive comparison on 2026-08-17 compared 322 previous with 322 current Movement discoveries and correctly emitted 0 events with Quality `ok`. This demonstrates the intended state/event separation: the broad Movement state can remain available for context without producing repeated daily research triggers.

The active Kicker Streaming input contract is built after the free-agent Movement state and event contracts from the held managed-team kicker and all actual fantasy-free-agent kickers:

```text
fantasy-management/automation/kicker-streaming-input-materialization.json
fantasy-management/_ai/schemas/kicker-streaming-inputs.schema.json
fantasy-management/_ai/scripts/build_kicker_streaming_inputs.py
→ fantasy-management/generated/operations/kicker-streaming-inputs.json
```

It carries the existing market, ADP, projection, activity, injury and nominal-role signals into one candidate set and reconciles raw Kicker projection statistics with the current league scoring where source detail permits it. CBS `50+` field goals remain bounded because the league distinguishes 50-59 from 60+; FFToday field-goal totals remain bounded because no distance buckets are supplied. Provider fantasy points remain separate.

Kicker Streaming is downstream position-specific analysis. Its existence does not create a second Free-Agent Discovery path; Free-Agent Movement Discovery and Movement Events remain common across QB/RB/WR/TE/K.

The productive materialization dependency order is:

```text
source-freshness.json
→ external-signal-relevance.json
→ player-signals.json
→ free-agent-signals.json
→ free-agent-movement-signals.json
→ free-agent-movement-events.json
→ kicker-streaming-inputs.json
```

Each step consumes the freshly rebuilt upstream output from the same retry/rebuild run before the changed generated artifacts are staged and published together. Before rebuilding `free-agent-signals.json`, the productive workflow copies the previous successful file to runner-temporary storage so Movement Discovery can derive exact day-over-day structural deltas. It also copies the previous successful `free-agent-movement-signals.json` to runner-temporary storage before rebuilding so the event layer can compare stable material state. Neither temporary comparison copy becomes a manually maintained baseline artifact.

### 3. External research and analysis

An external analyst may read the current materialized datasets, perform fresh research and interpret qualitative signals such as injury context, practice participation, role, opportunity, coaching comments and depth-chart changes.

Before interpreting deterministic events, scheduled monitoring must read `source-freshness.json`. A `block` decision stops normal monitoring; `proceed_degraded` restricts conclusions to fresh supported signal families; and `no_event_conclusion_allowed = false` forbids treating a zero-event contract as proof that nothing relevant changed. Monitoring must never infer readiness merely because the local clock is after 06:45.

`free-agent-movement-events.json` is the primary deterministic daily Free-Agent research-trigger layer. If its `event_count` is zero, scheduled monitoring must not launch qualitative Free-Agent research merely because players remain present in the broader Movement state, but a zero-event conclusion is only reliable when the Freshness Gate permits it.

`free-agent-movement-signals.json` is the current deterministic Discovery-state and detail layer. External research uses it to understand the current ADP/market/projection/structural context of an event, including cross-signal confirmation/divergence and replacement proximity. It is not a second alert list.

External activity is a prioritization and research trigger. It is not an automatic roster recommendation. Sleeper Trending remains corroboration context and is not a Discovery prerequisite.

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

A deterministic Movement discovery is not automatically a notification. `free-agent-movement-events.json` is the canonical deterministic Free-Agent event boundary for scheduled monitoring. Its first baseline is silent, and a comparison run with `event_count = 0` produces no Free-Agent research or user notification by itself when the Freshness Gate permits a no-event conclusion.

`new`, `changed` and `structural_change` events may trigger targeted qualitative research according to event priority and decision relevance. `resolved` events are normally closure/context signals and require further research only when the resolution itself changes a roster, trade or watchlist implication.

A notification does not change repository state.

### 5. Human-approved persistence

A durable write to State, Knowledge, Decisions, boards, baselines or stored reviews requires explicit human approval after the proposed change and supporting evidence are visible.

The approved write is then performed interactively with the normal repository validation and publication rules.

For qualitative observations that use the existing entity-observation profile model, the mandatory storage contract is:

```text
fantasy-management/_ai/OBSERVATION_STATE_STORAGE.md
```

The durable layout is:

```text
fantasy-management/automation/state/entity-observation.json
fantasy-management/automation/state/entity-observation-targets/{target_id}.json
```

`entity-observation.json` is the bounded global job header and contains no canonical qualitative target payloads. The complete approved qualitative baseline for each target lives exclusively in its target shard. A target without a shard has no durable qualitative baseline.

An approved interactive qualitative observation write must:

- persist only the specifically approved target/profile observations;
- read the existing complete shard for the affected target when present and preserve unrelated observation profiles in that target;
- normalize `material_state` according to the applicable profile `output_fields` and workflow rules;
- calculate changed `state_hash` values with the canonical compact sorted-JSON SHA-256 contract;
- preserve the stable `entity_fingerprint` and fail closed on identity drift;
- assign a new deterministic descriptive `write_id` to the logical target write;
- keep `base_state_revision` aligned with the bounded global header revision;
- validate the bounded header plus all canonical target shards with `validate_observation_state_shards.py` and the repository automation validation path;
- pin the current target-shard blob when replacing an existing shard;
- publish only by a non-forced fast-forward and recompute on concurrency conflicts;
- not rewrite the bounded global header merely because one qualitative target baseline changed.

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
- FFToday and CBS Sports Season Projections for the currently configured positions.

Rank-based cross-source comparisons use list-length-aware percentiles. Provider-native values remain intact in the source-specific provider view.

The external-signal materializer supports the normalized `top_n_activity_v1` comparison contract. It preserves:

- current top-N membership;
- `entered_top_n` and `left_top_n` changes;
- rank changes;
- count changes;
- silent baseline and material-event eligibility state.

A player absent from a top-N list is not assigned zero activity. The central player-signal dataset and Movement contract preserve the same rule: `not_listed` means outside the current provider top-N result, and rank/count remain null.

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
    ├── source-freshness.json
    ├── managed-roster-signals.json
    ├── external-signal-relevance.json
    ├── player-signals.json
    ├── free-agent-signals.json
    ├── free-agent-movement-signals.json
    ├── free-agent-movement-events.json
    ├── kicker-streaming-inputs.json
    └── data-quality.json
```

`generated/operations/` owns deterministic read models prepared specifically for Fantasy Operations. These files do not replace canonical current league data under `public/data/` or canonical source snapshots under `fantasy-management/sources/`.

### Generated-artifact read verification

Tool- oder Transportdarstellung ist nicht automatisch Dateizustand. Insbesondere bei großen Generated-Artefakten darf ein leerer oder ausgelassener Inline-`content`-Wert eines Connectors, einer API-Antwort oder einer UI-Vorschau **nicht** allein als Beleg für eine leere Repository-Datei oder eine echte Nullpopulation verwendet werden.

Vor einer Aussage wie „Datei ist leer“, „Feed enthält null Spieler“ oder „Publish hat einen leeren Contract erzeugt“ muss der tatsächliche aktuelle Artefaktzustand verifiziert werden. Zulässige Verifikation ist insbesondere:

- aktuellen Repository-Ref und Blob-SHA auflösen;
- Blob-Inhalt oder verlässliche Byte-/Dateigröße lesen;
- bei strukturierten Contracts den Inhalt mit dem vorgesehenen Parser beziehungsweise Schema prüfen;
- bei widersprüchlicher Tooldarstellung einen zweiten verlässlichen Read-Pfad verwenden.

Eine Connector-Trunkierung, ausgelassene Inline-Darstellung oder Antwortbegrenzung ist ein **Tooling-/Transportbefund**, kein Fantasy-Operations-Datenqualitätsbefund. Sie darf weder einen Datenqualitäts-TODO noch eine Spieler-/Populationsempfehlung auslösen, solange der tatsächliche Blob nicht entsprechend verifiziert wurde.

Umgekehrt bleibt eine verifiziert leere oder strukturell unerwartete Generated-Datei ein echter Fail-Closed-Fall und muss nach den normalen Datenqualitätsregeln behandelt werden.

If the amount or variety of deterministic generated data grows materially, `fantasy-management/generated/` may be extended with additional domain-specific subdirectories rather than mixing unrelated outputs into `operations/`. Examples include a future `reports/`, `indexes/` or another clearly owned generated domain. A `podcasts/` generated namespace is permitted only for strictly reproducible derived podcast artifacts; authored source packages, editorial extraction, Knowledge and analyses must remain in their existing non-generated locations.

New generated subdirectories must follow the same reproducibility rule and should be created only when real artifacts require them; do not create empty placeholder folders.

## Production order

The intended daily order is:

```text
league/source refreshes
→ external ranking/projection refreshes
→ external signal refreshes
→ immediate deterministic materialization after each successful relevant source/heartbeat publication
→ optional 06:45 Europe/Berlin catch-up
→ scheduled monitoring
```

The morning workflows remain scheduled in Europe/Berlin order before the 07:00 monitoring window. Their successful relevant source or Success-Heartbeat commits are independently materializable; there is no 05:00-06:45 batching exception. Multiple morning materializer runs are an accepted cost of publishing the latest derived state as early as possible.

The scheduled 06:45 run is only a best-effort reconciliation/catch-up. Its timing is not a readiness guarantee, and the 07:00 consumer must not assume that a scheduled materializer has started or finished. It must read the latest successfully published canonical Operations state and evaluate `source-freshness.json` before interpreting deterministic events. The Freshness Gate owns `proceed`, `proceed_degraded`, `block`, `no_event_conclusion_allowed`, blocking/unfresh sources and affected signal families.

A successful source refresh that leaves content unchanged is still fresh when its Success-Heartbeat is current. `public/data/Timestamps.json` remains provenance and must not be used as a substitute fetch-success proof.

Downstream scheduled Free-Agent monitoring should read `free-agent-movement-events.json` as the primary daily deterministic trigger layer after the Freshness Gate. `free-agent-movement-signals.json` remains the detail/current-state source for those events. Monitoring must not reconstruct ranking, projection, ownership and activity joins or use Sleeper Trending as a discovery gate. Kicker Streaming analyses remain downstream Weekly Decision modules.

## Legacy observation runner

The former autonomous State-writing observation runner is retained only as historical configuration. Its autonomous execution path is not part of current scheduled production monitoring and must not attempt State, event, Knowledge, Decision or board publication.

The reusable current contracts are:

- `fantasy-management/_ai/OBSERVATION_STATE_STORAGE.md` as the authoritative qualitative baseline storage contract;
- `fantasy-management/automation/state/entity-observation.json` as the bounded global job header with no canonical target payloads;
- `fantasy-management/automation/state/entity-observation-targets/{target_id}.json` as the exclusive durable qualitative target-baseline storage;
- target/profile identity and normalization semantics where they remain applicable;
- `automation-observation-state.schema.json` for the bounded global header shape;
- canonical material-state hashing semantics;
- the full-shard validator plus repository cross-file validation and optimistic-concurrency publication safeguards.

The following legacy behaviors are not part of scheduled production monitoring and must not be triggered merely because baselines are missing:

- autonomous Observation Bootstrap execution;
- autonomous incremental baseline backfill;
- autonomous State-only checkpoint publication;
- autonomous Replacement-State-Writer execution;
- autonomous Observation Event bundle publication.

Legacy workflow and helper files may remain only where another explicitly documented historical purpose requires them. Their existence does not override this architecture, `OBSERVATION_STATE_STORAGE.md`, the current `entity-observation` job definition or the current `runner-config.json` mode.
