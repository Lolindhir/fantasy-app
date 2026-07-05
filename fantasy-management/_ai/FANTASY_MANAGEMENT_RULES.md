# Fantasy Management AI Rules

Purpose: this file defines how agents should perform Fantasy Management analysis and recommendations.

These rules replace chat-level Fantasy Management instructions for this repository area.

## 1. Sources first

For any new Fantasy Management task:

1. read `fantasy-management/AGENTS.md`
2. read `fantasy-management/_ai/FANTASY_MANAGEMENT_SOURCES.md`
3. read this file
4. read `fantasy-management/_ai/WORKFLOWS.md` when the task involves extraction, analysis storage or repeated workflow steps
5. load current repo data when dynamic facts are needed

Do not answer dynamic roster, trade, salary, draft or player questions from memory alone.

## 2. User team and perspective

The user team is:

- Team name: `Mighty Giants`
- TeamID: `1`

Team recommendations must be from the Mighty Giants perspective.

Do not evaluate Mighty Giants as an abstract team. Consider:

- current roster
- current picks
- cap/salary context
- league format
- contender/rebuild window
- current season phase
- user preferences and decisions stored under `fantasy-management/decisions/`

## 3. Dynamic values must be re-derived

Always re-check current sources when relevant:

- roster
- reserve and taxi
- draft picks
- salary/cap state
- cap deadline
- trades/waivers/cuts openness
- season phase
- player status and injuries
- external rankings and market values

Stored analyses are historical context, not current truth.

## 4. Off-season starter rule

In the off-season, `League.json -> Teams[].Starter` is not a reliable quality or role signal.

The user does not actively maintain starters during the off-season.

Use starters only when the task is about in-season lineup or start/sit context.

## 5. League format rule

Always inspect `League.json -> RosterSize` and `League.json -> ScoringType` when player value depends on format.

Known current format may include:

- 2 QB
- 2 RB
- 2 WR
- 2 TE
- 4 FLEX
- 1 K
- 16 BN

Implications:

- QBs are strongly boosted because two fixed QB spots exist.
- TEs are strongly boosted because two fixed TE spots exist.
- RB and WR depth matters because four flex spots exist.
- In a 6-team league, replacement level is high, so quality matters more than mere playability.
- Depth still matters because many weekly slots must be filled.
- Kickers are usually replaceable unless the data shows a special reason.

Core question:

Can this player regularly provide a meaningful weekly contribution in this 2QB / 2TE / 4Flex format, serve as valuable scarce-position backup, or be used as a trade asset for an upgrade?

## 6. Salary rule

Salary is not a direct quality measure.

User-provided salary logic:

- salary is calculated from performance over the last three years
- rookies and young players cost less because they lack a full three-year production history
- high salary often reflects past production but not necessarily future quality
- low salary for rookies does not automatically imply weak quality

Use salary for:

- cap management
- roster management
- cut/trade timing
- opportunity cost
- projected salary risk
- rookie/prospect discount context
- salary-relevant team-size calculations

Do not use salary as the primary signal for:

- talent
- quality
- future value
- weekly startability

## 7. Player quality criteria

Use internal data primarily from:

- fantasy points
- average points per game
- average points per potential game
- point history
- game history
- games played and games potential
- availability and injury status
- snaps
- attempts/touches/routes where available
- points per snap or attempt
- touchdown profile
- position role
- age and career phase
- league-format fit

For players with little history, distinguish between lack of production and lack of opportunity.

## 8. Player-list and free-agent rule

For broad player lists, free-agent drafts, waiver boards and candidate generation:

1. do not operate directly from full `Players.json` if chunked player exports are available
2. load the chunk index first
3. load only relevant player chunks
4. build complete candidate lists through the chunks
5. for fantasy free agents, exclude all IDs present in any roster, reserve or taxi list in `League.json`
6. do not use `IsFreeAgent` as fantasy-league availability
7. verify top candidates through their concrete player records
8. add external market context only after the internal candidate set is complete

## 9. Mighty Giants role categories

Use these categories when useful:

- Core Asset
- Win-Now Producer
- Value Starter
- Depth / Backup
- Contingent Upside
- Prospect / Stash
- Trade Chip
- Cap / Cut Risk

## 10. Recommendation labels

Use concise labels for player recommendations:

- Core Hold
- Hold for 2026
- Hold as Value
- Shop
- Package Piece
- Stash
- Monitor
- Cut Candidate

Always explain the label.

## 11. Team-window strategy

Do not automatically treat Mighty Giants as a rebuild team.

Evaluate the window from current data:

- previous placement
- points production
- point differential
- roster strength
- pick inventory
- salary/cap state
- playoff format

When data indicates a contender window:

- prioritize quality over quantity
- prefer consolidation trades when possible
- use bench players and picks as package pieces for upgrades
- keep young assets when their value fits the title window or creates trade leverage
- avoid preserving depth that only blocks liquidity

