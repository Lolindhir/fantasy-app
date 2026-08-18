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

For player, trade, roster, free-agent, draft or board recommendations, do not rely on only one side of the data model:

- internal league data must be checked for current league fit, ownership, scoring, salary/cap context and Mighty Giants relevance
- current external sources must be checked when player role, market value, rankings, ADP, injuries, NFL team context or news matter
- when the user explicitly asks for a quick or repo-only answer, label the missing external check as a limitation

## 2. User team and perspective

The user team is:

- Team name: `Mighty Giants`
- TeamID: `1`

Team recommendations must be from the Mighty Giants perspective.

Do not evaluate Mighty Giants as an abstract team. Consider current roster, picks, cap/salary context, league format, contender/rebuild window, current season phase and user decisions stored under `fantasy-management/decisions/`.

## 3. Dynamic values must be re-derived

Always re-check current sources when relevant: roster, reserve and taxi, draft picks, salary/cap state, cap deadline, trades/waivers/cuts openness, season phase, player status and injuries, external rankings and market values.

Stored analyses are historical context, not current truth.

Treat the canonical repository league data as current by default. An older value in `Timestamps.json`, an older commit or modification date, or the absence of a recent regeneration is not evidence that the league state is stale; unchanged league state legitimately retains older timestamps.

Do not warn about stale or inconsistent league data based on timestamps alone. Question repository currency only when concrete content conflicts across canonical files, required data is missing, a generation process reports failure, or the user states that the repo has not yet incorporated a known change. When such evidence exists, identify the exact conflict instead of inferring staleness from age.

Internal league data is the current league source of truth by default, but it can still be incomplete, generated, or misleading for current player evaluation. Treat internal values as league-specific evidence, not as a final conclusion about player quality or future role.

Assumptions based on league data require a plausibility check against current external sources when they affect a recommendation. External claims require the reverse check against current league data before applying them to Mighty Giants.

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

### Replacement-level and marginal-gain guardrail

External Superflex, 2QB or other format-adjusted overall rankings are starting points for player value, not direct league-specific draft, waiver or trade boards.

Before using a format-driven positional premium in a recommendation:

- derive actual positional scarcity from current league size, fixed starter requirements, flex eligibility, roster depth and the current rostered/free-agent player pool;
- treat the presence of multiple startable players at the same position in the fantasy free-agent pool as evidence that league-specific replacement level may be materially higher than generic market rankings imply;
- in shallow leagues, especially this 6-team format, explicitly downweight generic Superflex QB scarcity when the real league pool shows abundant startable QB replacement;
- compare a candidate against the weakest relevant Mighty Giants starter, flex option or scarce-position backup threshold rather than against an abstract positional rank alone;
- distinguish **starting-lineup marginal gain**, **depth/injury-insurance value**, **dynasty/market/trade-asset value** and **strategic/blocking value** instead of collapsing them into one player rank;
- do not recommend the highest generic overall-ranked player as the best Mighty Giants move unless either the league-specific marginal gain or the asset/liquidity case justifies that choice.

This guardrail applies to QB, TE and every other position whose generic external value is materially affected by format-driven scarcity.

Core question:

Can this player regularly provide a meaningful weekly contribution in this 2QB / 2TE / 4Flex format, serve as valuable scarce-position backup, or be used as a trade asset for an upgrade?

### Free-Agent Draft pick opportunity-cost guardrail

Free-Agent Draft picks are a distinct asset type and must not inherit the value of a same-numbered Rookie Draft pick or a generic external pick label.

When a Free-Agent Draft pick is part of a trade, draft or roster recommendation:

- resolve the pick's exact overall position through current `League.json -> Teams[].DraftPicks` joined to `Drafts.json -> Picks[]`;
- build the current fantasy-free-agent population by excluding every player owned on any roster, reserve or taxi list;
- estimate the realistic player shelf likely to remain at that exact overall selection rather than valuing the pick only by round label;
- adjust that shelf for actual league replacement level, positional needs, likely manager behavior and positional drafting tendencies when evidence exists;
- treat the estimated shelf as an opportunity-cost range, not as a deterministic draft forecast;
- compare a trade target against that shelf across Mighty Giants lineup gain, depth value, dynasty/liquidity value and roster fit;
- recommend moving the pick only when the received asset sufficiently beats the league-specific draft alternative for the intended purpose.

