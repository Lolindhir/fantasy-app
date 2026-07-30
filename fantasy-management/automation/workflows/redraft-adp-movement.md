# Redraft ADP Movement Workflow

Purpose: evaluate short-term observed draft-cost movement for managed-roster players without treating ADP as dynasty value, projection or league-specific truth.

## Inputs

- `fantasy-management/automation/profiles/redraft-adp-movement.json`
- current resolved player identity and position
- Fantasy Football Calculator PPR 8-team latest pointer and normalized ranking
- Fantasy Football Calculator 2-QB 10-team latest pointer and normalized ranking
- `fantasy-management/sources/external-rankings/adp/fantasy-football-calculator/analysis-metadata.json`
- previous good profile state

## 1. Resolve sources once per run

1. Resolve both configured `latest.json` pointers through `source-binding-resolution.md`.
2. Load each ranking table and metadata only once per runner invocation.
3. Prefer same-day snapshots; accept the configured freshness window only when both pointers remain valid.
4. Do not substitute another provider or silently use web ADP when a required binding fails.
5. Preserve the previous good state when a required source, metadata file or player join is not reliable.

## 2. Resolve the player

1. Prefer a confirmed `source_player_id` mapping.
2. Fall back to normalized name plus position.
3. Use current NFL team only as a plausibility check, not as the primary identity.
4. Treat a missing row as `listed = false`; do not invent ADP, rank, draft count or uncertainty values.
5. A missing row alone is not material and must not create a notification.

## 3. Select the primary format

Use exactly one format for materiality:

- `QB` → `two_qb_10_team`
- `RB`, `WR`, `TE` → `ppr_8_team`

The other feed is supporting format context only.

Do not average raw PPR and 2-QB ADP. The league has six teams, two fixed quarterbacks and two fixed tight ends, while neither source format matches all of those settings. Tight-end scarcity must therefore be applied later in decision interpretation, not encoded by changing the observed ADP.

## 4. Normalize ranks

For a listed player in a ranking of length `N` with normalized offensive-player rank `Rank`, calculate:

```text
percentile = 100 * (N - Rank) / (N - 1)
```

Rules:

- clamp the result to `0..100`;
- higher means earlier and more expensive;
- use normalized `Rank`, never `source_rank`;
- do not compare raw ranks across lists of different length;
- retain raw `adp`, `times_drafted` and `stdev` for display and confidence only;
- derive `format_gap = two_qb_percentile - ppr_percentile` when both rows exist.

## 5. Build confidence

The primary row must have at least 50 observed player drafts for a material criterion.

Set confidence using all of:

- latest-pointer and ranking freshness;
- confirmed versus fallback identity join;
- primary player sample size;
- source-wide sample quality;
- reported player-level spread;
- whether the current position is represented by the chosen primary format.

Guidance:

- fewer than 10 player drafts → `low`;
- 10–49 player drafts → at most `low`;
- at least 50 player drafts with a plausible join and fresh source → at least `medium`;
- `high` additionally requires strong sample quality and a confirmed identity join.

## 6. Materiality

A first successful state is a silent baseline.

After baseline:

- at least 10 primary percentile points of cumulative movement against the previous material state → `medium`;
- at least 20 primary percentile points → `high`;
- a new primary-feed entry with at least 50 player drafts → `medium`;
- small raw-ADP movement, sample-count changes, uncertainty changes, format-gap movement and list exit alone are not material.

When the 10- and 20-point criteria both match, publish one event at the highest justified severity.

## 7. Interpretation

For a material event:

1. state direction and size of the primary-percentile change;
2. include raw ADP, player draft count and uncertainty as context;
3. compare with role, injury and dynasty-market states when available;
4. distinguish role-confirmed movement from unsupported market noise;
5. explain that ADP measures current-season acquisition cost, not expected points or long-term trade value;
6. translate the signal into the managed team's shallow 2-QB / 2-TE / 4-FLEX context.

## 8. State and notification

Store only normalized output fields and source fingerprints required by the generic observation workflow.

- no material change → no event, no commit, no notification;
- new baseline → state update allowed, no event and no notification;
- material change → publish state, JSON event and Markdown event atomically;
- notify only after successful atomic publication and only when job severity rules permit it.
