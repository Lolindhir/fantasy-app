# Free-Agent Movement Materiality

## Purpose

This contract defines deterministic materiality for the common QB/RB/WR/TE/K Free-Agent Movement Discovery layer. It narrows broad source movement into research-relevant state without creating Add/Drop, Waiver or roster recommendations.

The implementation is owned by:

```text
fantasy-management/automation/free-agent-movement-materialization.json
fantasy-management/_ai/scripts/build_free_agent_movement_dataset.py
fantasy-management/_ai/scripts/free_agent_movement_market_calibration.py
fantasy-management/_ai/scripts/free_agent_movement_contract.py
fantasy-management/_ai/scripts/build_free_agent_movement_events.py
```

The generated state remains:

```text
fantasy-management/generated/operations/free-agent-movement-signals.json
```

Daily research triggering remains the responsibility of the downstream deduplicated `free-agent-movement-events.json` contract.

## Comparison windows

Movement is evaluated across the shared calendar windows:

```text
1 / 3 / 7 / 14 / 30 days
```

The windows are anchored to the Movement evaluation date, currently derived from the current `free-agent-signals.json -> generated_at` date. For a window of `N` days, the cutoff is:

```text
evaluation_date - N days
```

Each provider then uses the last available successful normalized snapshot **at or before** that cutoff. The comparison is not anchored to the provider's last changed snapshot date.

This distinction is intentional for `--skip-unchanged` sources. A source may have been successfully refreshed today while its normalized content last changed several days earlier. Freshness/heartbeat answers whether the source was checked successfully; snapshot history answers when the source content changed. Those concepts must remain separate.

Example for an evaluation on 2026-08-18 with a source whose latest changed snapshot is 2026-08-16:

- the 1-day cutoff is 2026-08-17, so the 2026-08-16 snapshot may serve as both current state and last snapshot at/before the cutoff, producing no synthetic 1-day movement;
- the 3-day cutoff is 2026-08-15, so a 2026-08-15 snapshot can expose the genuine cumulative change between 2026-08-15 and 2026-08-16.

Long windows are not fallback-only diagnostics. Calibration on 2026-08-18 showed that the overwhelming majority of current numeric movement discoveries were first visible beyond the 1-day window. Removing the longer windows would therefore create material false negatives for gradual risers and fallers.

## Dynasty market source roles

### FantasyPros

`fantasypros-dynasty-superflex-ppr` is the authoritative source for hard Dynasty expert-consensus tier movement.

A changed FantasyPros tier is a high-severity `tier_change` threshold crossing. Existing FantasyPros overall-rank and position-rank materiality remains governed by the versioned `market-movement` profile.

### FantasyCalc

`fantasycalc-dynasty-superflex-ppr-8-team` is a market-value source, not the authoritative expert-consensus tier source.

FantasyCalc `maybeTier`/normalized `tier` remains available in provider-specific current and historical context, but a FantasyCalc tier change **must not by itself create hard materiality**.

FantasyCalc instead has independent quantitative market materiality so that real market movement is not masked by or forced through FantasyPros semantics.

## FantasyCalc percentile movement

The primary independent FantasyCalc hard signal is list-length-aware percentile movement:

```text
abs(delta percentile) >= 10 percentage points -> medium
abs(delta percentile) >= 15 percentage points -> high
```

The rule applies independently to every available 1/3/7/14/30-day window.

Replacement proximity affects research priority/context but is not required for the percentile movement to exist. This preserves visibility for an under-the-radar free agent who is moving materially before crossing the current league replacement boundary.

## FantasyCalc raw-value movement

FantasyCalc raw market value is retained as a complementary hard signal only when **both** absolute and relative movement are material:

```text
medium:
  abs(value delta) >= 250
  AND abs(value percent change) >= 20%

high:
  abs(value delta) >= 500
  AND abs(value percent change) >= 30%
```

A percentage-only value rule is prohibited. Low-value assets can produce very large percentage changes from small absolute moves, which would create excessive false positives.

The raw-value rule supplements rather than replaces percentile movement. A player can cross either quantitative FantasyCalc rule, and both crossings may coexist when the move is large in both normalized rank position and provider-native value.

