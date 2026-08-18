# 2026 Free-Agent Draft Preboard – Baseline 2026-08-19

Status: dated pre-draft analysis baseline, not permanent player truth.

Purpose: preserve the current Mighty Giants roster-pressure analysis and Free-Agent Draft board so later pre-draft and in-draft reviews can compare against a known starting point without treating dated market, injury or role signals as current forever.

## Scope and source state

Managed team: Mighty Giants, TeamID 1.

Primary current inputs at baseline creation:

- `public/data/League.json` @ blob `00957a261eea27db831ca400e84b1fc3e1e098f5`
- `public/data/Drafts.json` @ blob `91bb49c0913fd8acfeb7c318f49fefc42449a52c`
- `fantasy-management/generated/operations/managed-roster-signals.json` @ blob `3196fc3a57615290dc09a22d0ceebc7480bfad6b`
- FantasyPros Dynasty Superflex PPR snapshot dated 2026-08-18
- FantasyCalc Dynasty Superflex PPR 8-team snapshot dated 2026-08-18

All external ranks, market values, injuries, NFL roles and camp reports are dated evidence only and must be refreshed when decision-relevant.

## League and roster-capacity baseline

Roster capacity is derived dynamically from current `League.json`; no static bench count is authoritative.

At this baseline:

- `RosterSize` contains 30 regular active slots.
- Taxi capacity: 2.
- Reserve capacity exists in settings, but no Mighty Giants player is currently on Reserve.
- Mighty Giants has 33 player IDs in `Roster`.
- Taxi currently contains Kaelon Black and De'Zhaun Stribling; these IDs are subsets of `Roster` and are not counted again as regular active occupants.
- Therefore current regular active occupancy is 31 against a limit of 30: Mighty Giants is one regular active player over the limit.

Chris Bell is no longer on Reserve in the current league snapshot. This is the immediate reason the team is one active player over the limit after the five pre-draft cuts.

## Already executed pre-draft cuts

The following players are no longer on the Mighty Giants roster and were intentionally released before the FA Draft:

1. Joe Mixon
2. J.J. McCarthy
3. Kyle Williams
4. Chimere Dike
5. Troy Franklin

Strategic context: these were roster-justified cuts first. Releasing them before the FA Draft also widens the mixed rookie/veteran draft pool and may absorb selections from other managers, but decoy value must never justify cutting a superior keep/trade asset by itself.

## Current Mighty Giants FA Draft picks

Current `Drafts.json` resolves the open Mighty Giants picks as:

- 1.01 – overall 1
- 2.04 – overall 10
- 4.04 – overall 22
- 5.04 – overall 28

The former Mighty Giants 3.04 is no longer owned by TeamID 1 and must not be treated as a current Mighty Giants selection.

The FA Draft is a single dynamic mixed rookie/veteran pool. Players cut before or during the draft become eligible for later selections. The board must therefore be recalculated after material picks and intervening cuts.

## Locked decision at 1.01

Tetairoa McMillan is the fixed Mighty Giants target at 1.01. This is a user decision, not merely the top name in this dated board. The durable decision is logged separately under `fantasy-management/decisions/2026/draft-decisions.md`.

## Pre-draft candidate board after 1.01

This ordering is Mighty-Giants-specific and intentionally differs from a generic Superflex overall ranking. Additional QB acquisition is excluded by current team strategy; the important comparison is candidate value versus the next roster asset that must be sacrificed.

### Tier A – clear 2.04 accepts if available

1. Javonte Williams – RB
2. Travis Etienne – RB

These are strong enough on the current baseline to justify the expected additional roster cost at 2.04 if still available and if no material negative role/health change occurs.

### Tier B – strong 2.04 decision candidates

3. Parker Washington – WR
4. Jonathon Brooks – RB
5. Terry McLaurin – WR
6. Chuba Hubbard – RB

These require a fresh role/injury check at the actual pick, but currently clear the threshold for serious 2.04 consideration.

### Tier C – conditional 2.04 / strong value-fall candidates

7. Jalen Coker – WR
8. J.K. Dobbins – RB
9. Tyler Allgeier – RB
10. Jordan Mason – RB

These are not automatic additions merely because they remain available. Their value must be compared with the live Mighty Giants cut line and any new players released during the draft.

### Later-round watchlist

- Braelon Allen – RB
- MarShawn Lloyd – RB

At the current baseline they do not justify forcing a 4.04/5.04 pick over an approximately equivalent or better Mighty Giants keep asset. They remain live watchlist options if their role improves, another roster asset deteriorates, or the draft pool changes materially.

## Current incremental roster-sacrifice ladder

This is a provisional analysis ordering, not a durable cut decision:

1. Kaytron Allen – first current compliance candidate.
2. Kaelon Black – next sacrifice only when a materially stronger incoming asset requires the slot; NFL Round 3 / pick 90 capital remains meaningful and his thesis is unresolved rather than failed.
3. Chris Bell / Dylan Sampson – next comparison tier; ordering must be refreshed from current role, health, market and replacement value before action.
4. Pat Bryant / Malachi Fields and above – should not be sacrificed merely to use a late FA Draft pick under the current baseline.

Taxi is flexible. Current Taxi placement does not protect Black or Stribling, and any taxi-eligible rookie must be compared in the shared prospect pool before final Taxi allocation.

## Pick-by-pick operating rule

For every Mighty Giants selection after 1.01, ask:

**Is the best player actually available at this pick materially better for Mighty Giants than the next player we would have to remove from the final 30-active + eligible Taxi/Reserve structure?**

Consequences at this baseline:

- 2.04 is expected to be usable if a Tier A/B player or a new superior cut reaches the pick.
- 4.04 is optional; do not draft merely to consume the pick.
- 5.04 has an even higher keep-cost threshold and should normally be traded, passed or left unused if the league mechanics allow and no superior value falls.
- Late picks can be more valuable as liquidity than as forced roster additions.

## Mandatory rechecks

Rebuild or review this baseline when any of the following occurs:

- Mighty Giants or an opponent makes another cut that changes the draft pool.
- A FA Draft selection is made before a later Mighty Giants pick.
- a target or cut-line player has a material injury, role, depth-chart or NFL roster change.
- FantasyPros/FantasyCalc or other relevant market signals move materially.
- Bell or another player gains/loses usable Reserve eligibility.
- Taxi eligibility/settings change.
- Mighty Giants trades a pick or roster player.

## Validity note

This file is intentionally immutable as the 2026-08-19 baseline. Do not overwrite it with later conclusions. Create a new dated review or in-draft update that links back to this file. Current availability, ranks, values and player roles must be re-derived rather than copied forward.