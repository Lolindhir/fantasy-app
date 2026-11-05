# G5 – Fail-soft recovery observations and pre-check cost feasibility

Date: 2026-11-05. Parent issue: #1263. Checkpoint: narrow **GET-only, offline** producer-status classification. No live early exit, no run dispatch, no new persistent attestation.

## Why green League Live is not recovery proof

`tools/league_live_derived_refresh.py` catches exceptions for LeagueTransactions, LeagueDrafts and TeamWeekPerformance and emits `Status: blocked` while retaining the last good generated product. An unready TWP week can emit `no-scored-week`. These conditions deliberately do not always fail the overall job. Therefore a successful League Live job plus `Generator produced no repository changes` **must not** be interpreted as recovery-clean output or sufficient pre-execution skip evidence.

## Opt-in offline auditor

    GH_TOKEN=... python3 tools/league_live_recovery_audit.py --repo Lolindhir/fantasy-app --run-id 42094886471 --league nfl-reise

Use `--league` for **every** expected canonical league. The set is caller supplied; it is not independently discovered or attested by this tool, and thus does not prove all-league coverage without separate source metadata validation.

The script reuses the existing GitHub Actions API and credential-safe log reader. It verifies the exact successful regular League Live run, current job attempt, all mandatory upstream/Standings/League jobs, checkout-start SHA ancestry to actual main, and a second identical observed main ref during the audit. In the authenticated League job log it then requires exactly one first rebuild attempt (reject retries/ambiguity) and one well-formed source-derived status array. Every expected league must report exactly three distinct current-season products (`league-transactions`, `league-drafts`, `team-week-performance`). Each row must be `changed` or `unchanged`; for TWP the week is positive and PWF parity state must be `verified`. Missing, unexpected, duplicated or `blocked`/`no-scored-week` rows fail closed. A no-change publication marker with a changed Derived status also fails closed.

The result deliberately distinguishes `jobCompletionVerified` and `noBlockedDerivedRowsObserved` from **unproven** `allOutputsValidated`, `publicationCommitVerified`, `recoveryClean`, `raceFree`, `safeToSkip` and `enforced`. A clean producer report is never a complete output-parity attestation and does not verify previous fail-soft outputs, future draft partitions, independent provider freshness or safety after the last ref read.

## Real natural job evidence

Read-only API inspection of [League Live #42094886471](https://github.com/Lolindhir/fantasy-app/actions/runs/42094886471) found a successful League job, one rebuild attempt, three producer rows all `unchanged` and TWP week 8 parity `verified` (177 comparisons), followed by `Generator produced no repository changes. Nothing to publish.` This demonstrates the parser's expected log format, **not** a claim that the newly added authenticated CLI was itself executed. A different successful run could still contain `blocked` fail-soft rows and retain stale files. The current tool must reject such cases.

## Observed job/runtime budget (six natural successful ticks)

Direct independent GitHub Actions jobs API measurements for runs 42096456147, 42094886471, 42093327958, 42091695583, 42090097453 and 42088460708:

| Stage | Median wall clock | Median checkout step | Median non-checkout residual (approx.) |
|---|---:|---:|---:|
| Source Validate | 13 s | 4 s | 8 s |
| Source Sync | 59 s | 43 s | 15 s |
| Standings | 51 s | 43 s | 8 s |
| League | 104 s | 42 s | 62 s |

The medians are stage-level descriptive statistics, not a paired estimate of per-run savings. Job timing includes setup/cleanup, wall-clock variability and sequential dependency waits not fully captured by step medians. A naive full-checkout-based preflight on every 10-minute tick could cost as much as the Standings job itself; **do not deploy these offline GET/log checks into the hot path**. An eventual production gate would need a cheap, independently measured, revision-pinned preflight and a correct race/rollback proof.

## Remaining activation blockers and decision

1. The **complete published-output state** at an immutable revision, including dynamic future Drafts, transaction products and any prior fail-soft TWP partition, is still not independently attested for a given successful run. A positive derived producer report alone is insufficient.
2. The existing job-level GitHub concurrency prevents overlapping League Live ticks, but does not establish an atomic compare-and-skip with unrelated writers (NFL Live, standings, source/back-office, deploy, other Derived). Reading `refs/heads/main` twice is only an observation; another writer may publish immediately afterward.
3. Provider freshness, NFL scoring/finality and clock/waiver transitions require independent invalidation evidence beyond input-tree equality. A time cap is not a freshness guarantee.
4. A future fast path must prove **net wall-clock savings after including the gate**, not just another correct audit. An economical precheck cannot be assumed to be safe simply because it is faster.

Recommendation: do not activate a real early exit at this checkpoint. The next distinct work package should design a genuinely atomic publisher/lease/compare-and-swap boundary and revision-bound output receipt, with targeted impact/rollback and permission review **before** modifying any production writer or scheduler.

## Validation and rollback

Regression tests in the existing Core-registered `tools/tests/test_audit_workflow_job_costs.py` cover successful producer reports, missing/duplicate/malformed statuses, history/TWP blocked, no-scored-week, non-verified TWP parity, retries, impossible no-op markers, failed/in-progress run, omitted/skipped League job, a main ref advance during the read and missing credentials. No Deep tests are introduced. Roll back by reverting this scoped PR: one read-only script, the registered test module and this historical report; existing Source, Derived and App products and all workflows/permissions remain unchanged.