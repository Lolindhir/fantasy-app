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
- `public/data/Metadata.json`

## League source rules

`public/data/League.json` is the primary current source for league settings, team rosters, reserve lists, taxi lists, starters when in season, draft-pick references, roster size, lineup settings, scoring, salary cap fields and current league phase/status fields.

The user team is:

- Team name: `Mighty Giants`
- TeamID: `1`

For Mighty Giants analysis, always identify the team by `TeamID = 1` in current data.

## Metadata source rules

`public/data/Metadata.json` is the canonical source for owner/team mapping and league-specific manual inputs.

Known mapping may include:

| Real name | TeamID / OwnerID mapping value |
|---|---:|
| Robert | 1 |
| Marcel | 2 |
| Flo | 3 |
| Jan | 4 |
| Dennis | 5 |
| Tim | 6 |

Always re-check `Metadata.json` when exact owner mapping matters.

## Player source rules

`public/data/Players.json` is the canonical current raw player read model from the application context. Fantasy Management consumes it read-only and must not require the app producer to create AI- or agent-specific reduced copies or chunk exports.

For broad operational analysis, prefer the smallest current Fantasy-Management-owned derived contract that matches the task instead of scanning the raw player file:

1. `fantasy-management/generated/operations/player-signals.json` for the league-wide QB/RB/WR/TE/K operational population and joined market, projection, activity, ownership, injury and nominal-role signals.
2. `fantasy-management/generated/operations/free-agent-signals.json` for the complete current fantasy-free-agent population.
3. `fantasy-management/generated/operations/managed-roster-signals.json` for Mighty Giants roster-focused work.

When a raw app field or an exact player record is needed, read the targeted current record from `public/data/Players.json`. Do not recreate `Players_Relevant.json` or a chunked chat export merely to make the player data easier for a specific AI client to ingest.

Important player fields may include ID, name fields, NFL team, position, age, salary, projected salary, status, injury fields, games played/potential, snaps, attempts, fantasy points, point history, game history, ranking, grading, FantasyPros and ESPN fields, plus `ESPNID`, `SleeperDepthChartPosition` and `SleeperDepthChartOrder` when present.

### Sleeper player metadata and nominal depth-chart fields

`public/requests/RequestPlayers.ps1` already loads the Sleeper NFL player payload used during player generation. The generated player record can persist the following raw Sleeper-backed fields without an additional source request:

- `ESPNID` from Sleeper `espn_id`
- `SleeperDepthChartPosition` from Sleeper `depth_chart_position`
- `SleeperDepthChartOrder` from Sleeper `depth_chart_order`

Operational rules:

- Treat `ESPNID` as optional supplemental identity metadata. Sleeper does not populate it reliably for every current player, so it must not be the sole identity key or automatically override an already confirmed player mapping.
- Treat `SleeperDepthChartPosition` as the source-provided nominal football slot or alignment. For wide receivers this can distinguish values such as `LWR`, `RWR` and `SWR`.
- Treat `SleeperDepthChartOrder` as the source-provided nominal team-wide hierarchy within the player's fantasy position. The interpretation and recommendation safeguards are defined in `FANTASY_MANAGEMENT_RULES.md`.
- Null or partial depth-chart fields are valid source states and are not automatically data-quality failures; free agents, roster transitions, camp competitions and unresolved depth charts can legitimately remain incomplete.
- Sleeper depth-chart values are dynamic role observations, not permanent player truth. Re-read current generated player data when role matters instead of carrying an older order forward from memory or stored analysis.
- Depth-chart position and order are nominal role signals only. Do not treat them as direct evidence of snap share, routes, targets, carries, goal-line work or expected fantasy opportunity.
- When Sleeper depth-chart data conflicts with current transactions, official team information, observed usage or strong current role reporting, preserve the conflict and validate it instead of silently preferring the numeric order.

## Fantasy free-agent source rules

`Players.json -> IsFreeAgent` is not a fantasy-league free-agent signal.

A player is fantasy-owned if the player's ID appears in any team `Roster`, `Reserve` or `Taxi` list in `League.json`. A fantasy free agent is only a player whose ID does not appear in any of those lists.

For free-agent boards, prefer the current `fantasy-management/generated/operations/free-agent-signals.json` contract. It represents the complete current fantasy-free-agent population for Fantasy Operations and must remain downstream of current league ownership rather than `Players.json -> IsFreeAgent`.

When the population must be reconstructed from base contracts instead of using `free-agent-signals.json` directly:

1. load current `League.json`
2. collect every owned player ID from roster, reserve and taxi
3. load the current operational player population from `fantasy-management/generated/operations/player-signals.json`
4. exclude every owned player ID
5. evaluate the remaining candidates with the current derived signals
6. read targeted records from `public/data/Players.json` only when exact raw app fields are needed

## Draft source rules

Current team draft-pick ownership starts from:

`League.json -> Teams[].DraftPicks`

Pick metadata is resolved through:

`public/data/Drafts.json -> Picks[]`

Never infer true pick position only from a pick key such as `R1` or `OO5`. For current ownership, use `CurrentOwnerRosterID`, not `OriginalOwnerRosterID`.

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

### External-ranking hierarchy

All ordered external player or asset evaluations belong under:

```text
fantasy-management/sources/external-rankings/<ranking_kind>/<provider>/<format>/
```

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

External activities and events that do not evaluate player or asset quality belong under:

```text
fantasy-management/sources/external-signals/<signal_kind>/<provider>/
```

The current active signal kind is:

- `roster-activity`: observed add/drop or comparable platform activity

Source signals remain provider-global. Mighty Giants ownership, opponent ownership and fantasy-free-agent status are derived only later by joining the normalized signal with current `League.json` and player data.

The canonical hierarchy and common rules are documented in:

`fantasy-management/sources/external-signals/README.md`

### FantasyPros expert-consensus snapshots

Stored source area:

`fantasy-management/sources/external-rankings/expert-consensus/fantasypros/`

Available ranking IDs:

- `dynasty-superflex-ppr`: long-term asset and expert-consensus context
- `redraft-ppr-superflex`: current-season lineup, production and win-now context

For each ranking, use `latest.json` to resolve the newest successful snapshot. Load `ranking.csv` as the compact analysis table, `raw-ecr-data.json` when additional source fields or schema inspection matter, and `metadata.json` for provenance, freshness and ranking-specific interpretation.

Refresh directly from the official FantasyPros pages with:

```bash
python fantasy-management/_ai/scripts/fetch_fantasypros_dynasty_superflex.py --skip-unchanged
python fantasy-management/_ai/scripts/fetch_fantasypros_redraft_ppr_superflex.py --skip-unchanged
```

Both fetchers must fail closed after network, source-identity, schema, row-count or rank-validation errors. A successful refresh retains the complete parsed `ecrData` payload and writes the normalized consensus fields.

Canonical source documentation:

- `fantasy-management/sources/external-rankings/expert-consensus/fantasypros/README.md`
- `fantasy-management/sources/external-rankings/expert-consensus/fantasypros/analysis-metadata.json`

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

`fantasy-management/sources/external-rankings/market-value/fantasycalc/`

Available ranking IDs:

- `dynasty-superflex-ppr-8-team`: observed long-term trade-market values including source draft-pick assets
- `redraft-superflex-ppr-8-team`: observed current-season trade-market values

FantasyCalc is queried with two quarterbacks, full PPR and the nearest supported eight-team proxy for the actual six-team league. No TEP parameter is used because two fixed TE starters are not equivalent to Tight-End-Premium scoring.

For each ranking, use `latest.json` to resolve the newest normalized snapshot and current `raw-latest.json`. Historical snapshots contain only `ranking.csv` and `metadata.json`; the complete API payload is retained only as the latest Raw response.

Refresh both formats with:

```bash
python fantasy-management/_ai/scripts/fetch_fantasycalc_rankings.py --skip-unchanged
```

Canonical source documentation:

- `fantasy-management/sources/external-rankings/market-value/fantasycalc/README.md`
- `fantasy-management/sources/external-rankings/market-value/fantasycalc/analysis-metadata.json`

Operational rules:

- treat FantasyCalc as observed trade-market context, not expert consensus or a projection
- use normalized `Rank` for ordering and per-centile comparisons; retain `source_overall_rank` as an audit field with permitted ties
- join players primarily through `sleeper_id`, then `source_asset_id`, then normalized name plus position
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

`fantasy-management/sources/external-rankings/adp/fantasy-football-calculator/`

Available ranking IDs:

- `redraft-ppr-8-team`: observed Full-PPR mock-draft cost in the nearest supported small-league format for QB/RB/WR/TE
- `redraft-ppr-8-team-kicker`: Kicker-only ADP derived from the same PPR 8-team all-position API payload without an additional network request
- `redraft-2qb-10-team`: observed 2-QB mock-draft cost used primarily for quarterback-scarcity context

For each ranking, use `latest.json` to resolve the newest normalized snapshot and the current Raw-fetch state. Load `ranking.csv` as the compact analysis table, `metadata.json` for source format, sample quality, provenance and freshness, and `raw-latest.json` only when the complete latest API payload or excluded source positions matter.