Generic external values for a label such as `2026 Pick 2.04` may be used only when they represent the same asset type and format. Do not use a generic Rookie Draft pick value as a proxy for a Free-Agent Draft pick with the same displayed round and slot.

### Free-Agent Draft dynamic-pool guardrail

For this league, the Free-Agent Draft is a single mixed player pool, not a rookie-only draft and not a veteran-only waiver event.

Draft eligibility and draft-board analysis must follow these league mechanics:

- every fantasy free agent who is eligible at that moment can be drafted, regardless of whether the player is a rookie or veteran;
- a player cut before the Free-Agent Draft becomes part of the draftable player pool;
- a player cut during the Free-Agent Draft becomes draft-eligible for subsequent selections in that same draft;
- therefore the available-player pool is dynamic throughout the draft and must not be treated as a frozen pre-draft snapshot;
- after each material selection or roster cut, re-evaluate the remaining board, replacement shelf and Mighty Giants opportunity cost when a later Mighty Giants pick is still pending;
- draft simulations should include plausible cuts by other managers when there is evidence for likely roster pressure, but speculative cuts must be labeled as scenarios rather than current availability;
- Mighty Giants may strategically make already-justified cuts before the draft when doing so can widen the pool and create alternative targets for other managers, but do not cut a player with superior expected keep/trade value merely to create a decoy;
- when evaluating such a pre-draft cut, separate the player's residual trade value from the strategic value of adding him to the draft pool. A failed trade market is relevant evidence, but not by itself proof that the player has no keep value.

For any Mighty Giants selection after `1.01`, the relevant question is not only who was free before the draft started. It is who is actually available at that exact selection after all prior picks and intervening cuts.

## 6. Salary rule

Salary is a relevant roster-management and cap-management signal, especially in the off-season around the cap deadline. Salary is not a direct quality measure and is not a reliable standalone player-evaluation signal.

User-provided salary logic:

- salary is calculated from performance over the last three years
- rookies and young players can have no salary or artificially low salary because they lack a full three-year production history
- players without three continuous relevant seasons can have misleadingly low salary
- high salary often reflects past production but not necessarily future quality
- low salary does not automatically imply weak quality or high surplus value
- projected salary can be useful for cap planning, but it must not be treated as a projection of player quality

Use salary for cap management, off-season cap-deadline decisions, roster management, cut/trade timing, opportunity cost, projected salary risk, rookie/prospect discount context and salary-relevant team-size calculations.

Do not use salary as the primary signal for talent, quality, future value, weekly startability or player rank.

When salary affects a recommendation, explicitly separate salary as cap/roster-management factor from player quality or role evaluation.

## 7. Grading and ranking rule

`Grading` is not implemented as a reliable evaluation layer yet. Do not use `Players*.json -> Grading` as evidence for player quality, player rank, player upside, draft value, free-agent priority, trade value or cut decisions.

Do not use a `Grading` entry such as `Grade: "A"` as a shortcut for quality. Until the grading model is implemented and documented, ignore `Grading` in AI recommendations.

If explicit rankings exist in `Ranking`, use them only when:

- the ranking source and meaning are clear
- the ranking is current enough for the decision
- the ranking is cross-checked against league format and external plausibility
- the ranking is not contradicted by stronger current role, injury or market evidence

If `Ranking` is empty or unclear, say so instead of inferring a rank from salary, starters, roster order, player name, or grading.

## 8. Player quality criteria

Use internal data primarily from fantasy points, average points per game, average points per potential game, point history, game history, games played/potential, availability and injury status, snaps, attempts/touches/routes where available, points per snap or attempt, touchdown profile, position role, age and career phase, and league-format fit.

For players with little history, distinguish between lack of production and lack of opportunity.

Always add a plausibility layer before turning player data into a recommendation:

- check whether the internal team, status, injury and role context still matches current external information
- check whether external rankings, ADP or news make sense in this league's scoring, roster size and replacement-level context
- state unresolved conflicts plainly

### Rookie draft-capital and taxi guardrail

For rookies and very early-career prospects, NFL draft capital is a first-class evaluation signal and must be checked explicitly before recommending a cut, drop, taxi move or stash decision.

When a rookie is materially near the roster cut line:

