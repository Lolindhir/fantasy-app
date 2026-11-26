# CP3n/o — archived as-of lineup selection, ensemble, and residual calibration

Date: 2026-11-26. Research only; no production activation.

## Inputs and reproduction

CP3m's seven pinned 2026 pre-first-kickoff Git snapshots (W5–11) and final truth SHA are used unchanged. Each forecast uses its own archived PlayerWeekFantasy, DecisionWindows, MatchupProjections and strictly finalized earlier Matchups history, not the subsequently revised current tree. The archive commit date must precede the first kickoff. Actual scoring inputs for the target week are rejected; outcome join occurs separately. The historical season-statistics delivery did not exist in every snapshot, so efficiency arms were removed from the common comparison (W11 isolated experiment only). Roster fill is restricted to available candidate evidence in the snapshot; no imputation of missing slots.

Runner: `node research/matchup-projections/2026/backtest_asof_lineup_ensemble.cjs` at the research branch, using local Git history. Calibration runner: `node research/matchup-projections/2026/backtest_asof_residual_calibration.cjs`. Direct complete local checkout/Node CLI reproduction remains blocked by DNS in the current environment. The committed CP3n functions were read back and executed in V8 on all seven genuine archive weeks. Target-result perturbation invariance, rejection of injected target actuals and unfinalized history passed on all seven archived weeks. CP3o functions executed in V8 on the extracted CP3n per-team output (mu/sigma rounded to five decimals) and re-read earlier official scores from all seven archived histories; earlier official scores agreed with the final truth for all comparable observations. Perturbing the last evaluation week's outcome left all calibration forecasts unchanged. CP3o standalone CLI has not been independently executed.

## CP3n — common cohort

33 team-weeks / 15 complete paired matchups. Team outcome MAE (points), Brier (lower better):

| Arm | MAE | Brier |
|---|---:|---:|
| Archived production baseline / v1 replay | 30.571 | .269353 |
| Direct projected optimal lineup | 28.582 | .238660 |
| Direct with +3 incumbent-starter utility | 27.557 | .229278 |
| Direct risk penalty .25 sigma | 28.579 | .238526 |
| Lag-only EWMA .8 | 29.332 | .242952 |
| Shrink team mean toward league mean, k=4 | 26.573 | .238845 |
| Baseline + EWMA 50/50 | 29.258 | .255544 |
| Direct + EWMA 50/50 | 28.205 | .234640 |
| Incumbent lineup + EWMA 50/50 | 28.014 | .229245 |

Direct/incumbent lineup overlap with eventual starters: 10.15 / 11.33 of 13 on common teams. This is diagnostic only, not a prospective comparison using observed final starters as inputs. The +3 is a research choice, not a fitted manager-specific coefficient. Half-confidence ensemble (p -> .5 + .5*(p-.5)) Brier .224988. Improvement against mixed historical baseline is exploratory. Only W10–11 actually published v1; W5–8 used original published ranges with the later v1 probability formula. On W10–11 common 5 pairs, baseline .376438 versus incumbent .309030, both worse than .25. W9 had no complete baseline matchup.

## CP3o — sequential residual calibration and explicit fallback

For each arm separately, fit residuals from strictly earlier archived forecasts whose official scores are present in the target snapshot's finalized history. Pooled bias = sum(actual - forecast)/(n+12); variance shrinks squared centered residuals toward that target team's original sigma squared with 12 pseudo-observations and a sigma floor of 10. No outcome from the target week is used for fitting. Bias correction shared across teams largely cancels in probability differences; width calibration can affect Brier. Fallback = lag-only shrink4 when a complete direct lineup/ensemble cannot be formed. The calibrated ensemble fallback uses calibrated shrink4. No synthetic zero or null-to-zero substitution.

| Arm | MAE common 33 | Bias common 33 | Brier common 15 | Brier half confidence |
|---|---:|---:|---:|---:|
| Baseline | 30.571 | +2.956 | .269353 | .238435 |
| Baseline calibrated | 31.027 | +2.904 | .262452 | .237378 |
| Incumbent | 27.557 | +13.020 | .229278 | .227112 |
| Incumbent calibrated | 27.403 | +7.514 | .226931 | .225417 |
| Shrink4 | 26.573 | +4.766 | .238845 | .234778 |
| Shrink4 calibrated | 27.271 | +2.828 | .239619 | .235939 |
| Ensemble | 28.014 | +8.251 | .229245 | .224988 |
| Ensemble calibrated | 28.195 | +4.912 | .226322 | .224096 |

Calibration reduces ensemble bias substantially but does not improve common-cohort MAE. Incremental Brier gain is small and not independent. No calibration superiority claim.

Coverage-sensitive comparison on baseline-available 37 teams / 18 complete pairs:

| Arm | MAE | Brier |
|---|---:|---:|
| Mixed baseline | 29.870 | .264053 |
| Shrink4 | 25.450 | .243919 |
| Incumbent fallback | 26.328 | .235089 |
| Ensemble fallback | 26.735 | .236435 |
| Calibrated ensemble fallback | 26.725 | .234391 |

All 42 teams / 21 matchups with explicit fallback (baseline cannot be fairly included on this cohort):

| Arm | MAE | Brier |
|---|---:|---:|
| Shrink4 | 25.217 | .227935 |
| Incumbent fallback | 26.212 | .212914 |
| Ensemble fallback | 26.210 | .215341 |
| Calibrated ensemble fallback | 25.923 | .215316 |

The 50% benchmark is .25 in these non-tied cohorts. The fixed half-confidence uncalibrated ensemble on the 15 common pairs remains below the mixed raw baseline when omitting any one of the six weeks with common pairs (ensemble .20945–.24495 versus corresponding baseline .23860–.33085). This leave-one-week-out diagnostic is not independent validation or a significance test; matchups within a week and repeated teams are correlated.

## Research decision and prospective holdout

Prefer a simple explicit incumbent-aware lineup plus lag-only fallback as the primary *candidate*, retain 50/50 EWMA ensemble and its sequential calibration as comparisons, plus shrink4, actual archived production v1 and 50%. Freeze these rules now; no selecting a winner by the exploratory W5–11 table. For every untouched prospective week, choose the last committed pre-first-kickoff snapshot by timestamp without inspecting outcomes. Record availability and each forecast first, then score only after official finalization; compare on the same production-available pairs and report full candidate coverage separately. Report Brier, MAE, bias and sample size, weekly clustering, no omitted missing slots. Weeks 12–13 are an initial prospective regular-season check only (too small for superiority); continue with additional genuinely untouched comparable weeks/seasons before selecting a model. Playoff cohorts require explicit eligible matchup rules, not assumed regular-season structure. Do not change coefficients, blend, fallback or confidence mapping using the held-out outcomes; any change creates a new exploratory arm and needs a new holdout.

No validated replacement yet. No live writer, contract, inventory, CI, or production changes. Direct local full-CLI replay and independent prospective comparison still required. Research campaign stays open; this is a stable checkpoint, not CP4 or production approval.
