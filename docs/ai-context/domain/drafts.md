# AI Context: Draft Domain

Status: Manual Context
Audience: AI assistants and maintainers
Scope: Drafts, draft picks, ownership, and draft-pick display rules

## Purpose

This document describes the domain model and current decisions for drafts and draft picks.

Drafts are not only display data. They are part of the league model because draft picks can be owned, traded, displayed, and eventually resolved into selected players.

## Core Concepts

### Draft

A draft represents one draft event for a season.

Important draft-level concepts include:

- stable draft key,
- season,
- draft type,
- display labels,
- draft order number,
- source information,
- settings such as rounds and teams,
- picks belonging to the draft.

### Draft Pick

A draft pick represents one selectable asset inside a draft.

Important pick-level concepts include:

- stable pick key,
- draft key,
- season,
- round,
- position in round,
- overall pick,
- display pick text,
- original owner roster ID,
- current owner roster ID,
- trade state,
- trade history,
- selected player information when available.

## Ownership Rules

`OriginalOwnerRosterID` describes the team that originally owned the pick.

`CurrentOwnerRosterID` describes the team that currently owns the pick after transactions and manual corrections have been applied.

The original owner should not change because it is historical source information.

The current owner may change when a draft pick is traded.

A pick can be displayed for the current owner even when the original owner is different.

## Trade Rules

Draft-pick trades are represented through transaction history.

A traded pick should preserve enough information to answer:

- who originally owned the pick,
- who currently owns the pick,
- whether the pick was traded,
- which transaction changed ownership,
- when the ownership change happened,
- whether the change came from Sleeper data or manual data.

Manual corrections may be needed when external API data is incomplete or does not model league-specific rules correctly.

## Display Rules

Draft picks should have a stable display string, such as a round/pick label or another generated display representation.

Angular components may group picks by draft for display.

In Overview, current-season draft picks are currently grouped per team and then per draft.

The Overview display currently creates local chip view models with:

- display text,
- round,
- background color.

## Round Chip Color Rules

Round chip colors should visually distinguish draft rounds while remaining subtle enough for black text.

The current Overview implementation uses a global maximum round across all current-season picks visible in the Overview.

This means:

- all round 1 picks use the same color,
- all round 2 picks use the same color,
- same-round picks keep the same color across different drafts,
- colors are not recalculated relative to each individual draft.

The color scale runs from warm to cold using a light HSL range.

Current local rule:

```text
roundRatio = (round - 1) / (maxDisplayedRound - 1)
color      = hsl(interpolatedHueFromWarmToCold, 55%, 84%)
```

This logic is currently local to Overview. It should later be moved into a shared frontend utility, pipe, or service so all components render draft-round chips consistently.

## Data Ownership

PowerShell generation logic should own the normalized draft and draft-pick domain structure.

Angular should not infer ownership by parsing display strings.

Angular may prepare display groupings and chip view models, but the source ownership information should already be present in generated data.

## Important Decisions

- Drafts are first-class generated app data.
- Draft picks are assets that can change current ownership.
- Original ownership and current ownership must remain separate.
- Draft-pick display should use normalized fields, not string parsing.
- Round chip colors must be based on a global visible max round, not per-draft max round.
- Overview owns the round-color logic only temporarily.

## Notes for AI Agents

Do not collapse original owner and current owner into a single field.

Do not assume that all drafts have the same number of rounds.

Do not calculate chip colors relative to one draft if multiple drafts are visible together.

When adding new draft displays, prefer a shared round chip color helper once it exists.

When changing pick ownership logic, also review transaction documentation because draft-pick ownership is transaction-dependent.
