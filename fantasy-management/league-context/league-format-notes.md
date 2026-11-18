# League Format Notes

Purpose: stable interpretation notes for the league format.

Canonical current settings come from current repository data, especially:

- `public/data/League.json`
- `data-meta/nfl-reise/metadata.json`

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
- the final **additions to Taxi** must be made before the league's applicable Taxi deadline; after that deadline, players cannot be moved into or back onto Taxi;
- **promotion out of Taxi remains possible during the season**, including after the Taxi deadline, subject to current Sleeper/league roster limits and the relevant player's game/lineup lock; the lock prevents putting someone back onto Taxi, not moving a Taxi occupant onto the active roster;
- after the deadline, the Taxi slots are no longer freely swappable: promoting a player does not create permission to stash a different rookie or return the promoted player to Taxi;
- when the active roster is full, a promotion requires a legal capacity-clearing move (for example a drop). Assess that move's player/asset opportunity cost rather than treating promotion as a free weekly roster slot;
- analyses must respect the actual Taxi occupants and the historical decision time; do not assume preseason-style reshuffling or retroactive activation after an NFL kickoff.

Taxi is a separate rookie-development budget and does not replace general active churn/streaming capacity.

See Sleeper's [official Taxi Squad mechanics](https://support.sleeper.com/en/articles/3640482-how-do-taxi-squads-work) for the distinction between promotions out of Taxi and the deadline for moves back into Taxi.

## Historical Best Ball versus executable lineup moves

- **Retrospective Best Ball / potential points** is an ex-post theoretical ceiling over all players controlled by the team in the historical week, including regular active roster, Taxi and Reserve/IR, with each player counted once and the league's lineup-slot constraints applied. Do not exclude a player solely for being stored on Taxi or Reserve/IR; players who did not score still contribute only their actual points (normally zero).
- **Executable ex-ante lineup decisions** are a separate question. To start a Taxi or Reserve/IR player, the manager would first need to activate the player, satisfy active-roster capacity and other league restrictions (possibly through a legal drop), and complete the lineup change before that player's individual game lock. A Sunday activation cannot capture points already scored on Thursday.
- **Management opportunity cost** is yet another dimension: quantify the player/asset sacrificed, the lost ability to return a player to Taxi after the deadline, the availability of other legal moves and any transaction timing constraints. The theoretical Best-Ball number does not assume those sacrifices were desirable at the time.
- Keep historical ownership/transaction evidence separate from today's roster sections, and distinguish theoretical potential, feasible activation path and same-information decision quality. The postmortem's Best Ball is a diagnostic calculation, not a claim that Sleeper automatic Best Ball scoring is enabled in this league.

See Sleeper's [IR/Reserve mechanics](https://support.sleeper.com/en/articles/1983643-how-does-injured-reserve-ir-work) for capacity and activation requirements.

## Interpretation rules

- QB value rises when the current format contains multiple fixed QB starter spots and the actual free-agent replacement pool is thin enough to create scarcity.
- TE value rises when the current format contains multiple fixed TE starter spots and the actual replacement pool is thin enough to create scarcity.
- RB and WR depth value depends on the current fixed starter and FLEX structure.
- Replacement level must reflect the current league size and actual rostered/free-agent population.
- In a shallow league, quality and weekly ceiling matter more than mere rosterability.
- Depth still matters when the dynamically derived number of weekly starter and FLEX slots is large.
- Kickers are usually replaceable unless current data shows a special reason.
- For additional quarterbacks beyond the normally preferred starting rotation, value plausible actual starts during remaining bye/injury windows and backup insurance separately from long-term development and verified trade liquidity; a dynasty ranking alone does not justify a permanent active slot.
- When the primary QB group is temporarily weakened by injury/IR, extra QB coverage may be warranted, but re-evaluate it after health, bye or roster-role changes; do not count an injured reserve asset as an immediately playable starter or apply an automatic QB4/QB5 cut rule.

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
