# G5: bounded sparse checkout for League Live Source validation

Date: 2026-11-03 UTC. Owning issue: [#1263](https://github.com/Lolindhir/fantasy-app/issues/1263). Earlier baseline: [checkout-variance and cross-run shadow report](2026-11-03-g5-checkout-variance-and-shadow-crossrun.md).

## Objective and observed baseline

The existing ten-minute League Live chain uses reusable `.github/workflows/sync-league-source-data.yml` with `materialization_scope: current`. It first executes the **read-only** `validate` job, then an independent Source `sync` branch writer, then the Standings and League writers. Each executes a fresh Git checkout, and the three writers have existing rebuild/race-safety invariants.

For ten selected successful completed League Live runs (see earlier report), the **Source validate** job's full-tree checkout steps took 34, 36, 35, 85, 88, 85, 38, 122, 38, 39 seconds (range 34–122, median 38.5 sec). Those are GitHub step durations, not end-to-end job time, traffic bytes, billed minutes, or a causal performance estimate. All four checkouts together occupied 3,409 of 4,638 summed runner-job seconds (73.5%). The `data-source` current Git tree contains ~3,755 MB uncompressed tracked blobs including 2,129 MB historical player stats and 557 MB weekly roster history.

## Exact source-validation dependency closure

The **current** materialization scope calls four existing Python test modules (League Core targeting, transaction targeting, transaction window and draft targeting), then the unchanged `python tools/league_source_data.py validate` command.

The required checked-out families are:

- `tools/**`: all source CLI, library imports, test modules, shared Python helpers, and current-scope parity test
- `.github/workflows/**`: workflow-contract test inputs, particularly Source Sync
- `data-meta/**`: *all* manual League bootstraps, metadata, and league-specific configuration
- `data-source/league-registry.json`: canonical dataset registry; cone mode includes root files of `data-source/` as ancestors of selected subdirectories
- `data-source/leagues/**`: *all* canonical League manifests, seasons, transactions, drafts, and matchups
- `data-source/providers/sleeper/**`: current and historical persisted provider League evidence used by scope tests and byte-for-byte parity check
- `data-source/nfl/schedules/**`: official NFL weeks used for current/transaction week resolution
- `data-source/nfl/identities/**`: provider-mapping inputs for actual PlayerMappingResolver parity

Historical `data-source/nfl/player-stats/**` and `data-source/nfl/weekly-rosters/**` are excluded; neither is a live current League source validation input. Other Source materialization scopes, including `full`, keep complete checkout and the original full suite. The Source `sync` writer, Standings and League writers remain independent and keep full checkout.

## Implementation and fail-closed proof

Only the reusable Source workflow's **read-only** `validate` job branches on its existing `MATERIALIZATION_SCOPE`:

- `current`: the existing `actions/checkout@v7` action uses a cone-mode `sparse-checkout` profile for the listed directories. Checkout v7 currently adds a blobless partial-fetch filter for sparse checkouts. Do not set an additional `filter` input: its documented behavior is to **override** sparse-checkout.
- all other modes: the original full `actions/checkout@v7` with no filtering remains unchanged.
- current mode's immediate pre-test guard fails if `core.sparseCheckout`, `remote.origin.partialclonefilter=blob:none`, and 13 essential real persisted paths do not match expectations, or if historical player-stats/weekly-rosters unexpectedly appear in the working tree.
- A **pull_request-only, read-only** job `validate_current_sparse_pr` uses precisely the same sparse profile and guards and executes the current test modules, existing **real persisted** `test_league_source_current_scope` materialization equivalence/no-op parity test, and the source registry validation CLI. Its sole purpose is proving the sparse checkout before merge. The original PR `validate` job still runs the original complete full-source test suite. The new PR job never executes on a scheduled or reusable League Live run.
- Three new regression methods in existing registered Fast module `tools/tests/test_league_source_current_scope.py` enforce both sparse profiles' equality, exact allowed prefix closure, current-only conditional routing, full-mode/full-writer retention, and strict guards. Existing CI inventory and test-impact registration remain unchanged.

This is an **I/O change** to read-only validation only, not any semantic data, publication, service, scheduler, no-op gate or permission change. Missing sparse inputs fail validation; no partial source publication is permitted. Any newly required dependency must be added explicitly to the profile and negative tests, or the checkout restored to full. The PR test parity module must not be silently skipped on missing real fixtures; an explicit file-presence guard enforces this.

## Measurement, gates and rollback

Before merging, inspect exact-PR-head CI Core, Fast League and Merge Gate **and** the existing Source workflow's PR runs: full `validate` success, `validate_current_sparse_pr` success, and `sync` skipped (no source writer during PR). Compare the source validation checkout time in the PR parity job to its full counterpart; these use different GitHub runners and are only indicative. After merge, compare naturally scheduled League Live `source / validate` checkout to the historical 34–122 sec baseline and verify that the whole Source → Standings → League pipeline remains successful. **Do not dispatch an extra full live writer to obtain a benchmark.**

The intended reduction is only the Source validation checkout, at most one of four sequential job checkouts. It does **not** solve the other three publisher checkout costs. Use enough runs to avoid attributing GitHub network variability to this one change. A PR-only same-commit comparison is stronger than a across-day anecdote but is not a controlled runner/network experiment.

Failure or unexpectedly slow sparse behavior warrants reverting the PR's workflow and test/report changes; no canonical data or storage migration is needed. Continue #1263 G5 before any new production gating or Source/Derived ownership changes.
