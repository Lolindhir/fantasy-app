# CP3k – Robustness and manager-score / win-chance research (24.11.2026)

Refs #1451. Stacked on CP3j (Draft #1660, head a2dad9825a26fe6bd729a75a8f131e03774f6908); CP3i #1637 also remains draft. Runner: `backtest_pplay_robustness_manager.cjs` (commit 6277673ac401d2acc47026055438c9c0252e5bb3). **Research only; no production model, data product, workflow, writer, CI or consumer changes.**

## Design and data
- Pinned inputs at CP3j head a2dad982 (identical data at CP3k runner commit). Six league teams in each of 2025 and 2026 W5–10. 2025 is additional test data; 2024 excluded from primary comparison because it was used in PWF point/range fitting and CP3i selection. Both years are retrospective, not certified point-in-time.
- Frozen CP3i training 2016–22 (128,087), validation 2023–24 (36,134); 13 groups, global p=0.4367968646310711; same validation optimum k400/alpha8/window4, Brier 0.09091. Status-only k20. No refit on test outcomes.
- Same conditional PWF PI1 projection and archived entire roster/weekly positions, including IR/Taxi; same slots. Three paired arms: all-play, lagged status, lagged history. 1,200 draws each, seeds 20261123/17/991, normal and mean-centered split-normal sensitivity. Split slopes use distance from point projection to lower/upper PI1 bounds (clipped at zero) / z90; subtract analytic mean shift. It is not a fitted distribution and need not reproduce PI1 quantiles after centering. All arms share normal and uniform draws per team-week, independent across players/teams; correlation/workload given participation remain unmodeled.
- Exact specialized fixed-position + unrestricted RB/WR/TE FLEX optimizer, checked against existing global Hungarian assignment for projected points and first draw of each arm/seed/distribution. Reject unsupported slots. Virtual zero slots retained as in CP3j. 1,330 numerical equivalence checks (19 per accepted team-week). Not independent solver verification for all draws.
- Fail closed on missing prior record, incomplete deterministic projection, or non-reproduced TWP PotentialPoints (>0.05 or empty realized slots). 2025 W7 clr-404c16cec9545e41bcfd6114ff4c755a target nonreproduction; 2026 W10 clr-dc35c0c936175f68a694e7b05bd6861d missing prior for NFLP-14c210d263a1a64d8019. 35/36 accepted each year, 70/72 overall. Win evaluation only on complete two-sided canonical matchup IDs: 17 each, 34 total. Same sample across arms. Excluding target-misaligned cases conditions evaluation on retrospective evidence; cannot claim prospective coverage.
- Manager score = mean simulated Best Ball × arithmetic mean of prior finalized TWP EfficiencyPercent within season (minimum four weeks). No target-week efficiency; no locks or actual starter inputs. Target TWP ActualStarterPoints. Win probability = fraction of paired independent team draws where scaled score exceeds opponent (+0.5 on simulation ties); Brier against TWP OfficialMatchupPoints winner (0.5 for actual tie convention). Efficiency is deterministic per team-week, no residual distribution, custom score adjustment model or calibration; not current production win-prob-v1. Brier of constant 50% on non-ties is 0.25; not evidence of useful calibrated probability here.

## Main results (normal, seed 20261123)
MAE/bias in fantasy points; bias forecast minus target; coverage nominal 80% Best Ball interval.
| Season | Arm | n | BB MAE | BB bias | BB coverage | Manager MAE | Manager bias | matches | Brier |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
|2025|all|35|29.51|+16.23|54.3%|23.17|+6.07|17|0.2816|
|2025|status|35|27.39|-11.73|68.6%|24.33|-16.74|17|0.2774|
|2025|history|35|26.56|-6.93|74.3%|23.19|-12.85|17|0.2759|
|2026|all|35|30.70|+22.99|57.1%|27.37|+15.65|17|0.2270|
|2026|status|35|23.11|-3.38|77.1%|23.30|-5.80|17|0.2536|
|2026|history|35|22.83|+1.85|77.1%|23.39|-1.53|17|0.2443|
|Combined|all|70|30.10|+19.61|55.7%|25.27|+10.86|34|0.2543|
|Combined|status|70|25.25|-7.55|72.9%|23.82|-11.27|34|0.2655|
|Combined|history|70|24.70|-2.54|75.7%|23.29|-7.19|34|0.2601|

