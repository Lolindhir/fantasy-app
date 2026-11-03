# NFL Games: read-only Source → Derived → current App snapshot

- **Issue:** #1263, G1/G6 freshness evidence.
- **Observed:** 2026-11-03; `main` data files read through GitHub, no writes or live workflow dispatch.
- **Status:** bounded snapshot parity **verified**; event-to-event freshness, restore in production and full consumer reachability **not verified**.

## Exact evidence set (Git blob IDs)

| Input/output | Path (repository-relative) | Git blob SHA |
| --- | --- | --- |
| Canonical schedules | `data-source/nfl/schedules/2026.json` | `26dda029644b7b67025f3642f030f98e51b7e6ef` |
| Canonical game finality | `data-source/nfl/game-finality/2026.json` | `8991aea1de5b2ab02d93a3e1418c5b13cda95f47` |
| Canonical schedule odds | `data-source/nfl/schedule-odds/2026.json` | `1d680e73cad83869dfee83c045a3307d06e65ee5` |
| NFL Games Shared Derived | `data-derived/nfl-games/2026.json` | `2b727069533ca2e653fc4f498e2ab720a8652d1b` |
| App Schedule bridge | `public/data/Schedule.json` | `7fe026c249f8fe65f1867237b6f4057a0b3b962d` |
| Current App game context | `public/data/FantasyGameContext.json` | `d30220c6c8144bc0ac4c310bea7c9742142e8af8` |

## Method and result

Fetched the six JSON blobs without mutation. Indexed the three Source `Games` collections and the Derived `Games` by canonical `GameID`; checked that their `GameID` sets are identical and that each game has matching `GameType` and `Week`. Compared Derived `GameDay`, `GameTime`, home/away teams and scores against Source Schedule, `Final` against Source Finality, and `SpreadLine` and `TotalLine` against Source Odds (including nulls). Checked the two market implied-points values against `(TotalLine - SpreadLine)/2` and `(TotalLine + SpreadLine)/2`, rounded to two decimal places for complete lines.

**Result: 272/272 games found in all four collections, zero unmatched canonical IDs, and zero observed identity, finality, score or market-value mismatches.** This is direct blob equality of the enumerated fields, not a runtime rebuild comparison.

The published `FantasyGameContext.json` has `Season=2026`, `Week=9` and 15 games. Joined each context `GameID` to `Schedule.json.gameID`, then to Derived via `Schedule.CanonicalGameID`. **15/15 current-week context games had market values identical to the Derived market fields, with zero missing bridges or mismatches.** This proves consistency of the *observed* published App market adaptation, not freshness after the next upstream write.

## Existing code contracts and remaining boundary

- `tools/nfl_games_materialize.py` is read-only by default, writes only with `--write`, and skips byte-identical materialization. The existing `tools/tests/test_nfl_games_real_source_restore.py` exercises clean-root restoration and a repeat-build no-op from real canonical season data in CI; its success was reported in the preceding #1263 PR #1308 checks. This audit **did not** rerun materialization locally or dispatch a live publisher.
- `.github/workflows/sync-nfl-source-data.yml::nfl_games_derived` publishes after a successful complete source sync or delegated scoped schedule-odds sync, but not standalone NFL-live game-finality. `tools/derived_data_lib/fantasy_game_context.py::resolve_current_context` loads the season partition if present; `add_market_context` checks schema, season and game identity, not a current source-revision fingerprint.
- The Derived schema does **not** expose a source-content hash or published-source revision, and the consumer therefore cannot prove by contract alone that its optional market fields represent the latest odds revision. Even though the captured six blobs agree, there can be a timing window between upstream source publication, dependent Derived publication and League Live App publication.
- **Not accepted by this evidence:** publisher-specific actual wall-clock lag, in-flight revision races, price-only observation freshness, historical App market parity, complete angular caller reachability, real live no-op commit count, or recovery from an interrupted publisher.

## Proposed next evidence (no architecture activation)

Compare the exact Source→Derived→App blob revisions before and after an observed *normal* scoped odds publication and subsequent League Live run, using existing workflow run histories and committed payloads. Keep the real-source clean-root restore test separate from this time-ordered publication observation; do not introduce a parallel writer, source owner or new data contract without independent review.