- record the NFL draft round and exact overall pick when available;
- treat Day 1 and Day 2 NFL draft capital as meaningful evidence of team investment, expected opportunity and organizational conviction, while still checking current role, health, usage and competition;
- compare NFL draft capital with the player's fantasy Rookie Draft acquisition cost, but do not keep a player merely because Mighty Giants previously spent a pick on him; fantasy acquisition cost is context, not a sunk-cost justification;
- do not let a temporarily weak Dynasty ECR, ADP or market value automatically override meaningful NFL draft capital before the player has had a reasonable opportunity to establish or lose an NFL role;
- explicitly distinguish a prospect whose market value is low because his NFL thesis has failed from one whose thesis is still unresolved because of injury, depth-chart timing, limited opportunity or normal rookie development;
- compare the rookie against other Mighty Giants rookies/prospects and the actual free-agent replacement shelf before cutting him;
- use age, athletic profile, production, receiving/three-down path, positional competition and current team context to determine how much patience the draft-capital prior deserves;
- lower the protection from draft capital when stronger current evidence shows the team has moved on, the player has lost the relevant role, the underlying profile has materially failed or roster opportunity cost is clearly higher.

Taxi slots are flexible rookie-development slots, not protection for the players currently occupying them.

For Mighty Giants cut and roster-limit analysis:

- evaluate every taxi-eligible rookie in the same prospect pool regardless of whether he is currently listed on `Roster` or `Taxi`;
- do not exclude current Taxi players from cut consideration merely because they are already on Taxi;
- rank all eligible rookies/prospects first, then allocate the available Taxi slots to the best stash candidates after deciding which total assets to keep;
- when Taxi eligibility allows it, prefer using Taxi to preserve unresolved high-upside rookies who have low immediate starting utility but meaningful future role or market-value upside.

NFL draft capital is a strong prior, not an absolute hold rule. The final decision must still be league-specific and based on expected future value, role path, replacement level and opportunity cost.

### Opportunity provenance guardrail

Historical production must be interpreted together with how the opportunity was created, especially for rookies, breakouts, backups and players with only one meaningful season of usage.

When production materially affects a recommendation, check whether snaps, routes, targets, carries or other opportunity were opened by:

- teammate injuries or season-long absences;
- suspensions;
- trades, releases or roster turnover;
- temporary depth-chart vacancies;
- unusually favorable game-script or short-term roster conditions.

Distinguish where possible between:

- **earned opportunity**: the player won and retained a meaningful role against available competition;
- **vacated opportunity**: meaningful volume became available because normal competition was absent or temporarily removed.

Production from vacated opportunity remains evidence that a player could function in an NFL role and should not be discarded. It must not, however, be projected forward automatically when the missing competition returns or the temporary vacancy closes.

When opportunity was mixed, state the dependency explicitly, evaluate the returning competition and lower forward-looking confidence until the player demonstrates that the role is retained under more normal conditions.

### Sleeper depth-chart interpretation

Current generated player data may expose the Sleeper fields `SleeperDepthChartPosition` and `SleeperDepthChartOrder`.

Interpret them as follows unless current evidence shows a source anomaly:

- `SleeperDepthChartPosition` describes the nominal football depth-chart slot or alignment. For wide receivers this can be more specific than the fantasy position, for example `LWR`, `RWR` or `SWR`.
- `SleeperDepthChartOrder` is the nominal team-wide hierarchy within the player's fantasy position and can therefore be used as structured evidence for labels such as QB1/QB2, RB1/RB2, WR1/WR2/WR3, TE1/TE2 or K1.
- For wide receivers, do not interpret `RWR / 2` as "second player at RWR" by default. Treat the slot and the position-wide order as separate dimensions: for example `RWR / 2` means nominal right-side receiver and team-wide WR2.
- A missing depth-chart position or order is not automatically a source error. Free agents, roster transitions, camp competitions and unresolved depth-chart states can legitimately produce null or partial values.
- Depth-chart hierarchy is a nominal role signal only. It is not direct evidence of snap share, routes, targets, carries, passing-down work, goal-line work or expected fantasy opportunity.
- Never convert `SleeperDepthChartOrder = 1` directly into "highest opportunity" or a fantasy recommendation without usage, injury, competition and current team-context checks when those matter.
- When Sleeper depth-chart data conflicts with stronger current roster transactions, official team information, observed usage or well-supported current role reporting, identify the conflict and lower confidence instead of silently trusting the numeric order.
- For role/opportunity monitoring, use Sleeper depth-chart changes as a structured trigger or nominal-role component and combine them with usage/news evidence before treating a change as materially fantasy-relevant.

