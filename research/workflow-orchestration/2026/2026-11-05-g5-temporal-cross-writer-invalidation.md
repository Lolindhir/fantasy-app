# G5: Temporal and cross-writer invalidation audit (offline only)

Date: 2026-11-05. Parent: #1263. Scope: a bounded offline source/consumer temporal and revision change detection checkpoint, **no new live early exit**.

## Existing canonical owner and real dependencies

League lifecycle already has a canonical pure model with explicit time input: tools/derived_data_lib/league_lifecycle.py resolves the selected per-season model from data-meta, canonical League Source, the persisted Drafts product, NFL schedule/game finality, week-finality, and CapDeadline. tools/derived_data_lib/models/lifecycle/v1.py exposes Status/Phase/NextWaiverRun and Boundaries (SeasonWindowStart, CapWindowEnd, NextWaiverRun) and carries explicit warnings for unsupported waiver modes or DST ambiguity. We **reuse** it. We do not recreate Sleeper's waiver calendar or game kickoff parsing. tools/league_live_shadow_gate.py already declares conservative Standings and League input-root dependencies, including Source, Derived, App outputs and generator code. We reuse this inventory too.

## Optional study command

    python3 tools/league_live_invalidation_audit.py --repo-root . --league nfl-reise --season 2026 --stage league --previous-sha <40-character Git SHA> --from-utc 2026-11-05T18:52:00Z --to-utc 2026-11-05T19:02:00Z

The script performs only local Git and source/derived reads: no network, API mutation, workflow dispatch, writer, scheduler or persistent evidence. It requires an exact clean repository HEAD, a verified ancestor baseline SHA and no observed HEAD movement while auditing. It obtains canonical lifecycle facts once and evaluates the **same fact snapshot** at the two supplied instants.

For temporal coverage, it conservatively rejects any game kickoff in the open/closed interval (earlier, later], any *nonfinal game that has already started* at the later instant, any nonfinal game with an unknown kickoff, any canonical lifecycle boundary in the interval (CapWindowEnd, SeasonWindowStart, NextWaiverRun), unavailable current waiver schedule with WaiversOpen, lifecycle warnings/DST uncertainty, changed lifecycle projection, missing/invalid clocks or an observation window longer than 60 minutes (an offline audit bound, **not** a production TTL). Crucially, both endpoint lifecycle states can be equal while a kickoff/waiver event occurred between them.

Cross-writer invalidation compares exact Git subtree hashes at the supplied baseline and observed current HEAD for every root the existing League/Standings shadow observer declares. A changed data-derived or public/data root invalidates unchanged-input claims even when Source did not change. Root list and identity are required to match exactly; missing, malformed or unsupported roots fail closed.

## Validated limits

A result with knownClockWindowClear=true means **no known canonical event** was detected in the selected window under one static checked-out snapshot. dependencyTreesUnchanged=true means **the observed baseline/current Git dependencies were byte-for-byte identical**, not that providers or future writers cannot change. Unknown and API-independent events remain external risks. The probe cannot verify live Sleeper source freshness, future NFL scoring/finality polling, unobserved waiver/trade processing, all Derived/App output readiness, fail-soft recovery, a previous successful publication or an atomic race-free production preflight.

Regardless of result the output always includes independentProviderFreshnessVerified=false, independentNflFinalityVerified=false, allSourceDerivedAppOutputsValidated=false, timeAndFinalityVerified=false, raceFree=false, recoveryClean=false, safeToSkip=false, enforced=false. No productive change or permission to skip jobs is granted.

## Negative regression matrix

The registered League lifecycle Fast test module adds specific cases for: a quiet 10-minute clock window; kickoff crossing despite matching Status endpoints; scheduled waiver processing; cap-end and season-window crossings; unsupported waiver mode/DST warning; already-started nonfinal NFL game; missing kickoff; reversed/naive/too-long clock windows; changed Shared Derived and App subtrees; missing/malformed Git subtree IDs; invalid baseline identity. The existing v1 lifecycle implementation and consumer publication rules are not modified.

Rollback: revert this narrow PR (one new read-only script, tests in existing registered tools/tests/test_league_lifecycle.py, this historical report). Before any real League Live skip, independently attest current provider/finality freshness, previous complete publication with exact output partition coverage, robust cross-workflow compare-and-swap/race isolation and fail-soft recovery; run a separate targeted impact+rollback review and obtain authorization.