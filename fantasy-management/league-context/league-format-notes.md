# League Format Notes

Purpose: stable interpretation notes for the league format.

Canonical current settings come from current repository data, especially:

- `public/data/League.json`
- `public/data/Metadata.json`

Re-check current data before dynamic roster, salary, pick, standings or trade conclusions.

## Dynamic structure derivation

Do not store current starter, FLEX, bench, Taxi, Reserve or total roster-capacity counts here as durable truth.

For every analysis where format or roster capacity matters, derive the current structure from `public/data/League.json`:

- league size from `TotalTeams`;
- fixed starter counts, FLEX structure, bench count and regular active-roster capacity from `RosterSize`;
- Taxi capacity and eligibility from the current Taxi settings under `Settings`;
- Reserve capacity and eligibility from the current Reserve settings under `Settings` plus the player's current designation;
- scoring from `ScoringType`.

When `Teams[].Roster` also contains players listed in `Taxi` or `Reserve`, do not count those players again as regular active occupants. Report roster-limit conclusions from the current derived capacity and occupied counts rather than carrying forward an older number.

## Interpretation rules

- QB value rises when the current format contains multiple fixed QB starter spots and the actual free-agent replacement pool is thin enough to create scarcity.
- TE value rises when the current format contains multiple fixed TE starter spots and the actual replacement pool is thin enough to create scarcity.
- RB and WR depth value depends on the current fixed starter and FLEX structure.
- Replacement level must reflect the current league size and actual rostered/free-agent population.
- In a shallow league, quality and weekly ceiling matter more than mere rosterability.
- Depth still matters when the dynamically derived number of weekly starter and FLEX slots is large.
- Kickers are usually replaceable unless current data shows a special reason.

## Player value question

For this league, ask:

Can this player regularly provide meaningful weekly contribution in the current dynamically derived format, serve as scarce-position backup, or be used as a trade asset for an upgrade?

## Trade context

In trade analysis, combine format notes with:

- current roster construction
- current picks
- salary and projected salary
- contender / rebuild window
- counterparty roster needs
- owner profile and negotiation history
