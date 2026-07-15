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

Reason: the full file is large and may be truncated in tool or chat contexts.

For broad player lists, waiver/free-agent boards and candidate generation, use:

1. `public/data/chat/players-relevant/index.json`
2. the matching `public/data/chat/players-relevant/players_*.json` chunks

For a single player, load the relevant chunk or exact current player record before drawing conclusions.

Important player fields may include ID, name fields, NFL team, position, age, salary, projected salary, status, injury fields, games played/potential, snaps, attempts, fantasy points, point history, game history, ranking, grading, FantasyPros and ESPN fields.

## Fantasy free-agent source rules

`Players.json -> IsFreeAgent` is not a fantasy-league free-agent signal.

A player is fantasy-owned if the player's ID appears in any team `Roster`, `Reserve` or `Taxi` list in `League.json`.

A fantasy free agent is only a player whose ID does not appear in any roster, reserve or taxi list.

For free-agent boards:

1. load current `League.json`
2. collect every owned player ID from all teams' `Roster`, `Reserve` and `Taxi`
3. load relevant player chunks through the chunk index
4. remove owned IDs
5. evaluate the remaining candidates
6. verify top candidates through their concrete player records

## Draft source rules

Current team draft-pick ownership starts from:

`League.json -> Teams[].DraftPicks`

Pick metadata is resolved through:

`public/data/Drafts.json -> Picks[]`

Never infer true pick position only from a pick key such as `R1` or `OO5`.

For current ownership, use `CurrentOwnerRosterID`, not `OriginalOwnerRosterID`.

## Transaction source rules

`public/data/Transactions.json` is the current source for completed transactions.

Use it for trade history, add/drop history, pick movements, market activity and provenance checks.

When current state and transaction history disagree, current state from `League.json` wins for roster and pick ownership.

## Timestamp source rules

Check `public/data/Timestamps.json` before larger analyses when data freshness matters.

## External fantasy sources

External sources may be used for market, expert or plausibility context.

Examples:

- FantasyPros Dynasty Rankings / ECR
- FantasyPros PPR or redraft rankings
- KeepTradeCut dynasty rankings / trade calculator / market values
- FantasyCalc dynasty rankings / trade database
- ESPN player profiles
- official NFL/team/college pages for identity, roster and injury context

Rules:

- fetch external rankings, values, ADP, injury/news and market context fresh when used
- cite the source in user-facing responses when external data is used
- explain what the source measures
- do not let external sources override current league data
- do not store dynamic external rankings as permanent truth

### FantasyPros Dynasty Superflex PPR snapshot

Stored source area:

`fantasy-management/sources/external-rankings/fantasypros/dynasty-superflex-ppr/`

Use `latest.json` to resolve the newest successful snapshot. Load `ranking.csv` as the compact analysis table, `raw-ecr-data.json` when additional source fields or schema inspection matter, and `metadata.json` for provenance and freshness.

Refresh directly from the official FantasyPros page with:

```bash
python fantasy-management/_ai/scripts/fetch_fantasypros_dynasty_superflex.py
```

The fetcher must fail closed: do not update `latest.json` after network, schema, row-count or rank-validation errors. A successful refresh must retain the complete parsed `ecrData` payload, write a normalized CSV with `position_rank`, `tier`, `rank_min`, `rank_max`, `rank_ave` and `rank_std`, and document both files plus field coverage and cross-field diagnostics in metadata.

Interpret FantasyPros consensus fields as follows:

- use `tier` as the source-provided value cluster and prefer meaningful tier breaks over small rank differences inside one tier
- use `rank_std` as the primary expert-dispersion signal; lower means tighter agreement and higher means wider disagreement
- use `rank_min` and `rank_max` as best/worst submitted expert-rank extremes and remember that their range may be driven by an outlier
- use `rank_ave` as the average submitted expert rank
- treat `rank_ecr` as FantasyPros' final published consensus ordering; it is not guaranteed to lie inside `rank_min`/`rank_max`
- retain and document ECR-outside-range cases as source diagnostics rather than rejecting the complete snapshot
- do not interpret dispersion as a probability, projection confidence, injury risk or guarantee that the ECR will be correct

Treat FantasyPros Dynasty ECR as expert-consensus context, not ADP or league-specific truth. For the current fixed-2QB Mighty Giants league, apply an additional quarterback-scarcity interpretation only during analysis, not by mutating the source snapshot.

## Fantasy Management internal sources

The Fantasy Management workspace stores source, Knowledge, analysis and decision artifacts under:

`fantasy-management/`

Important active subfolders:

- `fantasy-management/sources/`
- `fantasy-management/knowledge/`
- `fantasy-management/analyses/`
- `fantasy-management/decisions/`

These files are useful context but are not canonical current league state.

## Stoned Lack source area

Stoned Lack podcast data belongs under:

`fantasy-management/sources/podcasts/stoned-lack/`

Stoned Lack is a secondary qualitative source, not a primary league source.

Use it for:

- rookie/prospect takes
- source sentiment
- conviction
- tiers and rankings
- sleeper/buy/sell/fade/watchlist takes
- source philosophy
- strategy notes
- later meta-analysis across episodes

Always distinguish:

- internal league data
- Stoned Lack source perspective
- current external market data
- final Mighty Giants recommendation

Raw transcripts may contain automatic transcription errors, especially player names. Use cleaned entity mappings where available and verify uncertain names when they matter.

## Relevant Players source area

User-provided or generated Relevant Players files belong under:

`fantasy-management/sources/relevant-players/`

These files can supplement generated app/player chunks, but they must not override current generated league state unless explicitly documented.

## Analysis artifacts are not permanent truth

Files under `analyses/`, `knowledge/` and `decisions/` are useful context and history.

They must not be treated as current truth for dynamic values such as current roster, current pick ownership, current salary/cap state, current injuries, current rankings, current market values or current NFL depth charts.

Re-derive dynamic facts from current sources when needed.