## Cross-source semantics

Signal families remain separate:

- Redraft ADP;
- Dynasty market;
- Season Projection.

FantasyPros and FantasyCalc are separate provider views inside the Dynasty-market family. Their provider-native values and tiers are preserved; they are not averaged into a single canonical player value.

Cross-signal confirmation/divergence continues to operate on comparable family-level percentile movement. Provider-specific materiality does not turn FantasyCalc into an expert-consensus source or FantasyPros into a trade-value source.

## Materiality-contract migrations

Movement state persists two independent provenance fingerprints before event comparison:

- `materiality_contract.fingerprint` describes the semantic rules used to classify Movement state;
- `evidence.input_fingerprint` describes the current evidence/context evaluated under those rules.

The materiality-contract fingerprint includes the explicit positive integer `materiality_contract.version`, comparison windows, resolved materiality thresholds, replacement rules, cross-signal rules and activity thresholds. Any semantic materiality-code change that is not already represented by those resolved values **must bump `materiality_contract.version`**. Logging, formatting and performance-only changes must not bump the version.

The evidence fingerprint includes the current Free-Agent and Player input fingerprints, evaluation date/current and baseline ranking-history identities, league state, source-catalog content and Movement history/quality context. Previous-Free-Agent rollover is intentionally excluded because structural Day-over-Day changes are edge events; rolling that baseline forward must not make otherwise identical current evidence appear new.

The event layer applies this policy only when **both the current and previous Movement states carry both fingerprints**:

```text
same contract
  -> normal comparison

changed contract + identical evidence
  -> baseline_mode = contract_migration
  -> silent rebaseline
  -> events = []
  -> candidate migration diff remains audit-visible as suppressed counts

changed contract + changed evidence
  -> baseline_mode = contract_migration_with_evidence_change
  -> fail open
  -> normal events retained
  -> quality = warning
```

A legacy previous state without comparable fingerprints can never enable silent suppression. It remains a normal comparison until two comparable fingerprinted Movement states exist.

This is a safety rule: a configuration or code change alone is never sufficient reason to suppress monitoring events. Silent rebaseline is permitted only when the Event layer can prove that the current evidence fingerprint is identical across the contract boundary.

After a silent migration, the newly published Movement state becomes the normal previous baseline for the next materialization. An unchanged subsequent run therefore returns to ordinary `comparison` mode with zero events.

## Calibration evidence: 2026-08-18

A production-shaped audit against 1,175 actual fantasy free agents after applying this contract produced:

- 289 current Movement discoveries;
- 60 high-priority and 229 medium-priority discoveries;
- positions: K 18, QB 48, RB 67, TE 56, WR 100;
- 204 discoveries with Dynasty-market materiality, 5 with Redraft-ADP materiality and 7 with Season-Projection materiality;
- 179 discoveries with at least one numeric hard threshold;
- earliest numeric material window: 1d 4, 3d 6, 7d 29, 14d 100, 30d 40;
- 19 discoveries with independent FantasyCalc quantitative materiality;
- 11 of those 19 had no other numeric hard threshold;
- 13 of those 19 were near or above the current league roster/replacement boundary;
- 5 had a high-severity FantasyCalc quantitative crossing.

After authoritative-tier restriction, all 225 current `tier_change` threshold records in the audit came from `fantasypros-dynasty-superflex-ppr`; FantasyCalc contributed zero hard tier-change records.

These counts are calibration observations for the source state on 2026-08-18, not permanent expected population sizes.

## Recalibration rule

Do not lower or raise thresholds merely because one day's Discovery state looks large or small. Recalibration should inspect event volume, replacement relevance, source-specific false positives/false negatives and mature comparison-window coverage.

The next focused calibration should occur after Redraft ADP and Season Projection histories have matured enough for reliable 14/30-day comparisons. Dynasty FantasyPros/FantasyCalc history already supports the complete window set; newer ADP/projection sources do not yet all have equivalent long-window depth.

Any future provider-specific tier or value rule must be configured explicitly. A source field named `tier` must never automatically inherit authoritative hard-tier semantics solely because it is mapped into the common Market provider view.
