# CP3p — layer-owned calibration and predictive team-strength hierarchy

2026-11-26. Research only. Refs #1451. Stacked on CP3n/o (draft #1692). User direction: separate player uncertainty, roster potential and realized utilization; avoid independently applying form weighting in downstream models; favor a shared predictive team-strength owner. This is a research proposal, not an adopted canonical architecture decision, production version, or cutover.

## Current source audit

2026 season metadata selects `schedule-outlook-v3` and `playoff-odds-v2` (`data-meta/nfl-reise/metadata.json`). Source inspection:
- `tools/derived_data_lib/models/season_stats/v1.py`: RelativeScoringStrength = actual season PPG / league actual PPG. ProjectedBestBallStrength = mean projected BB * mean projected lineup efficiency / 100. Descriptive and forecast-derived measures must remain semantically distinct.
- `tools/derived_data_lib/models/schedule_outlook/v3.py`: actual relative scoring strength blended with previous season, current-season weight min(1, g/(R/2)); current-season observations are equally weighted. V2 uses g/(g+K). V3 does not consume player projections. Remaining SoS compares opponents with other-team baseline. Preserve descriptive SoS as its own metric where appropriate.
- `tools/derived_data_lib/models/playoff_odds/v2.py`: already consumes the selected schedule-outlook Strength.Value; never computes/reweights strength itself. Scoring mean = league PPG × relative strength; spread = pooled SD of actual scores around team season means (current and previous season). Seeded independent normal score simulation and official points tiebreak; strict clinched/eliminated is mathematical and independent of estimated strength. V1 is exact equal-odds enumeration. Do not change historical model IDs or mathematical status.
- `tools/player_week_fantasy_materialize.py`, `tools/historical_projection_v4_calibration.py`: V4 historical weighting and recent role/usage signal (recent 3 played games, T-1 1.0 / T-2 .25 in historical baseline). Archived W5–11 PWF identifies V4-C, V4-C-PI1 and conditional participation. This is not a blanket last-three-games points weighting; player form is an upstream modeling responsibility.

## Proposed ownership / horizon contract (research, not implementation)

1. Player model owns conditional performance expectation, uncertainty and player-specific role/form. Participation/availability belongs to a separately identified upstream model or component; state precisely if adjustment has already been applied.
2. Roster potential model owns position constraints, eligible roster universe and aggregation of the player predictive distributions, including correlations if validated. Historical all-roster potential (TWP includes IR/taxi) differs from actionable live lineup potential. Do not silently conflate.
3. Manager/team model owns available information about lineup choice, realized utilization and lagged error corrections. A correction to BB should be fitted against BB, not team score. A manager utilization estimate should be fitted against actual score / comparable actual BB, not optimized to compensate for one version of the player model. That ratio is descriptive realization, not a pure causal skill measure: randomness and inaccessible slots remain.
4. Central predictive team-strength layer owns combining these estimates for a declared forecast horizon, with a versioned, calibrated distribution, as-of time, roster/availability scope, lineage and uncertainty. A short-horizon game projection is not automatically durable team strength: avoid carrying this week's bye, injury, locked lineup, opponent or game-specific effects into every future week. Use explicit horizon-specific projections when available; a longer-horizon predictive baseline needs separate validation and a defined fallback. Historical descriptive strength remains available separately.
5. Matchup win odds consume the relevant weekly score distributions; playoff simulation and predictive SoS consume the same centrally defined horizon-appropriate team-strength/distribution. They own only outcome/standings aggregation and schedule/bracket logic; no additional independent form weight. Current playoff v2 uses relative score and separate pooled score spread; a future version consuming absolute predictive distribution must not multiply by league PPG again or independently inflate/replace uncertainty without explicit validation.
6. Shared temporal policy: as-of and finality, causal windows, weight definitions, model/version provenance and diagnostics. One owner per signal, not one universal numeric decay for every target. Player role history, coach utilization, calibration residuals, and future horizon have different data-generating processes; weights should be justified by independent validation. Never apply the same recency signal twice downstream. If player models change, use version-specific residual history or cold-start/shrinkage until comparable forecasts accumulate; do not carry a correction that compensated for old model errors into a new version unchanged.
7. No historical contracts/writers changed. When independently validated, the canonical architecture/product owner, consumers and model-version transition require separate decision and review.

## CP3p empirical experiment

Runner `backtest_layered_best_ball_calibration.cjs`. Same seven pinned CP3m/CP3n pre-kickoff snapshots, and pinned final truth. DecisionWindows all roster placements (starter/bench/IR/taxi); archived PWF by provider player ID. Fixed 13-slot league formation 2 QB, 2 RB, 2 WR, 2 TE, 4 FLEX RB/WR/TE, 1 K. Virtual zero slots as in historical TWP. Forecast pool contains scheduled/unlocked players with available conditional forecasts, no availability adjustment beyond excluding non-unlocked/bye and missing projections. No unknown forecast is silently treated as an observed zero. This is a deliberately simple all-play MC benchmark, not CP3k history p(play); 1,200 independent normal draws with fixed deterministic team/week seed, SD from 90% intervals. Deterministic max of conditional point forecasts as control. Neither identifies pure player-model error; availability, distribution, candidate coverage, and player-model error remain conflated in BB residual.

