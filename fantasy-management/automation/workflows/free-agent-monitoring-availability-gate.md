# Free-Agent Monitoring Availability Gate

Purpose: keep broad Free-Agent Movement discovery intact while preventing stale ownership-only state from being presented as current actionable Free-Agent availability.

## Inputs

- `fantasy-management/generated/operations/free-agent-movement-events.json`
- `fantasy-management/generated/operations/free-agent-movement-signals.json`
- `fantasy-management/generated/operations/fa-board-readmodel.json`
- `fantasy-management/generated/operations/source-freshness.json`

## Boundary

`free-agent-signals.json`, Movement State and Movement Events remain the broad ownership-derived discovery layer. Do not filter or rewrite those deterministic contracts merely because a player is no longer actionable in the current FA context.

Before a Movement event is escalated or notified as a **currently available Free-Agent opportunity**, resolve the same `player_id` in the current schema-valid `fa-board-readmodel.json`.

Only `availability_status = available` permits an availability-based Free-Agent escalation.

Treat all other statuses fail-closed for that claim:

- `drafted`: suppress the available-FA escalation because the player is already assigned in the current FA Draft even when League ownership has not materialized yet.
- `rostered`: suppress the available-FA escalation. If the ownership change itself is materially relevant, it may be interpreted separately as opponent/transaction/market context rather than as an available-FA opportunity.
- `unknown`: suppress every positive availability statement and surface a data-quality/availability uncertainty only when that uncertainty is itself materially relevant.

A missing player row, missing/invalid FA-board contract, unresolved mandatory FA-board inputs or unusable FA-board freshness is equivalent to `unknown` for positive availability claims.

## Event handling

For every `new`, `changed` or `structural_change` Movement event considered for Free-Agent escalation:

1. Preserve the Movement event and its research evidence unchanged.
2. Resolve its `player_id` in `fa-board-readmodel.json`.
3. Verify FA-board quality and mandatory source resolution before relying on a negative ownership/draft conclusion.
4. If `availability_status = available`, normal research/escalation may continue subject to the usual materiality and freshness rules.
5. If `availability_status = drafted`, `rostered` or `unknown`, do not notify or escalate the player as a currently available Free Agent.
6. Do not discard independent non-availability significance. A roster acquisition by an opponent, injury development, market move, role change or trade-relevant signal may still be reported under the appropriate decision class when independently material.
7. `resolved` Movement events are not converted into positive availability claims; handle them under the normal resolution rules.

## Persistent-watch proposals

When Daily Monitoring proposes adding a player to a durable Free-Agent-oriented watch target because the player is an actionable FA opportunity, the same gate applies: only `availability_status = available` supports that rationale.

A player may still deserve a non-FA qualitative watch for role, injury, transaction or opponent context when rostered/drafted; the proposal must state that different rationale explicitly rather than calling the player available.

## No-op and safety rules

- Do not turn `drafted`, `rostered` or `unknown` into a generic user alert by themselves.
- Do not reclassify a Movement event as irrelevant merely because current FA availability is blocked.
- Do not let external rankings, projections, Sleeper Trending or `free-agent-signals.json` override the FA-board gate.
- Scheduled monitoring remains read-only.
- When the FA-board gate blocks only an availability-based path and no other material decision effect remains, stay silent.
