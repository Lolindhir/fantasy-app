# CP3l – Lag-only team-strength benchmarks (25.11.2026)

Refs #1451. Research only; new standalone benchmark, stacked on CP3k to preserve its exact pinned input tree 5712ec20e6207c1b3afee0a64abd3cb8adcf75ae. No production, contracts, writers, workflows or CI routing changes.

## Design
Seven fixed baselines: prior league average (50% probability), prior team mean, last 4 mean, team mean shrunk by 4 pseudo-weeks toward league mean, prior mean PotentialPoints × mean actual EfficiencyPercent/100, prior mean PotentialPoints − mean MissedPoints, and exponentially weighted actual starter score (weight 0.8 per elapsed week). All features from finalized earlier TeamWeekPerformance documents of the same season only; target official points for outcome and actual starter points for score loss. Matchup IDs from canonical archived matchup records used only for pairing. Normal-difference probability with per-arm pooled team RMSE of previous prequential residuals (starting week 3), floor 10; fixed 35-point fallback before 12 errors. No target-week outcomes in predictors or scale; all weeks scored before error updates. No claim of true historical revision snapshots. No PWF, roster or player inputs. Additive missed-points arm is algebraically equivalent to actual mean except rounding, a negative control, not an independent model family.

2025/26 W5–10 full cohort 36 teams and 18 matches each. Exact CP3k accepted cohort 35 teams and 17 matches each, excluding 2025 W7 clr-404c16cec9545e41bcfd6114ff4c755a and 2026 W10 clr-dc35c0c936175f68a694e7b05bd6861d and their respective matchups. All metrics computed on identical arms; prior history not retroactively censored by target-week CP3k exclusions. Separate fixed-family extension 2025 W11–14, 24 teams/12 matches; not a certified untouched holdout because earlier project research may have seen it. CP3k has already exposed W5–10 outcomes in both years; no independent validation or final model selection.

## Results
Full W5–10 (MAE / Brier), and extended 2025 W11–14:
| Model | 2025 | 2026 | 2025 W11–14 |
|---|---|---|---|
| League mean | 23.027 / .2500 | 27.020 / .2500 | 24.698 / .2500 |
| Season mean | 24.244 / .2579 | 27.317 / .2271 | 25.381 / .2692 |
| Last4 | 24.318 / .2568 | 28.293 / .2367 | 24.908 / .2238 |
| Shrink4 | 23.009 / .2544 | 25.630 / .2265 | 25.044 / .2639 |
| Potential × efficiency | 24.289 / .2574 | 27.257 / .2262 | 25.542 / .2686 |
| Potential − missed | 24.244 / .2579 | 27.317 / .2271 | 25.381 / .2692 |
| EWMA | 23.796 / .2508 | 27.525 / .2203 | 25.134 / .2305 |

Paired CP3k cohort (manager MAE / Brier):
| Model | 2025 | 2026 | Pooled (70 teams/34 matches) |
|---|---|---|---|
| League mean | 22.214 / .2500 | 25.556 / .2500 | 23.885 / .2500 |
| Season mean | 23.295 / .2638 | 26.435 / .2358 | 24.865 / .2498 |
| Last4 | 23.327 / .2567 | 27.234 / .2481 | 25.281 / .2524 |
| Shrink4 | 22.093 / .2586 | 24.524 / .2331 | 23.308 / .2459 |
| Potential × efficiency | 23.344 / .2637 | 26.387 / .2353 | 24.866 / .2495 |
| Potential − missed | 23.295 / .2638 | 26.435 / .2358 | 24.865 / .2498 |
| EWMA | 22.746 / .2530 | 26.630 / .2304 | 24.688 / .2417 |
| CP3k all-play MC | 23.17 / .2816 | 27.37 / .2270 | 25.27 / .2543 |
| CP3k prior status MC | 24.33 / .2774 | 23.30 / .2536 | 23.82 / .2655 |
| CP3k lag history MC | 23.19 / .2759 | 23.39 / .2443 | 23.29 / .2601 |

The MC results are from the previous committed CP3k report, not independently replayed in CP3l. EWMA has lower observed aggregate Brier than the MC arms and 50%, shrink4 comparable manager MAE to history MC. However, only 34 correlated matches, post-hoc comparison, no uncertainty test, no independence claim. 2025 EWMA is worse than 50% on paired cohort. Recency appears promising, not a validated fixed choice. Historical additive missed points is redundant with team mean. Score MAE and Brier rankings differ; direct expected lineup choice, residual calibration and ensembles are worth comparing. Productive win-prob-v1 exact inputs include actual as-of starter selection, bye/out and player ranges; no archived inputs proven here. CP3k MC is not win-prob-v1. Never interpret these numbers as superiority over production.

## Validation and rollback
Runner bff93b52 exports run and selfTest. Synthetic test checks target-week score perturbation cannot change same-week predictors/scale, 50% baseline and exact team/matchup counts. V8 PASS before commit and PASS on readback of committed script; exact readback run on real pinned 2025/26 W1–10 TWP and W5–10 matchup products reproduced full cohort and produced exact paired cohort. Extension W11–14 executed on real pinned inputs before commit using same run function. Direct git checkout DNS blocked; no full independent Node CLI or CI success claim. CLI: node research/matchup-projections/2026/backtest_lag_only_team_strength.cjs --self-test and same without flag (requires pinned commit locally available). No test inventory or Fast/Deep changes (standalone research). Rollback two research files/branch only. Keep draft pending independent reproduction and reconciliation of stacked dependencies.
