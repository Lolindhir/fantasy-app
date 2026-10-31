# Issue #1236 — post-Source projection baseline reconciliation (2026-10-31)

## Context and authority

The reviewed Cody White PFR token `WhitCo05` was attached to `NFLP-caf7c3d6786fcd72e704` by Source PR #1252 and materialized by [NFL Source Sync 41240534780](https://github.com/Lolindhir/fantasy-app/actions/runs/41240534780). Exactly 37 published REG snap rows across 2021, 2022 and 2024–2026 now resolve to Cody; frozen non-identity facts are unchanged. This correct Source-owned fact increases participating-player coverage used by **independent, non-Salary NFL projection backtests**. The source-code-only PR #1253 was green in CI #1807; its intentionally repeated CI #1808 **after the live Source publication** exposed old exact projection snapshot expectations.

## Reviewed differences in CI #1808

- **V1 walk-forward** 2024+2025 predictions: **11,361 → 11,369** (2024 +1, 2025 +7), from formerly unlinked offensive appearance evidence. 2024/2025 cold starts **629→630 / 641→642**. 2024/2025 unresolved-participation counts **6→4 / 13→5**. Source scoring model is unchanged.
- **V2 / V3 calibration** comparable source observations: **11,297 → 11,298**; the selected V2 baseline remains previous-season position mean with K=0.5, and selected V3 current K remains 1.0, with player-history decay 0.25 unchanged.
- **V4 2025 independent holdout**: **5,724 → 5,731**; selection against 2023–2024 recalibration changes V4-A Ridge **16→0** and V4-B Ridge **16→4**, while V4-C remains 64. On the new holdout, baseline V3 MAE/RMSE 4.5431/6.2429; V4-A 4.5277/6.2327; V4-B 4.5341/6.2375; V4-C 4.5305/6.2280. All three retain strict improvement over V3. V4-A remains best MAE, V4-C best RMSE.
- **Team V4 2025** remains the same 97 complete weeks / 85 all-starters-participated weeks, but exact model projections shift slightly due recalibrated coefficients. V4-C continues to improve both team-level MAE (24.3642 vs V3 24.4566) and RMSE (30.2252 vs V3 30.3207); V4-A remains worse on both.

## Change discipline

Five existing `tools/tests/test_nfl_source_projection*.py` tests retain strict **exact** reproducibility assertions with their new real published Source baselines. No tolerance, skip, disabled check, algorithm, output contract, model parameters, storage writer, schedule, permissions or generated data changes. Refresh numbers were read directly from the machine-readable `V1_BACKTEST_SUMMARY`, `V2_CALIBRATION_SUMMARY`, `V3_CALIBRATION_SUMMARY`, `V4_CALIBRATION_SUMMARY` and `V4_TEAM_2025_BACKTEST_SUMMARY` records in [CI #1808](https://github.com/Lolindhir/fantasy-app/actions/runs/41245069066). Require new CI to rerun all 5 strict assertions and the repository Merge Gate before merging follow-up. This Source-phase test-only change itself matches the existing Source Sync workflow push trigger; check semantic no-op after publication.

Phase B Salary/GamesPlayed remains separate and unmerged until these Source-owned snapshot tests and the new B combined-Source CI are green. See Issue #1236 for work status.