Truth: canonical final matchups and TeamWeekPerformance. Check same exact Sleeper all-roster membership as archived snapshot; reconstruct hindsight maximum using final provider points and archived positions; parity within .05. 26/42 strict aligned; changed rosters remain a separate operational forecast comparison. Final TWP derived products were not published at all earlier cutoffs, so lagged efficiency/potential values are retrospective reconstructions of earlier finalized facts, not fully timestamp-attested product versions. Prior official points are checked against each archived Matchups finalized history (126 cross-snapshot comparisons, all equal); this does not prove earlier TWP revisions. No target Actual or target outcome used in forecast. 

Warm-up W5–6, six aligned rows. W7–11 = 30 target team-weeks / 15 matches; strict same-roster subgroup 20 / 7 complete pairs (conditioned on final membership; not prospective coverage). Fit from strictly earlier aligned rows only. Pooled additive BB correction = sum(actual BB - forecast BB)/(n+4) for each estimator, with 4 pseudo-observations of zero bias. Recency sensitivity weights .8^(weeks since latest finished week), same pseudo-count. Coach utilization = arithmetic mean of own historical actual/BB ratios shrunk toward pooled league ratio with 4 pseudo-weeks; own unavailable => league ratio. Additive missed-points alternative (same shrink). Team correction comparator pooled around current league efficiency, not a true prequential historic residual comparator. No tuning on evaluation. No Brier claim from this checkpoint: predictive distribution for manager/roster residual uncertainty not yet specified. 

| Strict aligned W7–11 | Best Ball MAE | Best Ball bias | Team MAE | Team bias |
|---|---:|---:|---:|---:|
| Raw MC × estimated utilization | 31.824 | +19.725 | 27.140 | +19.303 |
| Calibrated MC × utilization | 25.342 | +7.534 | 24.828 | +8.957 |
| Recent-weighted correction MC × utilization | 25.706 | +8.575 | 25.017 | +9.839 |
| Deterministic maximum × utilization | 30.165 | -21.074 | 25.918 | -15.309 |
| Calibrated deterministic × utilization | 23.346 | -2.337 | 23.186 | +.570 |
| Calibrated MC minus lagged missed points | — | — | 24.941 | +8.960 |
| Pooled team correction comparator | — | — | 25.675 | +7.742 |

All 30 target team-weeks (roster changes included, therefore not pure model error):
| Arm | BB MAE | Team MAE |
|---|---:|---:|
| Raw MC | 30.466 | 31.047 |
| Calibrated MC | 25.995 | 28.327 |
| Recent-weighted MC | 26.176 | 28.430 |
| Raw deterministic | 32.014 | 28.910 |
| Calibrated deterministic | 25.005 | 26.339 |
| Calibrated MC minus missed points | — | 28.642 |
| Pooled team correction | — | 28.151 |

Pooled MC correction W7–11: -13.440, -11.109, -10.548, -13.362, -13.714. Deterministic correction positive because the max of means ignores upside from realized selection, not because individual player means are demonstrably too low. Weighted sensitivity does not outperform simple pooled correction here. Do not choose decay or estimator on this sample.

## Exact error decomposition and oracle

Let B = actual comparable best ball, e = actual / B, Bhat = estimated calibrated BB, ehat = lagged estimated utilization. Forecast error is exactly:
    Bhat*ehat - B*e = (Bhat-B)*ehat + B*(ehat-e).
On strict subgroup calibrated MC: mean absolute potential term 21.537 points, mean absolute utilization term 15.450 points (not additive MAE because they can cancel). Mean signed terms +6.096 and +2.861 = +8.957. Oracle actual BB × lagged efficiency has MAE 15.450, efficiency prediction MAE 6.90 percentage points; true BB × true efficiency is the trivial identity, not a forecast. On all 30: terms 21.945 and 16.247, efficiency MAE 7.19 pp. Even perfect knowledge of theoretical potential would leave realization uncertainty, and present potential uncertainty is materially relevant. No variance-share or causal skill attribution.

## Interpretation, validation, next gate

Both simple additive corrections improve points estimates versus their corresponding uncalibrated arms; this is exploratory and can compensate for current PWF errors. Calibrated deterministic is a useful parsimonious control, not established superior to CP3k availability MC or CP3n/o lineup models. No apples-to-apples production win-prob or independent holdout in CP3p. Keep prior CP3n/o frozen holdout candidates unchanged. Next research: repeat separate BB correction for p(play)-aware archived candidate model, measure conditional player-error and availability independently, reconcile actionable and theoretical pools, evaluate team strength across future horizons and compare predictive downstream matchup/season odds on same as-of cohorts. Distinct validation of descriptive vs predictive strength. More untouched evidence and independent full CLI required; no production approval.

Reproduction: from full checkout of stacked branch `node research/matchup-projections/2026/backtest_layered_best_ball_calibration.cjs`. Actual committed forecast/evaluate functions executed in V8 over the seven pinned inputs in three batches; aggregate walk and validation executed using extracted per-team numerical rows (full MC precision, deterministic values at 4 decimal places, known canonical matchup pairs represented by team pair). All target/future outcome perturbation invariance checks and exact error decomposition identity passed. Prior official score check independently run in V8 over the seven archived histories; optimized mean and prior score guard committed after replay (mean-equivalent change, no full CLI). Direct checkout remains DNS-blocked. No independent complete CLI run. No changes to production files, CI inventory, workflows, data contracts or app. Rollback research branch only.