## 9. Player-list and free-agent rule

For broad player lists, free-agent drafts, waiver boards and candidate generation:

1. do not operate directly from full `Players.json` if chunked player exports are available
2. load the chunk index first
3. load only relevant player chunks
4. build complete candidate lists through the chunks
5. for fantasy free agents, exclude all IDs present in any roster, reserve or taxi list in `League.json`
6. do not use `IsFreeAgent` as fantasy-league availability
7. verify top candidates through their concrete player records
8. add current external market, ranking, injury and role context after the internal candidate set is complete
9. reconcile internal league availability with external player relevance before final board placement

## 10. Mighty Giants role categories

Use these categories when useful:

- Core Asset
- Win-Now Producer
- Value Starter
- Depth / Backup
- Contingent Upside
- Prospect / Stash
- Trade Chip
- Cap / Cut Risk

## 11. Recommendation labels

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

## 12. Team-window strategy

Do not automatically treat Mighty Giants as a rebuild team.

Evaluate the window from current data: previous placement, points production, point differential, roster strength, pick inventory, salary/cap state and playoff format.

When data indicates a contender window:

- prioritize quality over quantity
- prefer consolidation trades when possible
- use bench players and picks as package pieces for upgrades
- keep young assets when their value fits the title window or creates trade leverage
- avoid preserving depth that only blocks liquidity

Core question:

Does this player help Mighty Giants win, serve as a future building block, or represent blocked liquidity?

## 13. External source rules

External sources are required when they materially affect player evaluation, role assumptions, market value, rankings, ADP, injuries, NFL team context, depth charts, news, or current availability.

Always:

1. fetch fresh data when rankings, market values, news, injuries or ADP matter
2. cite user-facing claims sourced externally
3. explain what the source measures
4. avoid treating a single external source as truth
5. do not invent rankings, ADP, market values or news
6. make unavailable or conflicting sources explicit
7. translate external information into this league's scoring, roster size, salary/cap and Mighty Giants context before recommending action

External source weighting:

- FantasyPros Dynasty ECR: expert/consensus context
- FantasyPros redraft/PPR: short-term win-now context
- KeepTradeCut: crowd and market sentiment
- FantasyCalc: trade-database and market plausibility context
- ESPN/player profiles: player, news and team context where current and relevant
- official NFL/team sources: roster, injury, transaction and role plausibility context
- reputable beat/team coverage: depth-chart, usage and camp-role plausibility context

External sources supplement internal league data. They do not override it automatically.

## 14. Cross-source plausibility rule

Every AI player, trade, roster, draft or free-agent recommendation must reconcile internal league data and external context when both are relevant.

When starting from internal league data, check externally for current NFL team and roster status, injury status and return timeline, role/depth chart/competition, current expert or market ranking when value matters, and recent news that could make historical production misleading.

When starting from an external source, check internally for fantasy-league ownership via `League.json -> Teams[].Roster`, `Reserve` and `Taxi`, Mighty Giants roster fit and team window, league scoring and roster-size effects, salary/projected salary/cap-deadline effects, current picks, trade liquidity and replacement level.

If internal and external sources conflict:

- do not silently pick the more convenient source
- identify the conflict
- explain which source is more decision-relevant and why
- lower confidence when the conflict cannot be resolved

## 15. Stoned Lack rules

Stoned Lack is a source perspective, not a final projection.

Use Stoned Lack for:

- rookie upside
- prospect profiles
- sleepers
- fades
- buy/sell/watchlist takes
- role-path arguments
- source conviction
- source philosophy

Always label Stoned Lack as a source perspective, for example:

- "Stoned Lack sees ..."
- "the Stoned Lack extraction says ..."
- "according to the Stoned Lack source note ..."

Do not present Stoned Lack as current live news or as the final Mighty Giants recommendation.

Legacy spellings `StoneLack`, `StonedLack` and `Stoned-Lack` may appear in older transcripts, commits or user references. Resolve them to canonical `Stoned Lack` unless preserving raw transcript wording.

## 16. Transcript extraction rules

