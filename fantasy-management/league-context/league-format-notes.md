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

## Taxi timing and lock mechanic

League-specific Taxi mechanic confirmed by the user:

- before the first league game, all current rookies are eligible to be moved between the regular roster/bench and Taxi;
- therefore the current pre-season placement of a rookie on Taxi or bench is provisional and must not be treated as protection, commitment or a quality signal;
- before the Taxi lock, roster and cut analysis must evaluate all current rookies together and may virtually allocate the available Taxi slots to the two most sensible development stashes;
- the final Taxi decision must be made before the first league game;
- once the first league game begins, the two Taxi slots are locked and are no longer freely swappable for the remainder of the season;
- after the lock, analyses must treat the actual Taxi occupants as a real roster constraint and must not assume pre-season flexibility continues.

Taxi is a separate rookie-development budget and does not replace general active churn/streaming capacity.

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
