# G5 – Current-scope Source no-op bound to a Git revision

Date: 2026-11-05 · Owner: #1263 · offline, read-only, non-enforcing.

## Background

The earlier Source receipts verified two separate publisher commits, and the historical full-week witness covered previously finalized weeks. Neither proved an ordinary ten-minute **current** Source Sync zero-change result at the Git revision actually checked out by the source writer.

## New optional audit

Run with read-only GitHub API permissions:

    GH_TOKEN=... python3 tools/league_current_noop_audit.py --repo Lolindhir/fantasy-app --run-id 42088460708

Existing GitHub API run/job and safe log-fetch infrastructure is reused. The tool verifies the requested successful run and source job. It parses exactly three real timestamped producer JSON results from the authenticated job log: raw acquisition, canonical materialization and second semantic no-op pass. It requires positive partition/file counts, zero RawFilesChanged/MetadataFilesChanged/CanonicalFilesChanged counts, equivalent successive canonical results, consistent league/provider/current-week/draft/transaction scopes, exactly one attempt, two identical reset revisions, no actual push and exactly one no-change completion marker. Ambiguous/retried/incomplete evidence fails closed.

GitHub resolves the reset's abbreviated SHA to a full commit. The audit independently compares the source revision and observed main revision using immutable root Git trees (data-source, data-meta, tools, .ai-context, .github, public). It also rereads main to reject an observed concurrent branch advance. A historical zero-change result and **currentMainInputTreesUnchanged** are *separate evidence fields*.

## Empirical evidence

Natural League Live run #42088460708 (2026-11-05 18:52 UTC) had one attempt, two reset lines at 469977a, raw 16 partitions and zero raw/metadata changes, then canonical 9 files with zero changes in both passes, and a canonical no-change message. The source job made no push. See https://github.com/Lolindhir/fantasy-app/actions/runs/42088460708.

Run #42090097453 did push Raw and Canonical commits, so it is a negative real-world counterexample to blanket no-op classification. The standalone CLI has not been invoked with a live authenticated local environment in this chat; only the source job logs and relevant GitHub repository APIs were inspected directly.

## Exact limits

On success, reportedNoOpAtSourceRevisionVerified=true proves a **producer-reported zero-change execution at a resolved Git commit**, not independent replay of a real-time Sleeper response. Main input-root tree equality confirms only those repository root contents at observation time. It cannot prove later provider freshness, NFL week/finality or waiver boundaries, cross-workflow changes in every shared data product, or race/recovery atomicity.

Even on success, independentProviderFreshnessVerified, independentCanonicalReplayVerified, allSourceDerivedAppOutputsValidated, timeAndFinalityVerified, raceFree, recoveryClean, safeToSkip and enforced remain false. This is NOT a production skip authorization or TTL.

Registered tests extend existing tools/tests/test_audit_workflow_job_costs.py with positive and fail-closed cases: raw/canonical changes, second-pass drift, malformed result, wrong scope, retry, diverged reset, unexpected push, missing/failed jobs, moving main ref and absent API credentials.

No changes to existing production workflow, schedule, writers, Source/Derived/App output, identity contract, permissions or stored attestations. Rollback: revert this scoped PR (standalone audit, existing test file, this report). Next step is current-scope upstream freshness/completeness, time/finality/waiver invalidation and remaining cross-writer/race/recovery proof prior to a separately authorized live skip.