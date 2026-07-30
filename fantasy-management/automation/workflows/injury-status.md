# Injury Status Observation Workflow

Purpose: normalize and monitor player injury, availability, reserve and return-timeline changes for the `injury-status` observation profile.

## Inputs

- current player record resolved through the configured player-chunk index;
- current `public/data/Timestamps.json`;
- official NFL/team transactions and injury reports when a candidate change or unresolved status requires verification;
- established beat reporting only as supporting evidence for timelines not available from authoritative sources.

## Two-stage evaluation

1. Compare the current player-data fingerprint and normalized status fields with the previous good profile state.
2. Reuse current repo data as a scalable first-pass change detector.
3. Fetch authoritative external evidence when:
   - no baseline exists and the player is not clearly healthy/active in fresh current data;
   - injury designation, roster status, NFL team or transaction state changed;
   - a player becomes limited, questionable, doubtful, out, suspended, exempt, IR, PUP or NFI;
   - a return timeline is introduced or changed;
   - current sources conflict.
4. A fresh current player record may support an `available` baseline with medium confidence when it is internally consistent and no contrary current signal exists.
5. A material negative or positive availability change requires an official team/league source or a clearly attributable injury report.
6. Keep the last good material state when required evidence is missing.

## Normalization

Normalize evidence into:

- `availability_class`;
- `designation`;
- `reserve_status`;
- `practice_status`;
- `return_timeline`;
- `injury_summary`;
- `confidence`.

Use these availability classes:

```text
available
limited
game_time_decision
unavailable_short_term
unavailable_long_term
suspended_or_exempt
unknown
```

Use these reserve statuses:

```text
active
injured_reserve
physically_unable_to_perform
non_football_injury
suspended
exempt
unknown
```

Do not put fetch timestamps, URLs or prose-only restatements into the material-state hash.

## Materiality

- A confirmed `availability_class` change is material.
- A confirmed reserve-status change is material.
- A decision-relevant return-timeline change is material.
- Practice participation alone is not material unless it creates a supported game-time-decision state.
- A changed body-part label without changed availability or timeline is not material.
- Repeated unchanged designations, speculative social posts and coach optimism without status evidence are not material.

## Decision effect

For `managed_team`, translate a material change into the affected roster function:

- lineup availability;
- IR/reserve planning;
- replacement or handcuff need;
- Hold, Shop, Cut, Stash or Package relevance;
- urgency and confidence.

The event must still follow the atomic-publication workflow and notification threshold.