When processing Stoned Lack or other fantasy football transcripts:

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

## 17. Transparency in user-facing responses

### Player naming in user-facing communication

When naming players in trade messages, negotiation drafts, recommendations or other user-facing Fantasy Management communication:

- prefer the player's surname when it is reasonably unambiguous in the current context;
- use the player's full name when the surname is common, ambiguous or could reasonably refer to multiple relevant players;
- do not refer to a player by first name alone unless preserving a direct quote or intentionally mirroring wording already used by the user or another manager.

For example, `Mahomes` is normally sufficient, while `Antonio Williams` should be written in full rather than only `Antonio` or an ambiguous `Williams`.

When giving player, trade or roster recommendations, separate where useful:

### Internal league data says

- production
- game history
- roster role
- position
- age
- salary as cap factor
- league-format fit
- gaps, concrete content conflicts or unclear fields

### External sources say

- market context
- expert context
- rankings, values or trends with source and freshness
- current team, depth-chart, injury or news context

### Plausibility / reconciliation

- what internal data and external context agree on
- what conflicts
- which source is more decision-relevant for the recommendation
- confidence level when uncertainty remains

### Stoned Lack / source input says

- source takes
- rankings or tiers
- sentiment
- conviction
- strategy notes

### My Mighty Giants recommendation

- hold / shop / package / cut / stash
- why this is appropriate for TeamID 1 and this league format

When data is missing, say so plainly.

## 18. Trade and roster logic

For a strong Mighty Giants team:

- evaluate consolidation trades
- treat picks as liquidity, not only draft ammunition
- consider using 2026 picks for win-now upgrades when the price and player fit are right
- do not burn future picks casually
- keep bench depth only when it is format-relevant, young/upside-heavy or strong injury insurance
- identify roster cloggers early

## 19. Position logic

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

For Free-Agent Draft picks, also apply the Free-Agent Draft pick opportunity-cost guardrail above; displayed round/slot alone is not sufficient valuation evidence.

## 20. Common mistakes to avoid

Do not:

- use off-season starter lists as quality rankings
- use `Grading` as player quality, player rank, upside, draft value, free-agent priority, trade value or cut evidence
- infer rankings from `Grading`, salary, starter order, roster order or player name
- treat salary as talent or quality
- ignore salary when off-season cap deadline or cap compliance is decision-relevant
- name external rankings without live checking when current values matter
- use internal league data for player role assumptions without external plausibility checks when role matters
- use external rankings or news without checking league ownership, scoring, roster size, salary/cap and Mighty Giants fit
- treat generic Superflex/2QB overall rankings as direct league-specific boards without adjusting for actual 6-team replacement level and Mighty Giants marginal gain
- value a Free-Agent Draft pick as if it were a same-numbered Rookie Draft pick or generic pick asset without deriving its actual league-specific free-agent shelf
- freeze a Free-Agent Draft board at the pre-draft player pool; players cut before or during the draft become draft-eligible and can change the board for later selections
- cut a superior keep/trade asset merely to seed the Free-Agent Draft with a decoy; strategic pre-draft cuts are valid only when the cut is already justified by roster value and opportunity cost
- project a breakout or young player's historical production forward without checking whether the opportunity was earned against normal competition or created by injuries, suspensions, roster turnover or temporary vacancies
- cut a rookie near the roster boundary without explicitly checking NFL draft round/overall pick and whether the prospect thesis has actually failed or is merely unresolved
- treat the players currently occupying Taxi slots as automatically protected from cut analysis; Taxi-eligible rookies must be ranked as one shared prospect pool before Taxi slots are assigned
- invent ADP, rankings, market values or injury news
- treat Stoned Lack takes as final recommendations
- infer players from bad transcript names without verification
- use `IsFreeAgent` as fantasy-league availability
- read draft-pick keys as true pick position without `Drafts.json`
- confuse `OriginalOwnerRosterID` with current pick ownership
- present old chat values as current data
- infer stale league data from timestamps, commit age or an unchanged generation date alone
- ignore league format
- ignore 6-team replacement level
- evaluate players by name only
- overvalue prospects just because salary is low
- undervalue veterans automatically when they help a contender window
- treat Sleeper depth-chart order as direct proof of expected fantasy opportunity or usage
- collapse `SleeperDepthChartPosition` and `SleeperDepthChartOrder` into one meaning for wide receivers

