# Fantasy Management Sources

Purpose: this file defines the source map for Fantasy Management work. It replaces external chat-level source notes for this repository area.

## Canonical technical app sources

The repository `Lolindhir/fantasy-app` remains the canonical source for current league and app data.

Current generated app data lives under:

`public/data/`

Important files:

- `public/data/League.json`
- `public/data/Players.json`
- `public/data/Teams.json`
- `public/data/Drafts.json`
- `public/data/Transactions.json`
- `public/data/Timestamps.json`
- `data-meta/nfl-reise/metadata.json`

## League source rules

`public/data/League.json` remains the primary current source for league settings, draft-pick references, roster size, lineup settings, scoring, salary cap fields, phase/status and ownership consumers not yet migrated. Canonical ownership is now productive in five scoped Operations consumers: `managed-roster-signals.json` (TeamID 1 membership/starter facts since 6Q), `external-signal-relevance.json` (league-wide Roster/Reserve/Taxi ownership since 6R), `player-signals.json` (league-wide ownership and `league_owned` population reason since 6S) and `fa-board-readmodel.json` (league-wide availability ownership plus Managed-Team Reserve/Taxi occupancy/capacity basis since 6T) and `managed-roster-overview.json` (Managed-Team membership/buckets inherited from canonical-active managed-roster-signals since 6U). In the migrated ownership consumers `League.json` no longer supplies membership; it remains only for consumer-specific App enrichment plus the existing trigger/freshness bridge. For `player-signals`, team labels now come from canonical members (#1263 C8c) and scoring settings from canonical league scoring (#347 A2); its `Timestamps.json` freshness/Age reference remains. Since #1263 C8e, FA-board capacity/settings are read from the canonical current-season league.json and display from canonical members; lifecycle owns status/phase/week and Timestamps.json remains the freshness reference.

### Sleeper platform-mechanics source hierarchy

For platform features whose behavior can materially change a Fantasy Management decision, keep the current league setting separate from the semantic meaning of that setting:

- use the current `public/data/League.json` value as the canonical app-level source for which Sleeper setting is currently active in this league;
- use current official Sleeper Support/documentation as the preferred external source for what that feature or setting means operationally;
- do not infer platform semantics only from a setting key, an old chat explanation, remembered behavior or a community post;
- community posts, Reddit and similar sources may help diagnose edge cases, but they do not override either the current league setting or official platform documentation;
- when AutoSubs materially affect a weekly lineup decision, resolve current league values such as allowed substitute count, timing eligibility and lock-related settings from `League.json`, then verify the current trigger/lock/substitution semantics against official Sleeper documentation before relying on them.

Current official AutoSub documentation:
`https://support.sleeper.com/en/articles/9731991-how-does-player-autosubs-work`

The user team is:

- Team name: `Mighty Giants`
- TeamID: `1`

For Mighty Giants analysis, always identify the team by `TeamID = 1` in current data.

### Canonical League ownership adapter and first productive consumer

Checkpoint 6P established the fail-closed Canonical League ownership adapter at:

`fantasy-management/_ai/scripts/canonical_league_ownership.py`

It resolves the active League season from:

- `data-source/leagues/nfl-reise/manifest.json`

and reads the accepted current-season basis facts from:

- `data-source/leagues/nfl-reise/seasons/<season>/league.json`
- `data-source/leagues/nfl-reise/seasons/<season>/members.json`
- `data-source/leagues/nfl-reise/seasons/<season>/rosters.json`

The stable Fantasy Management `TeamID` remains an application/Fantasy-owned identity. Its bridge to Canonical League data is explicit through
`fantasy-management/league-context/owner-registry.json -> owners[].canonical_league_member_id`.
Never infer `TeamID` from Sleeper `roster_id` or another provider roster identifier.

The adapter exposes current member/ownership basis facts such as
`Owner`/`OwnerID`, `Roster`, `Reserve`, `Taxi` and `Starter`.
It intentionally does **not** own or reproduce salary/cap fields, standings, awards, draft-pick readmodels,
team windows or other App/Fantasy-derived state.

Checkpoint 6Q activated this adapter for `managed-roster-signals.json`, which gets TeamID 1 membership and starter facts from Canonical League Source Data. Checkpoint 6X additionally moves the managed-roster consumer player identity surface and the identity fields used by its ranking/ADP joins to Canonical NFL Source Data: `Name` comes from `data-source/nfl/identities/players.json`, while fantasy-relevant `Position` and current NFL team come from `data-source/nfl/platform/sleeper/players.json` using the same `FantasyPositions` preference established in 6W. `public/data/Players.json` remains an explicit legacy enrichment only for Status, Age/Experience, Salary, SalaryProjected, IsFreeAgent and the existing structured Injury contract.

Issue #919 step 6 (2026-10-15) removes `public/data/Players.json` as an input of `managed-roster-signals.json`, `data-quality.json` and `player-signals.json`. `fantasy-management/_ai/scripts/canonical_player_inputs.py` now supplies the player list: population, Age/Experience, `IsFreeAgent`, Status and the structured Injury contract come from `tools/players_population.py` (ADR-043), Salary/SalaryProjected from the newest PlayerValuation snapshot under `data-derived/player-valuation` (ADR-055). Age uses the date of `Timestamps.json -> Players` as reference date. The earlier statements in this document that `Players.json` remains enrichment for those fields are historical.

Checkpoint 6R activates the canonical Roster/Reserve/Taxi ownership union for `external-signal-relevance.json`.
Issue #1263 C8 subsequently removes its last `public/data/League.json` display input: the
Fantasy Operations presentation adapter `operations_team_display.py` joins stable TeamID/member IDs
to `data-source/leagues/<CanonicalLeagueID>/seasons/<season>/members.json`, using member
`Metadata.team_name` (or `Team <DisplayName>`) and a presentation-only abbreviation compatible
with the existing App display convention. The six current team labels/abbreviations are golden-tested
against `League.json` but the Operations producer never reads it. League roster ownership
continues to come exclusively from canonical season rosters; the existing output contracts and
workflow triggering remain unchanged. Other Fantasy Operations consumers still have independent
League/Timestamps overlays until their own field-level cutovers.

Issue #1263 C8b next applies the same member display projection to
`managed-roster-signals.json` and `data-quality.json`: the managed team label
no longer reads App `League.json`. The `Timestamps.json -> Players` date
continues to anchor player Age and the existing timestamps source retains
its freshness/provenance role. Other Operations overlays remain separate.

Issue #1263 C8c applies the same member-based team display projection to
`player-signals.json`. Its canonical league scoring and all player evaluation,
ownership, source joining and population contracts remain unchanged. The
`Timestamps.json -> Players` reference date and freshness source record remain
explicit inputs; removing those is a later, separately validated project.

Checkpoint 6S extends the same Canonical League ownership union to `player-signals.json`. Its ownership status and `league_owned` population reason are canonical-derived. Checkpoint 6Y additionally moves `Name`, fantasy-relevant `Position`, Sleeper `Status`, `IDs.ESPN` and nominal Sleeper depth-chart fields to Canonical NFL Identity/Platform sources. External name+position joins use the Canonical Identity display name first and, only when that join is missing, may fall back to the Canonical Identity `FirstName + LastName` form; they never fall back to the legacy App name, and ambiguous alias matches remain fail-closed. Checkpoint 6Z.1 moves `player-signals.nfl_team` and team-assisted external-source evaluation to Canonical Sleeper `Team`, and Checkpoint C2 (Issue #347, 2026-10-05) replaces the former `has_nfl_team` population reason, which was sourced from `Players.json -> TeamAbbr`, with Canonical NFL roster evidence resolved by CanonicalPlayerID: `canonical_nfl_membership` (latest materialized weekly roster) and `canonical_nfl_recent_history` (current-season season roster or any current-season weekly roster). Provider team fields (Sleeper Team, Tank01 `TeamAbbr`/`IsFreeAgent`) never create population membership. The cutover removed 304 players without NFL roster membership in 2026, no external source or signal and no league ownership, and added none. `Players.json` otherwise remains enrichment for Age/Experience, Salary/SalaryProjected, Tank01 `IsFreeAgent` and the structured Injury contract. This previously published App display/ScoringType statement is historical: C8c now owns team display from canonical members and #347 A2 already migrated projection scoring to canonical `ScoringSettings`.

Checkpoint 6T extends Canonical League ownership to `fa-board-readmodel.json`: availability ownership, owner/bucket attribution and Managed-Team Roster/Reserve/Taxi occupancy now come from Canonical League Source Data. Since #1263 C8e, FA-board rules/capacity and team display use Canonical League season/member sources instead of App League.json; central lifecycle owns state and canonical drafts own the active Free-Agent-Draft assignment axis.

Checkpoint 6U removes the Managed-Roster-Overview's duplicate direct membership read from `League.json`. `managed-roster-overview.json` now derives held/active/reserve/taxi membership exclusively from `managed-roster-signals.json`; Since #1263 C8d, team display uses canonical members and roster positions/Taxi/Reserve capacity use canonical league settings. Shared lifecycle continues to own phase; `League.json` is no longer an Overview input.

Checkpoint 6V moves the Free-Agent Movement consumer's league-scoring input from `public/data/League.json -> ScoringType` to the active Canonical League `league.json -> ScoringSettings`. This is a scoring-only cutover: Movement population and ownership remain inherited from canonical-active `player-signals.json` / `free-agent-signals.json`; `player-signals` projection reconciliation followed in #347 step A2 and now reads league scoring from the same canonical `ScoringSettings` (via `canonical_league_ownership.load_canonical_league_scoring_settings`; the previous silent empty-scoring fallback is now a fail-closed error). Kicker Streaming inputs followed in #347 step A1 and now read kicker scoring from the same canonical `ScoringSettings` (team, season and phase context still come from `League.json`).

Checkpoint 6W removes the direct `public/data/Players.json` dependency from `external-signal-relevance.json`. Sleeper signal IDs resolve through the active `IDs.Sleeper` bridge in `data-source/nfl/identities/players.json`; player names come from that Canonical Identity contract, while fantasy-relevant position and current NFL team come from `data-source/nfl/platform/sleeper/players.json`. Position prefers the first provider-ordered QB/RB/WR/TE/K entry from `FantasyPositions` and falls back to raw `Position` when no such fantasy role exists (so dual-role players such as Travis Hunter remain WR rather than inheriting Sleeper's raw DB primary position). Duplicate active Sleeper identity links, duplicate platform Sleeper IDs and cross-source CanonicalPlayerID disagreement fail closed. Checkpoint 6Y later applies the same Canonical Identity/`FantasyPositions` contract to selected non-team player-signal fields; App-owned Salary/SalaryProjected/Grading and `RequestPlayers.ps1` remain outside that cutover.

This is **not** a wholesale Fantasy Management source cutover. `free-agent-signals.json` is already downstream of canonical-active `player-signals` and therefore inherits canonical fantasy ownership without its own direct League read. Draft metadata, Transactions, Salary/Grading and other unmigrated source domains retain their currently documented contracts until separately migrated.


## Metadata source rules

`data-meta/<CanonicalLeagueID>/metadata.json` is the canonical source for owner/team mapping and league-specific manual inputs.

Known mapping may include:

| Real name | TeamID / OwnerID mapping value |
|---|---:|
| Robert | 1 |
| Marcel | 2 |
| Flo | 3 |
| Jan | 4 |
| Dennis | 5 |
| Tim | 6 |

Always re-check the league metadata (`data-meta/<CanonicalLeagueID>/metadata.json`) when exact owner mapping matters.

## Player source rules

`public/data/Players.json` is the canonical current raw player read model from the application context. Fantasy Management consumes it read-only and must not require the app producer to create AI- or agent-specific reduced copies or chunk exports. During the field-by-field Phase-2 cutover it is no longer the identity source for every Operations consumer: `external-signal-relevance.json` is fully canonical for identity/platform fields since 6W; `managed-roster-signals.json` uses Canonical NFL identity/position/team fields since 6X; and `player-signals.json` uses Canonical NFL name/position, Sleeper status/depth and Canonical ESPN identity since 6Y. The player-signal TeamAbbr/population bridge plus App-owned/legacy enrichment fields remain on `Players.json`.

For broad operational analysis, prefer the smallest current Fantasy-Management-owned derived contract that matches the task instead of scanning the raw player file:

1. `fantasy-management/generated/operations/player-signals.json` for the league-wide QB/RB/WR/TE/K operational population and joined market, projection, activity, ownership, injury and nominal-role signals.
2. `fantasy-management/generated/operations/free-agent-signals.json` for the complete current ownership-derived fantasy-free-agent population used by general discovery and movement processing.
3. `fantasy-management/generated/operations/fa-board-readmodel.json` for current/live Free-Agent-Draft availability, current draft assignment, Reserve-/Taxi-Eligibility, immediate slot-cost and compact market context.
4. `fantasy-management/generated/operations/managed-roster-signals.json` for Mighty Giants roster-focused work.

When a raw app field or an exact player record is needed, read the targeted current record from `public/data/Players.json`. Do not recreate `Players_Relevant.json` or a chunked chat export merely to make the player data easier for a specific AI client to ingest.

Important player fields may include ID, name fields, NFL team, position, age, salary, projected salary, status, injury fields, games played/potential, snaps, attempts, fantasy points, point history, game history, ranking, grading, FantasyPros and ESPN fields, plus `ESPNID`, `SleeperDepthChartPosition` and `SleeperDepthChartOrder` when present.

### Sleeper player metadata and nominal depth-chart fields

`public/requests/RequestPlayers.ps1` already loads the Sleeper NFL player payload used during player generation. The generated player record can persist the following raw Sleeper-backed fields without an additional source request:

- `ESPNID` from Sleeper `espn_id`
- `SleeperDepthChartPosition` from Sleeper `depth_chart_position`
- `SleeperDepthChartOrder` from Sleeper `depth_chart_order`

Operational rules:

For `player-signals.json`, Checkpoint 6Y no longer reads these mirrored identity/role values from `Players.json`: ESPN identity comes from `data-source/nfl/identities/players.json -> IDs.ESPN`, while Sleeper status and nominal depth-chart fields come from `data-source/nfl/platform/sleeper/players.json`. The mirrored App fields may remain for other App consumers until their own contracts migrate.

- Treat `ESPNID` as optional supplemental identity metadata. Sleeper does not populate it reliably for every current player, so it must not be the sole identity key or automatically override an already confirmed player mapping.
- Treat `SleeperDepthChartPosition` as the source-provided nominal football slot or alignment. For wide receivers this can distinguish values such as `LWR`, `RWR` and `SWR`.
- Treat `SleeperDepthChartOrder` as the source-provided nominal team-wide hierarchy within the player's fantasy position. The interpretation and recommendation safeguards are defined in `FANTASY_MANAGEMENT_RULES.md`.
- Null or partial depth-chart fields are valid source states and are not automatically data-quality failures; free agents, roster transitions, camp competitions and unresolved depth charts can legitimately remain incomplete.
- Sleeper depth-chart values are dynamic role observations, not permanent player truth. Re-read current generated player data when role matters instead of carrying an older order forward from memory or stored analysis.
- Depth-chart position and order are nominal role signals only. Do not treat them as direct evidence of snap share, routes, targets, carries, goal-line work or expected fantasy opportunity.
- When Sleeper depth-chart data conflicts with current transactions, official team information, observed usage or strong current role reporting, preserve the conflict and validate it instead of silently preferring the numeric order.

## Fantasy free-agent source rules

`Players.json -> IsFreeAgent` is not a fantasy-league free-agent signal.

Fantasy ownership is consumer-scoped during Phase 2. `external-signal-relevance.json`, `player-signals.json` and `fa-board-readmodel.json` now use the Canonical League Roster/Reserve/Taxi union for fantasy ownership. `free-agent-signals.json` is selected downstream from canonical-active `player-signals`, so its ownership population is canonical-derived without a separate League read. `Players.json -> IsFreeAgent` is never a fantasy-league ownership signal.

`fantasy-management/generated/operations/free-agent-signals.json` remains the complete current ownership-derived free-agent population for general Fantasy Operations discovery, movement analysis and research prioritization. It is selected from canonical-active `player-signals.json` ownership rather than from a separate `League.json` union or `Players.json -> IsFreeAgent`.

For a live or current Free-Agent Draft, use `fantasy-management/generated/operations/fa-board-readmodel.json` as the preferred compact decision-infrastructure source. It combines the fully evaluated league ownership state, the currently resolved Free-Agent Draft from `Drafts.json`, provider-neutral player/injury signals, current Reserve-/Taxi-Eligibility and compact FantasyCalc/FantasyPros context. It exposes per player:

- `availability_status` (`available`, `rostered`, `drafted`, `unknown`);
- owner and roster bucket when currently owned;
- current FA-draft status and assigned pick/owner where applicable;
- current Reserve-/Taxi-Eligibility and special-capacity context;
- `active_slot_cost_now` and `active_slot_cost_on_materialization`;
- market/ranking snapshot and freshness metadata.

Availability is fail-closed. Only an explicit `availability_status = available` from a schema-valid readmodel with resolved mandatory inputs is a positive availability result. `unknown` must not be presented as available. External rankings, activity or `free-agent-signals.json` alone must never override a positive ownership or already-assigned current-draft result.

The distinction is intentional: `free-agent-signals.json` can correctly say that a player is absent from every materialized League roster while the same player has already been selected in the running FA Draft but not yet materialized into `League.json`. The FA-board readmodel closes that gap by evaluating both canonical axes together.

When the population or availability must be reconstructed from base contracts instead of using the current derived contract directly:

1. load the current Canonical League manifest plus current-season league/member/roster partitions and build the complete Roster/Reserve/Taxi ownership union through the stable TeamID→CanonicalLeagueMemberID bridge;
2. load the validated canonical current-season `league.json` for `RosterPositions` and Reserve-/Taxi settings plus canonical `members.json` for team display; phase/status/kickoff/week come only from shared lifecycle;
3. load complete current `Drafts.json` and resolve the current relevant Free-Agent Draft plus every assigned `Status: Picked` player;
4. load the current operational player population from `fantasy-management/generated/operations/player-signals.json`;
5. treat a positive canonical league ownership or current assigned draft pick as not available;
6. emit `available` only when both negative checks are complete and unambiguous; otherwise keep `unknown`;
7. evaluate Reserve-/Taxi-Eligibility and capacity from current League rule enrichment plus Canonical Managed-Team occupancy and current player/injury fields;
8. read targeted records from `public/data/Players.json` only when exact raw app fields are needed.

A negative result from a truncated or incomplete connector response is never sufficient to prove absence.

## Draft source rules

Current team draft-pick ownership starts from:

`League.json -> Teams[].DraftPicks`

Pick metadata is resolved through:

`public/data/Drafts.json -> Picks[]`

Never infer true pick position only from a pick key such as `R1` or `OO5`. For current ownership, use `CurrentOwnerRosterID`, not `OriginalOwnerRosterID`.

For live/current Free-Agent-Draft player availability, `Drafts.json` is the canonical raw draft-status source, while `fantasy-management/generated/operations/fa-board-readmodel.json` is the preferred fully joined operational readmodel. A player already assigned to a current FA-draft pick remains unavailable even if Sleeper has not yet materialized that player into `League.json`.

## Transaction source rules

`public/data/Transactions.json` is the current source for completed transactions. Use it for trade history, add/drop history, pick movements, market activity and provenance checks.

When current state and transaction history disagree, current state from `League.json` wins for roster and pick ownership.

## Timestamp source rules

Check `public/data/Timestamps.json` before larger analyses when data freshness matters.

## External fantasy sources

External sources may be used for expert, market, ADP, projection, activity, injury, news or plausibility context. They supplement current league data and never override it automatically.

Always:

- fetch dynamic external rankings, values, ADP, projections, activity signals, injuries and news fresh when used
- cite external claims in user-facing responses
- explain what each source measures
- do not store dynamic external values or signals as permanent truth
- reconcile every source with the actual league format and Mighty Giants context

### Automated external-source HTTP resilience

Automated external-source fetchers that depend on HTTP or public HTML must treat temporary transport and provider throttling as an operational failure mode without weakening source validation.

Operational rules:

- use bounded retries for transient network failures and retryable HTTP responses, including `403`, `408`, `425`, `429` and relevant `5xx` statuses when the source contract makes a later retry meaningful;
- use increasing backoff with small jitter between attempts and respect a valid `Retry-After` response header within a bounded maximum wait;
- keep retries finite; a persistently blocked, unavailable or invalid source must still fail closed rather than being treated as a successful refresh;
- fail immediately on non-retryable client errors unless a source-specific audited contract explicitly documents otherwise;
- when a final HTTP error is available, retain actionable diagnostics such as status, reason and a short sanitized response excerpt without storing an entire error page as source data;
- do not overwrite the last good published source state or success heartbeat after an unsuccessful fetch;
- run source-identity, schema, completeness, freshness and plausibility validation only on a successful response and never relax those checks merely because retries were needed;
- add source-specific pacing when repeated requests or pagination make provider throttling likely;
- retries are resilience, not access-control circumvention: do not automate challenge solving, authentication bypasses or other mechanisms that evade a provider's access restrictions;
- a 403 that carries an access challenge (Cloudflare `Just a moment...` body or `cf-mitigated: challenge` header) is not transient: it is raised as `HttpFetchBlockedError` without retries (Issue #1045);
- a seasonal source (FFToday publishes preseason projections only) makes no request outside its active NFL phase, taken from the canonical season context (`tools/external_source/season_phase.py`, driven by the `seasonPolicy` of the dataset in `data-source/external-registry.json`), and ends successfully with a `skipped` message so the daily pipeline stays green;
- when this contract is added or changed, audit existing automated fetchers separately for implementation drift instead of assuming documentation alone makes them compliant.

### External-ranking hierarchy

Active external ranking, ADP, market-value and projection providers are shared Source Evidence (ADR-060, Issue #988) and live in the shared source layer, not in `fantasy-management`:

```text
data-source/market/<ranking_kind>/<provider>/<format>/   normalized snapshots, latest.json
data-source/providers/<provider>/<dataset>/               raw-latest.*, README, SOURCE_AUDIT, analysis-metadata
data-source/market/_status/<provider>.json                refresh heartbeat
```

`fantasy-management/sources/external-rankings/` keeps only audits of inspected but inactive sources and manual-reference notes (KeepTradeCut, Dynasty Data Lab, FantasyPros ADP) plus the ranking-kind rules below. Fetchers live in `tools/external_source/`; Fantasy Management reads the moved snapshots only as a transitional consumer until the `market-observations` product exists.

The first level describes how the ordering is produced, not who publishes it.

Active and reserved ranking kinds:

- `expert-consensus`: ordering derived from expert opinions
- `market-value`: ordering or values derived from trade/crowd market behavior
- `adp`: ordering derived from observed draft positions
- `projections`: ordering derived from expected statistical or fantasy production for a defined horizon

Provider comes second because one provider can publish more than one ranking kind and several providers can publish the same kind. Format comes last and records horizon, scoring, league-size and lineup assumptions.

The canonical hierarchy and common rules are documented in:

`fantasy-management/sources/external-rankings/README.md`

### External-signal hierarchy

External activities and events that do not evaluate player or asset quality are shared Source Evidence (ADR-060). The Sleeper roster-activity signal moved to the shared source layer:

```text
data-source/market/roster-activity/<provider>/   normalized latest.json
data-source/providers/<provider>/<dataset>/      raw-latest.json, README, SOURCE_AUDIT, analysis-metadata
```

The current active signal kind is:

- `roster-activity`: observed add/drop or comparable platform activity

Source signals remain provider-global. In the productive external-signal relevance materializer, Mighty Giants ownership, opponent ownership and fantasy-free-agent status are derived later by joining the normalized signal with Canonical League ownership plus current player data; `League.json` contributes only team display metadata for that consumer.

The canonical hierarchy and common rules are documented in:

`fantasy-management/sources/external-signals/README.md` (generic rules) and `.ai-context/manual/external-source-data.yaml` (contract)

### FantasyPros expert-consensus snapshots

Stored source area:

`data-source/market/expert-consensus/fantasypros/`

Available ranking IDs:

- `dynasty-superflex-ppr`: long-term asset and expert-consensus context
- `redraft-ppr-superflex`: current-season lineup, production and win-now context

For each ranking, use `latest.json` to resolve the newest successful snapshot. Load `ranking.csv` as the compact analysis table, `data-source/providers/fantasypros/<ranking-id>/raw-latest.json` when additional source fields or schema inspection matter, and `metadata.json` for provenance, freshness and ranking-specific interpretation.

Refresh directly from the official FantasyPros pages with:

```bash
python -m tools.external_source.fantasypros --skip-unchanged
python -m tools.external_source.fantasypros_redraft --skip-unchanged
```

Both fetchers must fail closed after network, source-identity, schema, row-count or rank-validation errors. A successful refresh retains the complete parsed `ecrData` payload and writes the normalized consensus fields.

Canonical source documentation:

- `data-source/providers/fantasypros/README.md`
- `data-source/providers/fantasypros/analysis-metadata.json`

Operational rules:

- never assume `rank_ecr` must lie inside `rank_min`/`rank_max`
- interpret `rank_std` as dispersion of source-provided ranks, not total panel coverage or outcome confidence
- keep explanations about unranked players, weighting and cache alignment unconfirmed unless FantasyPros documents them
- retain ECR-outside-range cases and diagnostics
- join Dynasty and Redraft primarily through `source_player_id`
- prefer snapshots fetched on the same day
- normalize ranks to list-length-aware percentiles before calculating gaps
- do not use raw rank differences across lists with different pools or lengths

FantasyPros ECR is expert consensus. It is not ADP, a projection or league-specific truth.

### FantasyCalc market-value snapshots

Stored source area:

`data-source/market/market-value/fantasycalc/` (snapshots and `latest.json`), raw responses and documentation under `data-source/providers/fantasycalc/`, heartbeat `data-source/market/_status/fantasycalc.json` (shared source layer, ADR-060)

Available ranking IDs:

- `dynasty-superflex-ppr-8-team`: observed long-term trade-market values including source draft-pick assets
- `redraft-superflex-ppr-8-team`: observed current-season trade-market values

FantasyCalc is queried with two quarterbacks, full PPR and the provider's nearest supported eight-team parameter. New snapshots carry no league team count. No TEP parameter is used because two fixed TE starters are not equivalent to Tight-End-Premium scoring.

For each ranking, use `latest.json` to resolve the newest normalized snapshot and current `raw-latest.json`. Historical snapshots contain only `ranking.csv` and `metadata.json`; the complete API payload is retained only as the latest Raw response.

Refresh both formats with:

```bash
python -m tools.external_source.fantasycalc --skip-unchanged
```

Canonical source documentation:

- `data-source/providers/fantasycalc/README.md`
- `data-source/providers/fantasycalc/analysis-metadata.json`

Operational rules:

- treat FantasyCalc as observed trade-market context, not expert consensus or a projection
- use normalized `Rank` for ordering and per-centile comparisons; retain `source_overall_rank` as an audit field with permitted ties
- join players primarily through `sleeper_id`, then `source_asset_id`, then normalized name plus position
- resolve only FantasyCalc's explicit `UNK` player-position sentinel through matching `SleeperPlayerID -> Position` from `data-source/nfl/platform/sleeper/players.json`; do not use `public/data/Players.json` for that fallback and keep all other unexpected provider positions fail-closed
- treat FantasyCalc draft-pick IDs as source-only synthetic identifiers
- resolve real pick identity and ownership from `League.json` and `Drafts.json`
- apply six-team replacement-level context after reading the eight-team proxy
- apply additional scarcity for two fixed QB and two fixed TE starters during analysis
- compare FantasyCalc and FantasyPros through normalized percentiles, not raw value-to-rank arithmetic
- visibly attribute FantasyCalc whenever its values are shown

### KeepTradeCut manual-reference restriction

KeepTradeCut belongs under:

`fantasy-management/sources/external-rankings/market-value/keeptradecut/`

Its current status is `manual_reference_only`. Do not create an automated fetcher or workflow unless the published automation policy changes or explicit permission is obtained.

### Fantasy Football Calculator ADP snapshots

Fantasy Football Calculator is the active automated ADP provider.

Stored source area:

`data-source/market/adp/fantasy-football-calculator/`

Available ranking IDs:

- `redraft-ppr-8-team`: observed Full-PPR mock-draft cost in the nearest supported small-league format for QB/RB/WR/TE
- `redraft-ppr-8-team-kicker`: Kicker-only ADP derived from the same PPR 8-team all-position API payload without an additional network request
- `redraft-2qb-10-team`: observed 2-QB mock-draft cost used primarily for quarterback-scarcity context

For each ranking, use `latest.json` to resolve the newest normalized snapshot and the current Raw-fetch state. Load `ranking.csv` as the compact analysis table, `metadata.json` for source format, sample quality, provenance and freshness, and `data-source/providers/fantasy-football-calculator/<ranking-id>/raw-latest.json` only when the complete latest API payload or excluded source positions matter.

Refresh all active FFC rankings together with:

```bash
python -m tools.external_source.fantasy_football_calculator --skip-unchanged
```

Canonical source documentation:

- `data-source/providers/fantasy-football-calculator/README.md`
- `data-source/providers/fantasy-football-calculator/analysis-metadata.json`

Operational rules:

- treat Fantasy Football Calculator as observed mock-draft cost, not expert consensus, trade-market value or points projection
- do not average the PPR-8-team and 2QB-10-team feeds because team count, scoring context and quarterback requirements differ simultaneously
- use the PPR-8-team offensive feed as the closest supported small-league and Full-PPR proxy for RB, WR and TE draft cost
- use the 2QB-10-team feed as additional quarterback-scarcity evidence, not as a direct model of the six-team league
- use `redraft-ppr-8-team-kicker` only as a Kicker-market ranking and normalize it against other Kicker rankings, not against the offensive cross-position list
- materialize the Kicker ranking from the already fetched PPR payload; do not add a separate FFC request for it
- apply the actual six-team replacement level, two fixed QB, two fixed TE and one fixed K starter only during analysis; do not mutate source ADP values
- consider `times_drafted`, source sample window, `high`, `low` and `stdev` before treating small ADP movements as material, especially for kickers
- join players through confirmed source-player mappings or normalized name plus position; Fantasy Football Calculator IDs are source identifiers, not Sleeper IDs
- visibly attribute Fantasy Football Calculator whenever its ADP values are shown

### FFToday projection snapshots

FFToday is an active automated Projection provider for QB, RB, WR, TE and K.

Stored source area:

`data-source/market/projection/fftoday/` (snapshots), `data-source/providers/fftoday/` (raw files and provider docs)

Active ranking IDs:

- `redraft-qb-preseason`: provider Regular-Season QB projections with passing and rushing raw stats retained
- `redraft-rb-preseason`: provider Regular-Season RB projections with rushing and receiving raw stats retained
- `redraft-wr-preseason`: provider Regular-Season WR projections with receiving and rushing raw stats retained
- `redraft-te-preseason`: provider Regular-Season TE projections with receiving raw stats retained
- `redraft-kicker-preseason`: provider Regular-Season Kicker projections ordered by projected FFToday fantasy points, with FGM/FGA/FG%/EPM/EPA retained

The audited public Projection area also exposes DEF and IDP projections. Those positions remain outside the current active league-lineup scope.

Refresh with:

```bash
python -m tools.external_source.fftoday_kicker --skip-unchanged
python -m tools.external_source.fftoday_offense --skip-unchanged
```

The workflow `FM • Pipeline • Daily` (matrix job `Provider • fftoday`) refreshes the source daily before monitoring.

Canonical source documentation:

- `fantasy-management/sources/external-rankings/projections/README.md`
- `data-source/providers/fftoday/README.md`
- `data-source/providers/fftoday/SOURCE_AUDIT.md`
- `data-source/providers/fftoday/analysis-metadata.json`

Operational rules:

- treat FFToday Projections as expected production, not expert consensus, ADP or trade-market value
- use only the public non-authenticated page; do not create or automate a My-FFToday login or custom-scoring profile
- retain position-specific raw statistics separately from provider `FPts`
- do not treat FFToday `FPts` as Mighty-Giants league scoring
- for QB/RB/WR/TE, calculate league-specific `core_points` only in the Derived Operations layer from scoring-relevant raw stats that are comparably available from the active providers; never impute unprojected components
- offensive FFToday feeds may span multiple public pages; follow the public `Next Page` chain completely and fail closed on loops, duplicate Source IDs, inconsistent source dates or implausibly small populations
- retain only the newest Raw HTML and archive changed normalized ranking/metadata snapshots
- compare Projection rankings only within the same position through list-length-aware percentiles

### CBS Sports projection snapshots

CBS Sports is an active automated Projection provider for QB, RB, WR, TE and K. The GitHub-Actions workflow `FM • Pipeline • Daily` (matrix job `Provider • cbs-sports`) refreshes the source daily from 05:20 Europe/Berlin and supports manual `workflow_dispatch` runs.

Stored source area:

`data-source/market/projection/cbs-sports/` (normalized snapshots) and `data-source/providers/cbs-sports/` (latest raw HTML and source documentation)

Active ranking IDs:

- `redraft-qb-preseason`: provider Regular-Season QB projections with passing and rushing raw stats retained
- `redraft-rb-preseason`: provider Regular-Season RB projections with rushing, targets and receiving raw stats retained
- `redraft-wr-preseason`: provider Regular-Season WR projections with targets, receiving and rushing raw stats retained
- `redraft-te-preseason`: provider Regular-Season TE projections with targets and receiving raw stats retained
- `redraft-kicker-preseason`: provider Regular-Season Kicker projections ordered by projected CBS fantasy points, retaining FGM/FGA, five field-goal distance buckets, XPM/XPA, FPTS and FPPG

The audited public Projection area also exposes DST projections. DST remains outside the current active league-lineup scope.

Refresh directly with:

```bash
python -m tools.external_source.cbs_sports_kicker --skip-unchanged
python -m tools.external_source.cbs_sports_offense --skip-unchanged
```

Canonical source documentation:

- `fantasy-management/sources/external-rankings/projections/README.md`
- `data-source/providers/cbs-sports/README.md`
- `data-source/providers/cbs-sports/SOURCE_AUDIT.md`
- `data-source/providers/cbs-sports/analysis-metadata.json`

Operational rules:

- treat CBS Sports Projections as expected production, not expert consensus, ADP or trade-market value
- use the public Non-PPR projection pages without login; source stats and provider points remain provider-specific evidence
- retain position-specific offensive raw stats separately from provider `FPTS`/`FPPG`
- retain Kicker FGM/FGA, XPM/XPA and the five CBS field-goal distance buckets separately from provider `FPTS`
- preserve decimal Kicker distance-bucket projections; accept CBS `—` bucket values only for a true FGM/FGA zero-projection and normalize those buckets to zero
- do not treat CBS `FPTS` as Mighty-Giants league scoring
- for QB/RB/WR/TE, calculate league-specific `core_points` only in the Derived Operations layer from scoring-relevant raw stats that are comparably available from the active providers; never impute unprojected components
- CBS exposes no reliable visible projection-updated timestamp on the audited page; store fetch time and HTTP provenance and do not invent `source_updated_date`
- fail closed on source-identity, row-count, duplicate-ID, numerical-plausibility or unexpected-pagination failures
- retain only the newest Raw HTML and archive changed normalized ranking/metadata snapshots
- do not double-weight CBS Sports and a Projection Consensus when that consensus already includes CBS Sports

### Sleeper Trending Players roster-activity signal

Sleeper Trending Players is the active automated external roster-activity signal.

Stored source area:

`data-source/market/roster-activity/sleeper/` (normalized `latest.json`) and `data-source/providers/sleeper/trending/` (raw evidence and documentation). The freshness heartbeat is `data-source/market/_status/sleeper.json`.

Default signal configuration:

- platform-wide NFL activity
- separate add and drop lists
- rolling 24-hour lookback
- top 100 results per activity type
- daily refresh target

Refresh both activity types with:

```bash
python -m tools.external_source.sleeper_trending
```

The first successful run creates `raw-latest.json` and `latest.json` as a silent baseline. Later compatible runs compare source membership, ranks and counts with the previous successful state.

Canonical source documentation:

- `data-source/providers/sleeper/trending/README.md`
- `data-source/providers/sleeper/trending/SOURCE_AUDIT.md`
- `data-source/providers/sleeper/trending/analysis-metadata.json`

Operational rules:

- treat the source as global activity and attention, not as a ranking, value, projection or league-specific fact
- fetch add and drop successfully before publishing either output
- fail closed and retain the previous successful state after any incomplete or invalid refresh
- keep missing top-N entries as `not_listed` with null rank and count; never convert absence to zero activity
- compare only identical schema, provider, lookback and limit configurations
- interpret count deltas as differences between overlapping rolling windows, not new transactions since the prior fetch
- join to current league ownership only downstream through `sleeper_player_id`
- retain unresolved IDs as data-quality findings
- use trends only as targeted research and monitoring triggers
- never derive automatic add, drop, trade, hold, shop or cut actions from this source alone
- attribute stored and user-facing uses with `Trending data provided by Sleeper`

### FantasyPros ADP restriction

FantasyPros ADP is not an active automated or stored ranking source.

The live source check on 4 August 2026 established that anonymous access exposes only five player rows. The rendered page and its embedded report payload contain the same five-player excerpt, followed by an account gate. The former `export=xls` route does not provide a complete anonymous export on the GitHub runner.

Operational consequences:

- do not use or store the anonymous FantasyPros top-five excerpt as a complete ADP ranking
- do not recreate a FantasyPros ADP crawler, parser, provider directory or workflow from the current anonymous pages
- do not substitute FantasyPros ECR fields for ADP
- use Fantasy Football Calculator as the active automated ADP source
- reconsider FantasyPros ADP only when a complete anonymous official feed becomes available or the user explicitly approves an authenticated official access method and its required secrets

The durable investigation record and common ranking rules are documented in:

`fantasy-management/sources/external-rankings/README.md`

## Fantasy Management internal sources

The Fantasy Management workspace stores source, Knowledge, analysis and decision artifacts under `fantasy-management/`.

Important active subfolders:

- `fantasy-management/sources/`
- `fantasy-management/knowledge/`
- `fantasy-management/analyses/`
- `fantasy-management/decisions/`

These files are useful context but are not canonical current league state.

## Podcast source areas

Podcast source packages belong under `fantasy-management/sources/podcasts/`. Stoned Lack, Down Set Talk and Football Bromance are qualitative secondary sources whose fantasy specificity and reliability depend on the subject.

Always distinguish internal league data, source perspective, current external market/news context and the final Mighty Giants recommendation. Raw transcripts may contain transcription errors, especially player names; use the identity registry and verify uncertain names when they matter.

## Analysis artifacts are not permanent truth

Files under `analyses/`, `knowledge/` and `decisions/` are context and history. They are not current truth for roster, pick ownership, salary/cap state, injuries, rankings, market values or NFL depth charts.

Re-derive dynamic facts from current repository data and current external sources when needed.