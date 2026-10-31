# Issue #1236 — fantasy-relevante GamesPlayed: Historical impact audit

**Evidence snapshot:** 2026-10-31. **State:** read-only validation; no published regeneration. Owning Issue [#1236](https://github.com/Lolindhir/fantasy-app/issues/1236), implementation [Draft PR #1251](https://github.com/Lolindhir/fantasy-app/pull/1251).

## Domain decision

Non-kickers count one `GamesPlayed` per final regular-season player-week **if OffenseSnaps > 0 OR actual league-scored FantasyPoints != 0** (positive or negative). An offensive zero-point appearance counts; a scoreless special-teams-only appearance does not. K remains kick-attempt-based. FantasyPointsTotal includes all scored points from counted weeks. The same denominator feeds current and historical `AvgGame`, salary inputs, and public `FantasyPointsAvgGame`. No second NFL-games counter. **salary-v1 and salary-cap-v1 formula/parameters stay unchanged**; PlayerValuation `ContractVersion` becomes 3 due to changed input semantics.

## Method and source

- CI [#1790](https://github.com/Lolindhir/fantasy-app/actions/runs/41234060349) and [#1793](https://github.com/Lolindhir/fantasy-app/actions/runs/41234664840): read-only `derived_data.materialize_player_valuation` into a temporary directory, exact comparison with persisted `data-derived/player-valuation/nfl-reise/<season>/week-<NN>.json` ContractVersion-2 baselines, one latest as-of regular-season snapshot for each manifest season (2024, 2025, 2026).
- Same production salary and cap model modules are used on both sides. History inputs include the snapshot season and prior three years, so 2023 is covered by 2026 `SeasonMinus3`; 2021/2022 are in the oldest 2024/2025 salary windows.
- Separately simulate verified **unowned** PFR `WhitCo05` offensive-snap facts from canonical `data-source/nfl/snap-counts/<year>/<week>.json` for Cody White `NFLP-caf7c3d6786fcd72e704`, in memory only. Recompute PlayerValuation with this controlled input while preserving scored points, source roster, bye weeks, and models. **This scenario is not a replacement for a full Source rebuild or publication.**

## Exact scoring-policy impact, before PFR source repair

| PlayerValuation snapshot | Population | Salary changed | SalaryProjected changed | Current GamesPlayed changed | Current points changed | SalaryCap Δ | SalaryCapProjected Δ |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2024 W17 | 887 | 12 | 12 | 9 | 9 | $0 | $0 |
| 2025 W17 | 880 | 10 | 15 | 11 | 11 | $0 | $0 |
| 2026 W07 | 956 | 13 | 11 | 5 | 5 | $0 | $0 |

In the **2026 snapshot's historical inputs**, 11 players change in 2025 (`SeasonMinus1`), 8 in 2024 (`SeasonMinus2`), and 3 in 2023 (`SeasonMinus3`). Historical scored-week inclusion explains why prior-season Salary values move even where the current-year participation predicate remains unchanged.

## Cody White source identity scenario

Identity evidence: [Pro-Football-Reference `WhitCo05`](https://www.pro-football-reference.com/players/W/WhitCo05.htm) and [PFF `61448`](https://www.pff.com/nfl/players/cody-white/61448), cross-checked against the canonical GSIS `00-0035891`/PFF `61448` player and previously unresolved PFR snap row(s). Reviewed source adjudication ID `2026-pfr-whitco05-cody-white` in the draft PR.

| Snapshot | Current Cody GamesPlayed | Salary Δ from PFR snap correction | SalaryProjected Δ from PFR snap correction | Cap Δ |
|---|---|---:|---:|---:|
| 2024 W17 | 1 → 4 | −$120,545 | −$1,009,750 | $0 |
| 2025 W17 | 3 → 9 | −$1,009,750 | −$1,066,274 | $0 |
| 2026 W07 | 5 → 7 | −$1,066,274 | −$1,275,384 | $0 |

These PFR snap deltas are relative to the **already corrected v3 scoring** (not the old v2 published snapshot). Combining both changes, Cody's **2026 total salary change versus published v2** is **+$185,035**, and **2026 SalaryProjected change is +$1,742,222**. The 2026 scoring-policy-only correction had raised his SalaryProjected by $3,017,606; the two additional offensive appearances then reduce it by $1,275,384. Top-N cap stays unchanged in both read-only steps.

The raw PFR evidence also includes older 2021 and 2022 offensive games. Replay must preserve regular-season/week bounds; for example, 2021 W18 is not part of a 17-week league regular-season Salary history.

## Safety and validation

- Scored-only weeks with positive **or negative** points are counted; scoreless ST-only weeks are intentionally excluded. Dylan Sampson's scoreless ST-only week does not alter his salary-game denominator.
- Current and historical salary input semantics are consistently changed; `salary-v1` behavior is immutable. The prior v2 snapshots remain reproducible as stored historical evidence, but a v3 regeneration is a deliberate contract-semantic migration.
- The one-off complete multi-season and PFR in-memory impact audit was run under existing CI **only temporarily**. It was removed from the normal Fast suite after collecting this evidence to preserve CI runtime. The permanent Fast regression instead verifies corrected scratch v3 points against final persisted current-season PWF points, plus existing synthetic scoring and Source identity tests.
- Source full builder/raw snap materialization and rollout are tracked in the Issue; the draft PR must not be treated as a productive data correction until the identity replay, matching regenerated snap rows, strict parity, and controlled classified Source→Derived→Players publication are actually verified.
- **Rollback:** before activation, discard the PR branch. After activation, reverting only the adjudication/code is **not sufficient to undo the canonical PFR identity association**, because the identity builder reuses persisted provider IDs. A Source-owned, explicitly reviewed reversal/reconciliation must first remove the exact current-season PFR claim without harming other players or historical provenance, then rerun the existing classified Source → Derived → Players/League producers with verified parity. Do not hand-edit generated identities, snap counts, or consumer JSON. This rollback and a safe staged activation order remain unresolved at the draft PR handoff.

**Limit:** values above use one final as-of snapshot per league season, not every weekly snapshot; no generated file, workflow, permission, or output path was changed by these read-only calculations.
