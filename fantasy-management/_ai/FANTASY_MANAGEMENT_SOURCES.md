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
- `public/data/chat/players-relevant/index.json`
- `public/data/chat/players-relevant/players_*.json`

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

Do not use the full `public/data/Players.json` as the operational source for broad player lists in chat or agent workflows when chunked player exports are available.

For broad player lists, waiver/free-agent boards and candidate generation, use:

1. `public/data/chat/players-relevant/index.json`
2. the matching `public/data/chat/players-relevant/players_*.json` chunks

For a single player, load the relevant chunk or exact current player record before drawing conclusions.

Important player fields may include ID, name fields, NFL team, position, age, salary, projected salary, status, injury fields, games played/potential, snaps, attempts, fantasy points, point history, game history, ranking, grading, FantasyPros and ESPN fields.

## Fantasy free-agent source rules

`Players.json -> IsFreeAgent` is not a fantasy-league free-agent signal.

A player is fantasy-owned if the player's ID appears in any team `Roster`, `Reserve` or `Taxi` list in `League.json`. A fantasy free agent is only a player whose ID does not appear in any of those lists.

For free-agent boards:

1. load current `League.json`
2. collect every owned player ID from roster, reserve and taxi
3. load relevant player chunks through the chunk index
4. remove owned IDs
5. evaluate the remaining candidates
6. verify top candidates through their concrete player records

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

External sources may be used for expert, market, ADP, injury, news or plausibility context. They supplement current league data and never override it automatically.

Always:

- fetch dynamic external rankings, values, ADP, injuries and news fresh when used
- cite external claims in user-facing responses
- explain what each source measures
- do not store dynamic external values as permanent truth
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

Provider comes second because one provider can publish more than one ranking kind and several providers can publish the same kind. Format comes last and records horizon, scoring, league-size and lineup assumptions.

The canonical hierarchy and common rules are documented in:

`fantasy-management/sources/external-rankings/README.md`

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

### ADP sources

ADP is an external ranking kind. The first implemented provider must be stored under:

`fantasy-management/sources/external-rankings/adp/<provider>/<format>/`

ADP measures observed draft cost and must remain distinct from expert consensus and trade-market value even though all are normalized as rankings.

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

## Relevant Players source area

User-provided or generated Relevant Players files belong under:

`fantasy-management/sources/relevant-players/`

They can supplement generated app/player chunks but do not override current generated league state unless explicitly documented.

## Analysis artifacts are not permanent truth

Files under `analyses/`, `knowledge/` and `decisions/` are context and history. They are not current truth for roster, pick ownership, salary/cap state, injuries, rankings, market values or NFL depth charts.

Re-derive dynamic facts from current repository data and current external sources when needed.
