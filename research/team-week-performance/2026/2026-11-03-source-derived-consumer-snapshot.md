# TeamWeekPerformance: read-only canonical league → Derived → WeeklyRecaps snapshot

- **Issue:** #1263, G1/G6 freshness and consumer evidence.
- **Observed:** 2026-11-03; eight canonically scored weeks of `nfl-reise` season 2026.
- **Status:** bounded current snapshot parity **verified**; source-correction invalidation, retained-stale recovery and live producer/no-op history **not verified**.

## Evidence set

| Role | Path / range | Git blob SHA |
| --- | --- | --- |
| NFL week finality | `data-source/nfl/game-finality/2026.json` | `8991aea1de5b2ab02d93a3e1418c5b13cda95f47` |
| Current published recaps | `public/data/WeeklyRecaps.json` | `2796bb14e595511dc1a118fb6b9d473ae6c8e19b` |
| League matchup Source | `data-source/leagues/nfl-reise/seasons/2026/matchups/week-{1..8}.json` | Individual week blob IDs below |
| Shared Derived product | `data-derived/team-week-performance/nfl-reise/2026/{01..08}.json` | Individual week blob IDs below |

| Week | Canonical matchup Source blob SHA | TeamWeekPerformance blob SHA |
| --- | --- | --- |
| 1 | `69434003f21515049d75a8c5929a7ee416925f42` | `141372b42b6d3046aee68b53f38b2d8d1b9bb5f8` |
| 2 | `38898c843984b2c2e7b4025c05196ae5eaa7e1c5` | `91fd479bea1a2f4aa008bb7927dabb1185c28e25` |
| 3 | `cc8486568e73ee68d32fe6e4386eedff836b9d85` | `400f49b61f7cfb0f514856f1130d1bdf82040c7a` |
| 4 | `8fedffdc40d52e7bca8b6045f10d3c6ee536219f` | `bc35e3f773cc12a33f47acb6107da2b43cb2883f` |
| 5 | `49efecc325cb8557e98636546d72d9e67d8932f3` | `9580864ec8c9b0b8df5a8b40aaa29539e703b119` |
| 6 | `ea19cc4160152c81f3ac43a234044e54eea5a5cf` | `68bd69218af973297d316052f2b6ee56dc89576a` |
| 7 | `cbb9f8c10c0775c107f4b38a64792aab776501fe` | `51c231c89050791f545961436f0800926fd624a1` |
| 8 | `54a5d42b961451113e5865bde2ff3f02199b4969` | `82c308f60f446e5517753f910a43bc99f03c6aad` |

## Method and result

Fetched each Source matchup partition, matching Shared Derived TWP partition and `WeeklyRecaps.json` from GitHub, read-only. Matched each team by `CanonicalLeagueRosterID`; compared `TeamWeekPerformance.Teams[].OfficialMatchupPoints` against the corresponding canonical `matchups/week-N.json[].Points`. Checked that each Source/Derived partition contains the same six roster IDs and exactly six team records. Compared `Awards.BestManagerRosterIDs` and `Awards.BestCoachRosterIDs` in each Derived partition with the `CanonicalLeagueRosterID` values in the App `Weeks[].TeamAwards.BestManager` / `BestCoach` arrays (order-insensitive).

**Result: 8/8 tested weeks, 48/48 official team score comparisons and all 16 manager/coach award-set comparisons agree.** All eight App week-award entries report `State=available`. The canonical `game-finality/2026.json` `Weeks` records report `REG` weeks 1–8 `WeekFinal=true`, whereas week 9 is not final at the observed snapshot. Each TWP partition declares the expected week `FinalityEvidence` token. No live refresh or rebuild was initiated.

## Existing code contracts and remaining boundary

- `tools/team_week_performance.py::save_team_week_performance` compares serialized bytes to retain a semantic no-op. `tools/team_week_performance_materialize.py::materialize_all_finalized` preflights all selected weeks, aborting batch writes when any selected week is blocked.
- `.github/workflows/league-live.yml` invokes `league_live_derived_refresh.py` before `weekly_recaps_app_publish.py`. The live refresh attempts newest scored-week TWP and is intentionally **fail-soft** on missing/unready evidence: it warns and can retain an older Derived file. The separately scoped `.github/workflows/update-standings.yml::historical_twp` performs the weekly all-finalized backfill.
- `tools/derived_data_lib/weekly_recaps.py::team_awards` checks the Derived contract version, league/season/week identity, exact named finality token, nonempty `LineupDefinitionHash` and `ScoringProfile.SettingsHash`, and roster/winner joins. It does **not** verify that those stored hashes match the *current* upstream league-settings/roster Source revisions. The Derived product does not carry a complete upstream content revision marker for this consumer boundary.
- **Not accepted by this evidence:** fresh recomputation from corrected historical points or league settings; equivalence of Source scoring configuration hash at publication time; delayed weekly recovery after a blocked League Live refresh; observed repeated no-op production commits; full historical restore after an actual Source correction; reproducibility of the optimal lineup calculation (this snapshot compares published awards and official scores, not re-solving the lineup optimizer).

## Proposed next evidence (no new writer)

Observe a normal League Live and historical-TWP run crossing a finalized week boundary and record the exact changed Source/Derived/App blobs, warnings and subsequent no-op. For a controlled correction, first use the existing read-only historical preflight/restore path with separately staged Source and Derived directories rather than changing real production Source. A source-version freshness mechanism or changed stale-consumer behavior would be an architectural change and requires targeted review, not an inference from this snapshot.
