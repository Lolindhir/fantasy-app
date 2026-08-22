# Managed Roster Selector Workflow

Purpose: resolve the complete current player roster of `managed_team` as dynamic observation targets without hard-coding player names or the current franchise display name.

## Configuration contract

The selector type is:

```text
managed_team_roster_players
```

Required parameters:

- `team_ref`: must be `managed_team`;
- `membership_fields`: ordered list of team fields to union, initially `Roster`, `Reserve` and `Taxi`;
- `player_source_path`: current FM-owned player-signal contract used to resolve player records;
- `stable_identifier`: must be `sleeper_id`;
- `target_id_template`: stable target ID template using `{sleeper_id}`;
- `deduplicate_player_ids`: whether duplicate membership entries are collapsed;
- `retain_state_when_unselected`: whether historical state is retained when a player leaves the selector result.

## Resolution

1. Resolve `managed_team` from `runner-config.json` against current `public/data/League.json`.
2. Read every configured membership field from that team.
3. Treat `null` or a missing optional membership field as an empty list.
4. Union all player IDs and deduplicate them before creating targets.
5. Load `player_source_path` once and resolve selected Sleeper IDs through `players[].player_id`.
6. Fail closed when a selected ID cannot be resolved to exactly one current player-signal record.
7. Build each entity with:
   - `type: player`;
   - current display name;
   - `identifiers.sleeper_id`;
   - current NFL team and position as non-identity attributes when available.
8. Build the target ID from `target_id_template`.
9. Use `player:sleeper_id:{id}` as the entity fingerprint.
10. Apply selector profile bindings and decision-context template.
11. Never write the resolved player list back into the target-set configuration.

## State lifecycle

- A newly selected player receives a silent baseline for every enabled profile.
- A player present in more than one membership field remains one target.
- A player that leaves this selector but remains selected by another target set stays active with the remaining target-set IDs.
- A player that is no longer selected by any target set is marked `expired`; the last good profile states are retained when `retain_state_when_unselected` is true.
- If an expired player is selected again with the same entity fingerprint, reactivate the target and compare against the retained last good material state.
- Selector-resolution changes may update operational state but do not by themselves create an observation event or notification.

## Efficient evidence collection

The complete roster must not cause repeated identical fetches.

- Load each repository file or ranking snapshot once per run.
- Reuse one authoritative team source for every relevant player it supports.
- Group player-specific role research by NFL team and position group.
- Use current repo/player fingerprints as the first change detector.
- Perform deeper player-specific external research for a missing baseline, changed source/input fingerprint, changed status/transaction signal, or another profile-specific reason.
- A material event still must satisfy the full profile source policy; prefiltering must never lower evidence requirements.

## Current scope

The selector monitors the union of `Roster`, `Reserve` and `Taxi`. It does not use offseason `Starter` membership as a quality or role signal.