Refresh all active FFC rankings together with:

```bash
python fantasy-management/_ai/scripts/fetch_fantasy_football_calculator_adp.py --skip-unchanged
```

Canonical source documentation:

- `fantasy-management/sources/external-rankings/adp/fantasy-football-calculator/README.md`
- `fantasy-management/sources/external-rankings/adp/fantasy-football-calculator/analysis-metadata.json`

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

`fantasy-management/sources/external-rankings/projections/fftoday/`

Active ranking IDs:

- `redraft-qb-preseason`: provider Regular-Season QB projections with passing and rushing raw stats retained
- `redraft-rb-preseason`: provider Regular-Season RB projections with rushing and receiving raw stats retained
- `redraft-wr-preseason`: provider Regular-Season WR projections with receiving and rushing raw stats retained
- `redraft-te-preseason`: provider Regular-Season TE projections with receiving raw stats retained
- `redraft-kicker-preseason`: provider Regular-Season Kicker projections ordered by projected FFToday fantasy points, with FGM/FGA/FG%/EPM/EPA retained

The audited public Projection area also exposes DEF and IDP projections. Those positions remain outside the current active league-lineup scope.

Refresh with:

```bash
python fantasy-management/_ai/scripts/fetch_fftoday_kicker_projections.py --skip-unchanged
python fantasy-management/_ai/scripts/fetch_fftoday_offense_projections.py --skip-unchanged
```

The workflow `FM • Projection • FFToday` refreshes the source daily before monitoring and also runs once after a fetcher, fetcher test or workflow-contract change reaches `main`.

Canonical source documentation:

- `fantasy-management/sources/external-rankings/projections/README.md`
- `fantasy-management/sources/external-rankings/projections/fftoday/README.md`
- `fantasy-management/sources/external-rankings/projections/fftoday/SOURCE_AUDIT.md`
- `fantasy-management/sources/external-rankings/projections/fftoday/analysis-metadata.json`

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

CBS Sports is an active automated Projection provider for QB, RB, WR, TE and K. The GitHub-Actions workflow `FM • Projection • CBS Sports` refreshes the source daily at 06:08 Europe/Berlin, supports manual `workflow_dispatch` runs and also runs once after its fetcher, fetcher test or workflow contract changes on `main`.

Stored source area:

`fantasy-management/sources/external-rankings/projections/cbs-sports/`

Active ranking IDs:

- `redraft-qb-preseason`: provider Regular-Season QB projections with passing and rushing raw stats retained
- `redraft-rb-preseason`: provider Regular-Season RB projections with rushing, targets and receiving raw stats retained
- `redraft-wr-preseason`: provider Regular-Season WR projections with targets, receiving and rushing raw stats retained
- `redraft-te-preseason`: provider Regular-Season TE projections with targets and receiving raw stats retained
- `redraft-kicker-preseason`: provider Regular-Season Kicker projections ordered by projected CBS fantasy points, retaining FGM/FGA, five field-goal distance buckets, XPM/XPA, FPTS and FPPG

The audited public Projection area also exposes DST projections. DST remains outside the current active league-lineup scope.

Refresh directly with:

```bash
python fantasy-management/_ai/scripts/fetch_cbs_sports_kicker_projections.py --skip-unchanged
python fantasy-management/_ai/scripts/fetch_cbs_sports_offense_projections.py --skip-unchanged
```

Canonical source documentation:

- `fantasy-management/sources/external-rankings/projections/README.md`
- `fantasy-management/sources/external-rankings/projections/cbs-sports/README.md`
- `fantasy-management/sources/external-rankings/projections/cbs-sports/SOURCE_AUDIT.md`
- `fantasy-management/sources/external-rankings/projections/cbs-sports/analysis-metadata.json`

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

`fantasy-management/sources/external-signals/roster-activity/sleeper/`

Default signal configuration:

- platform-wide NFL activity
- separate add and drop lists
- rolling 24-hour lookback
- top 100 results per activity type
- daily refresh target

Refresh both activity types with:

```bash
python fantasy-management/_ai/scripts/fetch_sleeper_trending.py
```

The first successful run creates `raw-latest.json` and `latest.json` as a silent baseline. Later compatible runs compare source membership, ranks and counts with the previous successful state.

Canonical source documentation:

- `fantasy-management/sources/external-signals/roster-activity/sleeper/README.md`
- `fantasy-management/sources/external-signals/roster-activity/sleeper/SOURCE_AUDIT.md`
- `fantasy-management/sources/external-signals/roster-activity/sleeper/analysis-metadata.json`

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