# G5: Revision-bound historical League full-refresh witness audit

Date: 2026-11-05 · Parent #1263 · offline-only, read-only, no production Early Exit.

## Discovery and existing owner

The source-owned script tools/league_source_refresh_witness.py already records full-acquisition witnesses under data-source/_sync/league-refresh-witnesses/{league}/{season}-week-{week}.json. Only a fully successful full Sleeper acquisition, subsequent canonical materialization, and an idempotent second semantic pass may mint this file. Current-scope ten-minute League Live runs **do not mint** a full refresh witness. Its payload contains canonical league/season/provider identity, NFL finality fingerprint, ordered SHA-256 hashes of relevant provider and canonical inputs, and SucceededAtUtc. Identical subsequent full refreshes deliberately do not rewrite this file (no heartbeat).

Observed natural evidence: nfl-reise 2026 week 08 persisted full witness with SucceededAtUtc 2026-11-05T03:37:20.348919Z, 18 input file hashes, and an existing NFL-finality fingerprint. This is historical **week-8 coverage**, not evidence that current/future week 9 or newly published market/scoring inputs require no update.

## New optional audit and exact meaning

Use a clean, ordinary repository checkout (do not dispatch a workflow):

    python3 tools/league_full_refresh_witness_audit.py --repo-root . --league nfl-reise --max-age-hours 24

The audit is read-only and calls the **existing** source owner's prepare(), _inputs() and _digest() routines. It validates:

1. Root is exactly a Git repository root at a 40-character HEAD SHA and the entire worktree, including untracked paths, is clean; witness, all referenced raw/canonical files and finality source are Git-tracked.
2. The current finalized-week candidate, canonical league/season/provider identity, unique finality row and fingerprint recompute to exactly the witness identity; no future/other week assumption is hardcoded.
3. Actual raw acquisition metadata is validated against payload SHA-256 by the original source-owned input function; every exact input path/hash matches the saved witness and its full-input fingerprint.
4. Scope must be full, schema and fields exact, and witness timestamp must not be in the future or older than the **user-selected historical audit age bound**. This cap is only an observation policy, NOT a production TTL or a guarantee of freshness.

A successful result is limited to historical full-week content on an exact immutable **observed repository revision**, with flags sourceWitnessVerified=true, contentRevisionVerified=true, observedAgeBoundVerified=true. Even a success ALWAYS includes providerFreshnessVerified=false, currentScopeNoOpVerified=false, lastSuccessfulRunVerified=false, outputsValidated=false, timeAndFinalityVerified=false, raceFree=false, recoveryClean=false, safeToSkip=false, enforced=false.

This audit does **not** establish that a particular GitHub run authored the full witness; SucceededAtUtc is not run identity. It does not fetch live Sleeper data, recompute derived consumer outputs, assess market/waiver/week boundary invalidation, enforce cross-writer isolation, or skip any job.

## Negative cases and safety

The existing registered Source witness regression test suite now checks: positive pinned historical full week; no witness/mismatched league; dirty or untracked Git state; committed changed canonical bytes, raw provider metadata, or NFL finality; invalid scope, edited witness input list/fingerprint, future-dated timestamp; exceeded bounded age and malformed/naive clocks. All failures remain fail closed with no product mutation or dispatch.

Changed files: one new offline tool, an extension to the existing registered tests, and this historical evidence report. No workflow or scheduler YAML, writer/retry/permission/branch policy, Source/Derived/App product, or generated data was modified. Rollback: revert this narrow PR.

## Next gate before genuine Early Exits

A robust per-run and per-branch publication/no-op proof still requires a verified **current-scope acquisition outcome** pinned to a successful run and git revision; an old full-week witness cannot substitute for that. The eventual gate also needs time-sensitive finality/week/waiver/transactions, all model/Derived dependencies, validated output partitions, and branch-race/recovery atomicity. A separate targeted activation authorization/review is mandatory for any live skip.