Core question:

Does this player help Mighty Giants win, serve as a future building block, or represent blocked liquidity?

## 12. External source rules

External sources may be used when they add value.

Always:

1. fetch fresh data when rankings, market values, news, injuries or ADP matter
2. cite user-facing claims sourced externally
3. explain what the source measures
4. avoid treating a single external source as truth
5. do not invent rankings, ADP, market values or news
6. make unavailable or conflicting sources explicit

External source weighting:

- FantasyPros Dynasty ECR: expert/consensus context
- FantasyPros redraft/PPR: short-term win-now context
- KeepTradeCut: crowd and market sentiment
- FantasyCalc: trade-database and market plausibility context
- ESPN/player profiles: player, news and team context where current and relevant

External sources supplement internal league data. They do not override it.

## 13. StonedLack rules

StonedLack is a source perspective, not a final projection.

Use StonedLack for:

- rookie upside
- prospect profiles
- sleepers
- fades
- buy/sell/watchlist takes
- role-path arguments
- source conviction
- source philosophy

Always label StonedLack as a source perspective, for example:

- "StonedLack sees ..."
- "the StonedLack extraction says ..."
- "according to the StonedLack source note ..."

Do not present StonedLack as current live news or as the final Mighty Giants recommendation.

## 14. Transcript extraction rules

When processing StonedLack or other fantasy football transcripts:

1. read `AGENTS.md`, source rules, analysis rules and the podcast-specific extraction guide
2. treat the raw transcript as the primary trace
3. do not clean the raw transcript content except allowed metadata/frontmatter
4. separate original statement, cleaned name/entity mapping and agent interpretation
5. do not invent missing details
6. use `unknown`, `unverified`, `low confidence` or explicit uncertainty notes when needed
7. atomize takes into player, type, fantasy context, format context, sentiment, conviction, arguments, risks and evidence
8. use short evidence or paraphrase with timestamp; avoid long quotes
9. verify names, teams, draft context and landing spots through current sources when decision-relevant
10. create or update reusable output files under the correct podcast/source folder

## 15. Transparency in user-facing responses

When giving player, trade or roster recommendations, separate where useful:

### Internal league data says

- production
- game history
- roster role
- position
- age
- salary as cap factor
- league-format fit

### External sources say

- market context
- expert context
- rankings, values or trends with source and freshness

### StonedLack / source input says

- source takes
- rankings or tiers
- sentiment
- conviction
- strategy notes

### My Mighty Giants recommendation

- hold / shop / package / cut / stash
- why this is appropriate for TeamID 1 and this league format

When data is missing, say so plainly.

## 16. Trade and roster logic

For a strong Mighty Giants team:

- evaluate consolidation trades
- treat picks as liquidity, not only draft ammunition
- consider using 2026 picks for win-now upgrades when the price and player fit are right
- do not burn future picks casually
- keep bench depth only when it is format-relevant, young/upside-heavy or strong injury insurance
- identify roster cloggers early

## 17. Position logic

### QB

Strongly boosted by two fixed QB spots.

### RB

Important for fixed RB and flex spots. Short-term production matters for contenders, but age and role risk are important.

### WR

Often more stable long-term. Flex depth matters, but in a 6-team league upper starter/flex quality matters most.

### TE

Strongly boosted by two fixed TE spots. Mid-tier TEs may be more valuable than in standard formats if they produce usable weekly points.

### K

Usually replaceable.

### Picks

Flexible assets. Resolve true current pick ownership through `League.json -> Teams[].DraftPicks` joined to `Drafts.json -> Picks[]`.

## 18. Common mistakes to avoid

Do not:

- use off-season starter lists as quality rankings
- treat salary as talent or quality
- name external rankings without live checking when current values matter
- invent ADP, rankings, market values or injury news
- treat StonedLack takes as final recommendations
- infer players from bad transcript names without verification
- use `IsFreeAgent` as fantasy-league availability
- read draft-pick keys as true pick position without `Drafts.json`
- confuse `OriginalOwnerRosterID` with current pick ownership
- present old chat values as current data
- ignore league format
- ignore 6-team replacement level
- evaluate players by name only
- overvalue prospects just because salary is low
- undervalue veterans automatically when they help a contender window

## 19. Standard single-player analysis structure

Use this structure when helpful:

1. short verdict
2. role for Mighty Giants
3. internal data
4. format fit: 2QB / 2TE / 4Flex
5. salary/cap relevance
6. external market/ranking context if checked
7. StonedLack/source input if relevant
8. risks
9. recommendation label

## 20. Standard team-analysis structure

Use this structure when helpful:

1. data state and sources
2. league format
3. roster by position
4. player role categories
5. cap/salary situation
6. picks and trade liquidity
7. team window
8. concrete recommendations
9. uncertainties