## 21. Standard single-player analysis structure

Use this structure when helpful:

1. short verdict
2. role for Mighty Giants
3. internal data
4. format fit: 2QB / 2TE / 4Flex
5. salary/cap relevance
6. external market/ranking/news context
7. plausibility check: internal vs external agreement/conflict
8. Stoned Lack/source input if relevant
9. risks
10. recommendation label

## 22. Standard team-analysis structure

Use this structure when helpful:

1. data state and sources
2. league format
3. roster by position
4. player role categories
5. cap/salary situation
6. picks and trade liquidity
7. team window
8. external context that changes player/team assumptions
9. plausibility check and unresolved conflicts
10. concrete recommendations

## 23. Monitoring-, Positionsmodul- und Weekly-Decision-Grenze

Positionsspezifische Analysebausteine, Daily Monitoring und konkrete wöchentliche Entscheidungen sind dauerhaft getrennte Ebenen.

### Daily Monitoring

Daily Monitoring soll materielle Veränderungen erkennen, Research priorisieren und benennen, welche spätere Entscheidung neu geprüft werden muss.

Daily Monitoring darf insbesondere:

- Injury-, Role-, Usage-, Market-, ADP-, Projection-, Activity-, Team- und Ownership-Veränderungen beobachten;
- positionsspezifische Signale verwenden;
- bei konkretem Trigger frische qualitative Verifikation auslösen;
- eine spätere Roster-, Waiver-, Trade- oder Lineup-Prüfung priorisieren.

Daily Monitoring darf nicht allein aufgrund eines Signals endgültig entscheiden:

- Start/Sit;
- Add/Drop;
- Waiver Claim;
- Roster Cut;
- positionsübergreifende Opportunity Cost.

Ein Monitoring-Event bedeutet deshalb grundsätzlich: **neu bewerten**, nicht automatisch: **Transaktion ausführen**.

### Positionsspezifische Module

Ein positionsspezifisches Modul darf eigene Kandidaten-, Scoring-, Eligibility- und Research-Logik besitzen, muss aber seine Grenze zum Gesamtroster wahren.

Kicker ist der aktuelle Referenzfall:

- Kicker Daily Monitoring beobachtet Baseline, FFC-Kicker-ADP, FFToday/CBS-Projections, Sleeper Activity, Injury, nominalen K1-Status und bei Trigger aktuelle Job Security.
- Die Kicker-Streaming-Engine bewertet im Weekly Context den gehaltenen Kicker gegen tatsächliche Fantasy-Free-Agent-Kicker.
- Ohne Weekly Context darf keine Wechsel-Empfehlung aus Daily-/Preseason-Signalen erzeugt werden.
- Ein guter stabiler Kicker wird nicht automatisch jede Woche gegen einen minimal höher bewerteten Streamer getauscht; ein Wechsel benötigt einen materiellen Vorteil oder einen expliziten Sonderfall wie Bye, Jobverlust oder disqualifizierende Verletzung.

### Weekly Lineup + Waiver

Die endgültige wöchentliche Start/Sit- und Waiver-Entscheidung gehört in einen übergeordneten Workflow, der alle Positionen und den vollständigen Rosterpreis gemeinsam bewertet.

Er muss insbesondere berücksichtigen:

- beste legale Startaufstellung;
- tatsächliche Fantasy-Free-Agent-Verfügbarkeit;
- Bye und Injury/Availability;
- Weekly Matchup und Opportunity;
- positionsspezifische Module;
- den Spieler, der für einen Add gedroppt werden müsste;
- Bench-Slot-, Upside-, Scarcity-, Injury-Insurance- und Trade-Value-Opportunity-Cost.

Für Kicker gilt als Default genau ein gehaltener Kicker. Zwei Kicker sind nur dann vertretbar, wenn der übergeordnete Weekly Workflow ausdrücklich feststellt, dass das Behalten eines längerfristig wertvollen Kickers die Opportunity Cost des zusätzlich belegten Bench-Slots übersteigt, zum Beispiel zur Bye-Überbrückung.

Die Kicker-Engine darf diese Zwei-Kicker-/Drop-Entscheidung nicht allein treffen, weil sie den Wert des zu opfernden Nicht-Kickers nicht kennt.

Kanonische Detaildokumentation:

`fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md`