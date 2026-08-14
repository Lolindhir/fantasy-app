# Trade Negotiation Rules

Purpose: define how Fantasy Management should use direct manager communication, negotiation history and counterparty-specific communication style when preparing, conducting and reviewing trade talks.

This file is canonical for trade negotiation behavior. Use it together with `FANTASY_MANAGEMENT_RULES.md`, current league data and the league-context files. It does not replace current player, roster, pick, salary or market analysis.

## 1. Scope

Read and apply these rules whenever the task involves:

- preparing a trade approach or opening message;
- choosing which counterparty to contact;
- constructing or presenting an offer;
- responding to a counteroffer;
- deciding whether and how to follow up;
- interpreting a rejection, delay, price anchor or stated preference;
- comparing likely negotiation paths across managers;
- updating owner tendencies or trade-negotiation history.

## 2. Direct manager communication is a distinct evidence class

Direct communication from a league manager is first-party negotiation evidence.

Examples include:

- explicit statements about whether an asset is available or protected;
- requested prices and counteroffers;
- reasons given for accepting or rejecting an offer;
- stated roster-building philosophy, timeline or positional preference;
- stated preference for or aversion to particular asset types;
- explicit feedback about message length, detail, pressure, cadence or negotiation style;
- repeated behavior across completed and failed negotiations.

Treat this evidence separately from:

- current league state from `public/data/`;
- current player quality, role, injury and market evidence;
- draft and roster-construction tendencies;
- external rankings, projections, ADP and market values.

A manager's historical statement about a player or asset documents that manager's belief at that time. It is not current player truth and must not replace fresh player or market analysis.

## 3. Negotiation evidence strength and recency

Use the following hierarchy when estimating how a manager is likely to negotiate:

1. explicit statements or behavior in the current active negotiation;
2. repeated behavior across several independent prior negotiations;
3. a direct historical statement that is highly diagnostic of communication or process preference;
4. a repeated owner-profile tendency derived from roster, draft and trade behavior;
5. a single historical trade or weak inferred tendency.

Do not let an old tendency override a manager's current explicit position.

Distinguish between:

- **stable process preference**: for example preferred communication density, willingness to research before answering, or repeated use of counters;
- **context-dependent valuation**: for example liking picks in one draft class but not another;
- **asset-specific conviction**: a player or pick may be unusually protected without proving a general manager tendency;
- **temporary team-state preference**: contender/rebuild status, cap pressure, roster uncertainty and draft timing can change negotiation behavior.

Lower confidence when evidence is sparse, contradictory or old.

## 4. Required counterparty context before trade outreach

Before recommending or drafting a trade outreach, load as relevant:

1. `fantasy-management/league-context/owner-registry.json`;
2. `fantasy-management/league-context/owner-profiles.md`;
3. `fantasy-management/league-context/trade-negotiation-history.md`;
4. current `League.json`, `Drafts.json`, `Transactions.json` and player data required for the actual assets;
5. current external market, role, injury or news context when value depends on it.

Do not draft from negotiation history alone. A historically attractive construction can be obsolete because rosters, picks, salaries, player values, team windows and manager priorities change.

## 5. Counterparty-specific communication calibration is mandatory

Before producing a trade message, explicitly calibrate the communication strategy to the best available evidence about that manager.

Consider at minimum:

- **message length and detail:** short/direct versus analytical deep dive;
- **number of simultaneous ideas:** one clear offer versus several alternative constructions;
- **argument type:** roster fit, salary/cap relief, immediate production, youth/upside, draft capital, liquidity, positional scarcity or personal conviction;
- **anchoring style:** ask for a price, lead with a concrete offer, or present a range only when evidence supports it;
- **pace and follow-up:** whether friendly reminders are useful, neutral or likely to create friction;
- **decision friction:** whether the manager benefits from a simplified choice or enjoys jointly solving a complex package;
- **timing:** whether uncertainty around cuts, draft order, injuries, roster deadlines or other decisions makes immediate negotiation inefficient.

The same underlying trade can therefore require different outreach wording for different managers.

Do not optimize only for theoretical trade value. Optimize the presentation for the counterparty without changing the underlying Mighty Giants price ceiling or inventing false claims.

If there is insufficient communication evidence, default to a concise, friendly and low-pressure message with one clear idea and room for a counter. Do not invent a personality profile.

## 6. Preserve Robert's negotiation objectives separately from presentation

Communication calibration must not silently change the actual trade recommendation.

Before outreach, separate:

- Robert's preferred target;
- acceptable substitutes;
- neutral market estimate;
- Mighty Giants-specific value;
- opening offer;
- intended concessions;
- hard price ceiling;
- walk-away conditions.

A more detailed or more concise message is presentation strategy, not permission to exceed the price ceiling.

When several reasonably substitutable targets exist, preserve an internal preference order and individual ceiling for each target before signaling that one player is a must-have.

## 7. Use direct communication to learn, not merely to persuade

A trade conversation is also an information-gathering process.

Use responses to update:

- actual availability;
- which asset types the manager wants;
- which assets are protected;
- current price anchors;
- whether the manager values quantity, consolidation or specific roster functions;
- whether a stated objection is about value, timing, uncertainty or the specific asset;
- whether alternative targets are more movable.

Do not interpret silence or a delayed response as rejection unless current or historical evidence supports that inference.

When a manager gives a clear categorical refusal, do not keep arguing the same construction. Revisit only when the context materially changes or the manager reopens the topic.

## 8. Negotiation integrity

Strategic presentation is allowed; fabricated information is not.

Do not:

- invent competing offers;
- claim false market values, injuries, deadlines or roster facts;
- create fake urgency;
- misrepresent what another manager said;
- conceal a material factual correction after discovering it.

It is acceptable to choose which truthful arguments to emphasize, how much analysis to disclose, when to ask for a price and when to preserve optionality among several targets.

## 9. Persistence rules

Durable negotiation context belongs in:

- `fantasy-management/league-context/owner-profiles.md` for reusable manager tendencies and communication preferences;
- `fantasy-management/league-context/trade-negotiation-history.md` for concrete chronological offer paths, counters, refusals, reasons and outcomes.

Persist successful and failed negotiations when they reveal useful price or process information.

Promote a tendency to an owner profile only when the evidence level is appropriate. Keep one-off or highly asset-specific observations in negotiation history when they do not justify a general tendency.

Directly supplied private chat exports are source material for extraction, not repository artifacts by default. Do not commit full private chat logs unless Robert explicitly requests it. Persist only the Fantasy-relevant distilled context necessary for future management decisions.

Do not reconstruct excluded media, deleted messages or unavailable context.

## 10. Required trade-outreach workflow

For a concrete trade approach:

1. resolve the counterparty and current team state;
2. resolve the exact target assets and Robert's assets;
3. load owner profile and negotiation history;
4. re-check current roster, picks, cap/salary and relevant player/market context;
5. determine target preference order, opening offer, concessions, ceiling and walk-away conditions;
6. identify the counterparty's best-supported current motivations and likely objections;
7. choose the communication format using the calibration rule in this file;
8. draft or recommend the outreach without fabricating leverage;
9. after a reply, update the negotiation model from what the manager actually said instead of forcing the old profile onto the new evidence;
10. after the negotiation is materially complete, persist reusable new evidence at the proper confidence level when requested or when maintaining the league context is part of the task.

Core question before sending any trade message:

**Is this both a good Mighty Giants trade path and the right way to present that path to this specific manager?**
