# Season Projection Movement Workflow

Purpose: observe material changes in expected regular-season production for QB, RB, WR and TE without treating projections as ADP, dynasty market value, expert consensus or a final lineup decision.

## Inputs

- `fantasy-management/automation/profiles/season-projection-movement.json`
- `fantasy-management/generated/operations/player-signals.json`
- current resolved player identity and position
- previous good profile state

The materialized player-signal contract is the required source. The observation run must not independently refetch FFToday or CBS Sports when the materialized dataset is current and usable.

## 1. Applicability

Apply this profile only to:

- QB
- RB
- WR
- TE

Kicker projections remain owned by the separate Kicker Daily Monitoring module. DST and IDP are outside the current league lineup scope.

## 2. Projection semantics

Keep three dimensions separate:

1. **Provider projection rank / percentile**: each provider's ordering by its own expected production.
2. **Projection consensus percentile**: arithmetic mean of the available provider position percentiles, used only as a provider-neutral rank signal.
3. **Managed-team core points**: current league scoring applied to projected raw stats shared by the active providers.

Do not average provider fantasy-point totals. Their scoring contracts are different.

Do not call the derived core points a complete exact league projection. Components not comparably projected by both active providers, including relevant two-point conversions and fumble-loss projections, are explicitly excluded rather than imputed.

## 3. Source readiness

For each player:

1. require a valid current `player-signals.json` row;
2. read provider freshness and join state from the materialized provider views;
3. accept one-provider coverage for movement monitoring when evidence confidence is at least medium;
4. prefer two-provider coverage for higher-confidence interpretation;
5. treat a source that has not completed its first successful materialization as unavailable, not as a zero projection;
6. preserve the previous good profile state if the current projection input is technically invalid.

## 4. Confidence

Use provider count, provider freshness, join quality and provider spread.

Guidance:

- no listed provider or invalid materialized state -> `low` / not evaluable;
- one current provider with a plausible player join -> at least `medium` when no contrary evidence exists;
- two current providers with plausible joins -> normally `medium` or `high`;
- a large provider percentile spread lowers interpretive confidence even when both providers are current.

The provider spread is an uncertainty signal. A large spread alone is not a notification criterion in version 1.

## 5. Materiality

The first successful state is a silent baseline.

After baseline:

- at least 10 consensus percentile points of cumulative movement versus the previous material state -> `medium`;
- at least 20 consensus percentile points -> `high`;
- first transition to two listed providers -> `medium` coverage event;
- small provider-point changes, small raw-stat changes and provider spread changes alone are not material.

If multiple criteria match, publish one event at the highest justified severity.

## 6. Interpretation

For a material event:

1. state direction and size of the consensus-percentile movement;
2. include each provider's rank/percentile and current league-scoring core points when available;
3. state provider spread and coverage count;
4. compare the signal with role, injury, usage, ADP and dynasty-market context when those states are available;
5. distinguish a production-expectation change from a market-price change;
6. translate relevance into the actual six-team, 2-QB, 2-TE, 4-FLEX managed-team context;
7. route the event to later roster, free-agent, trade or weekly-decision research as appropriate.

## 7. Decision boundary

This profile may flag that expected production changed materially. It must not by itself decide:

- Start/Sit;
- Add/Drop;
- Waiver priority;
- trade acceptance;
- a permanent Hold/Shop/Cut label.

Those decisions require the appropriate higher-level workflow, including ownership, roster opportunity cost, weekly context and other position-specific evidence.

## 8. State and notification

- no material change -> no event and no notification;
- new baseline -> state update allowed, no event and no notification;
- material change -> publish state, JSON event and Markdown event atomically;
- notify only after successful publication and only when the generic job severity threshold is met.
