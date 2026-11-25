# CP3m – Pre-kickoff Git archive evidence (25.11.2026)

Refs #1451. Read-only audit, research-only report. This supersedes the earlier blanket assumption that no historical as-of inputs can be retrieved; does not establish complete archival coverage or superiority. No production changes.

## Pinned forecast and outcome inputs

For each 2026 week query GitHub commit history for public/data/MatchupProjections.json with an until cutoff just before scheduled first kickoff, then read MatchupProjections.json and DecisionWindows.json from the returned commit. Verify season/week, commit committer time < minimum DecisionWindows[].StartsAtUtc, all FinalStarterCount=0. Source history cutoff queries before W1–4 returned no commit for this path; this is not proof that other historical inputs are absent.

| Week | Forecast commit | Commit UTC | First kickoff UTC | Model | Complete pairs |
|---|---|---|---|---|---|
|5|a6e44e497cef4b1e05e665b0d16ce9dcc79f668c|2026-10-08T21:35:20Z|2026-10-09T00:15:00Z|pre-v1|3|
|6|47b93807dba5aacdbb9bd9904fd8df2f00e86e17|2026-10-15T21:13:28Z|2026-10-16T00:15:00Z|pre-v1|3|
|7|b772191c64cfe0434e5eeec45dee74a0a812f3f7|2026-10-22T23:13:28Z|2026-10-23T00:15:00Z|pre-v1|3|
|8|3b1bd8f163a631cee81ec708d550f5c8195201e5|2026-10-29T22:58:14Z|2026-10-30T00:15:00Z|pre-v1|3|
|9|ecdc08690342b6f55b9cf6e08ff3c04ea6a2edfd|2026-11-05T23:56:20Z|2026-11-06T01:15:00Z|pre-v1|0|
|10|1166a6d6f32b6dc517fe7b226ce15802b705023a|2026-11-13T00:43:03Z|2026-11-13T01:15:00Z|win-prob-v1|3|
|11|23a4b5f896543096e3b4e3c33fafac6aece36eda|2026-11-19T11:33:24Z|2026-11-20T01:15:00Z|win-prob-v1|3|

Truth commit 9ff07162a701ea3545de23020fa9f022bf7aac02; read canonical data-source/leagues/nfl-reise/seasons/2026/matchups/week-W.json (Sleeper ProviderRosterID -> CanonicalLeagueRosterID and shared CanonicalLeagueMatchupID) and data-derived/team-week-performance/nfl-reise/2026/WW.json (FinalityEvidence, OfficialMatchupPoints winner, ActualStarterPoints for score loss). For each pair verify both source rows share the canonical matchup identity. All seven snapshots passed date/week/finality checks. Commit timestamps evidence repository publication chronology, not independent provider acquisition attestations.

## Reproduction
Use git show FORECAST_SHA:public/data/MatchupProjections.json and git show FORECAST_SHA:public/data/DecisionWindows.json. Use truth SHA for the two canonical outcome products above. On pairs with finite mean and sd for both teams, calculate p = statistics.NormalDist().cdf((mu_a-mu_b)/math.hypot(sd_a,sd_b)), y = 1 for official winner A, 0 for B, 0.5 for tie; Brier = mean((p-y)**2). Missing mean/sd is unknown, not 50%. The observed calculation used a standard normal CDF approximation in V8; negligible rounding error relative to reported precision. W5–9 have no WinProbabilityModel, so this is a replay of the later v1 formula on original published team ranges, not a claim those probabilities were originally published. W10 rounded published probabilities match replay; W11 raw displayed probabilities match replay to within 1e-6. No change to historical recaps or consumer products.

Observed probabilities for first named provider roster and official binary outcomes (order is only for reproducibility):
| Week | Provider roster pair | p(A) | y |
|---|---|---:|---:|
|5|5/6|.146377|0|
|5|1/4|.122037|1|
|5|2/3|.473421|0|
|6|1/6|.759485|1|
|6|2/5|.890423|1|
|6|3/4|.986261|1|
|7|1/5|.692748|0|
|7|2/4|.585990|0|
|7|3/6|.611137|1|
|8|4/6|.355679|1|
|8|3/5|.840546|1|
|8|1/2|.523243|0|
|10|2/3|.276176|0|
|10|1/4|.597334|1|
|10|5/6|.031138|1|
|11|1/6|.690986|1|
|11|2/5|.756284|0|
|11|3/4|.635147|1|

Brier: W5–8 pre-v1 replay 0.231273 (12); W10–11 actual v1 0.329613 (6); pooled heterogeneous 0.264053 (18/21 scheduled). W9 all three incomplete; never present as zero or 50%. The sample is too small, correlated, mixed model versions/coverage and heterogeneous time-to-kickoff. No independent superiority result. W11 two hybrid complete pairs only; no probability claim.

## Additional archive proof and next research direction
At W11 forecast SHA, data-derived/player-week-fantasy/nfl-reise/2026/11.json blob 8dcd88a8f0f6f6f8d6abe7da67772bdce9df4dd3 is genuine pregame: 683 records, 580 available projections, 103 insufficient-history, all Actual unavailable and ActualScoringEvidenceFinalized=false. Canonical source league rosters.json at same SHA blob bc9eeed6c6912ce86a5093d3069ada7a843e37f3 contains six teams. DecisionWindows from same commit supplies lock/slot facts. These inputs allow as-of W11 direct projected lineup and hybrid experimental replay without current-week outcome leakage. Historical availability v3 product path 404 at this SHA; version/revision availability is a separate feature restriction. Training on earlier historical outcomes must be carefully time-censored; never inject later v3 target-week records. Check archival equivalents W5–10 and freeze a standard cutoff (e.g. 24h before first kickoff) independently of outcomes, multiple kickoff windows if feasible. Reproduce on a full checkout; prospective weeks/seasons must remain untouched for independent superiority test. Only W10–11 has observed win-prob-v1 version, so production comparison remains very small. CP3l and CP3k retrospective metrics are not directly comparable to this cohort.

A first direct projected-lineup experiment using prior archived roster hit empty GitHub contents responses for a large weekly NFL roster JSON; blob read recovered 2025 W4 (1,756,186 chars, 2,548 records). No direct-lineup metrics produced in that attempt; blob fallback available. Prioritize true archive inputs rather than final roster proxy where possible.

## Validation and scope
Real connector reads of all seven pinned forecast and DecisionWindows pairs plus all seven outcome/source pairs succeeded in V8; identity and pre-kickoff checks passed. Brier aggregation recomputed in local Python from observed probabilities. This is a reproducible pinned audit with explicit formulas/inputs, not a checked-in full CLI or independent replay. Direct checkout DNS remains blocked. No production writer/data/contract/consumer/workflow changes; no CI inventory or runner changes. Rollback this research document only. Keep draft and #1451 open.