Deterministic projected Best Ball × same prior actual efficiency: aggregate manager MAE 29.41. Not a probability arm.

## Sensitivity (combined, same cohort)
Each cell BB MAE / manager MAE / Brier. Values rounded from weighted batch means (team-week weights for points; complete matchup weights for Brier).
| Distribution / seed | All-play | Status | History |
|---|---|---|---|
|Normal 20261123|30.103 / 25.271 / .2543|25.249 / 23.817 / .2655|24.697 / 23.289 / .2601|
|Normal 17|30.196 / 25.272 / .2522|25.173 / 23.690 / .2622|24.702 / 23.161 / .2599|
|Normal 991|29.983 / 25.166 / .2522|25.096 / 23.787 / .2617|24.571 / 23.254 / .2598|
|Split 20261123|30.766 / 25.628 / .2505|25.240 / 23.840 / .2630|24.672 / 23.347 / .2583|
|Split 17|30.848 / 25.632 / .2490|25.163 / 23.708 / .2602|24.680 / 23.196 / .2573|
|Split 991|30.629 / 25.545 / .2485|25.098 / 23.804 / .2612|24.546 / 23.280 / .2589|

Ranking identical across all six combined configurations. 2026 normal/base seed reproduces CP3j BB metrics to rounding. Additional 2025 evidence is weaker: BB improves but manager MAE is essentially tied vs all-play, with negative manager bias. Combined history improves BB MAE 18.0% and manager MAE 7.8% vs all-play, but worsens Brier. Individual-history incremental benefit vs status only 0.55 BB / 0.53 manager points, not proven significant. 12 correlated NFL weeks and 34 matchups, repeated players/managers; multiple seeds do not increase the effective sample size. No significance or production superiority claim.

## Interpretation and next research gate
Hypothesis, not established causal result: historical Actual/Potential efficiency may absorb some of the participation/roster/selection effects already treated by availability sampling; multiplying a reduced Best Ball by the unchanged efficiency may overcorrect manager points. Separate coach choice from availability, residual game randomness and roster feasibility. Compare walk-forward calibration of efficiency conditional on each forecast arm, a lag-only residual correction and residual predictive variance against current win-prob-v1 and 50% on a strictly common out-of-sample matchup set. Fit only prior seasons/weeks; keep future weeks untouched. Then test shared NFL game/player correlations and genuinely timestamped roster/lock/projection snapshots; no inference of past in-week manager actions. No production activation until explicit model/version contract and validation gates.

## Validation, reproducibility, rollback
- Refit actual CP3i train/validation products in isolated V8, independently reselect exact hyperparameters; CP3j synthetic self-test passed in V8. CP3k committed `runWeek` and `report` ran in six two-week batches on pinned true JSONs. Tool limits required a V8 harness with Node shims, formula-equivalent CP3i forecast and slot-list functions, and earlier TWP projections reduced to the exact fields consumed by runWeek; the fixed model group counts were copied from the actual retraining. Not an independent complete CLI execution. The full CLI and CP3k CLI self-test are not yet executed. Direct Git checkout blocked by DNS; large files fetched by Git blob. No one-off workflow introduced.
- From complete checkout of this stacked branch: `node research/matchup-projections/2026/backtest_pplay_robustness_manager.cjs --self-test`; `node research/matchup-projections/2026/backtest_pplay_robustness_manager.cjs`. Verify both commands and all six configurations, exclusions, and parity before independent review. Ordinary PR CI is not the full research replay. CI inventory impact: standalone research script outside production test inventory/CI, no changed CI routes or existing tests.
- No production data/source/derived/consumer/secret changes; no guidance or canonical architecture contract update needed. This report and runner are the only CP3k files. Rollback by reverting CP3k research commits or abandoning the stacked draft, not altering dependent PRs. Keep draft unmerged pending dependency reconciliation and independent full-CLI/research review.
