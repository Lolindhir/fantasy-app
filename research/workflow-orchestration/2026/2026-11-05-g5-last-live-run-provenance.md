# G5 · Last League Live run provenance (read-only)

Date: 2026-11-05 · Parent: #1263 · Scope: one bounded **offline audit**, no live skip.

## Purpose and method

Separate **independently verified GitHub Actions completion** from **publication-commit identity** and **safe-to-skip**. `run.head_sha` records the workflow start revision and is *not* the generated data commit that may be published later during the Source/Standings/League rebuild-and-retry jobs.

Use the existing manually invoked, read-only GitHub API tool:

```sh
GH_TOKEN=... python3 tools/audit_workflow_job_costs.py --repo Lolindhir/fantasy-app --audit-latest-league-live
```

The tool makes GET-only calls through the already existing API client. It queries the **latest unfiltered** League Live workflow run, including in-progress or failed runs, rather than cherry-picking an older success. It retrieves **all available job attempts** and verifies the latest attempt for the four required jobs: `source / validate`, `source / sync`, `standings`, and `league`. Legitimate PR-only / historical-preflight skips are not treated as failures.

It separately reads the actual `refs/heads/main` GitHub ref and Git compare evidence showing the run-start SHA to be an ancestor of the observed branch head. The compare result must identify the **exact** observed main SHA, not merely any descendant. Missing, truncated or inconsistent API evidence fails closed. An older failed job attempt does not supersede a successful latest attempt, and a latest failed/in-progress workflow cannot be replaced with a preceding successful one.

The result reports `jobCompletionVerified: true` **only** if all identity, attempt, job, time and ancestry checks succeed. It reports `mainAdvancedSinceRunStart` separately. It always sets `publicationCommitVerified: false`, `outputsValidated: false`, `timeAndFinalityVerified: false`, `raceFree: false`, `recoveryClean: false`, `safeToSkip: false`, `enforced: false`.

## Observed natural run

Direct GitHub API inspection (not a newly dispatched workflow) found League Live run [#41966328830](https://github.com/Lolindhir/fantasy-app/actions/runs/41966328830), starting 2026-11-05 04:12:13 UTC, completed successfully at 04:16:01 UTC; four required jobs completed successfully. Its run-start SHA `2d0fa7387b6191ff80d7d4eed281f1b22fd10009` was a strict ancestor of the subsequently observed main SHA `59a6d3f76656d3abd918b69838795a2f63763fb0`. This supports the distinction: **successful execution on a start revision does not prove which commit the publisher produced**. The audit does not claim a live no-op or completed output receipt for that run. Any later latest run takes precedence.

## Negative coverage / remaining prerequisites

The existing `tools/tests/test_audit_workflow_job_costs.py` Fast/registered audit tests now include successful latest-attempt evidence, a newer failed run, incomplete runs, wrong workflow/repository/branch, missing or skipped required job, duplicate jobs, mismatched `run_id` or `run_attempt`, timestamp violations, missing job pagination, invalid branch ref, divergent/ref-mismatched main SHA, and explicitly non-enforced output. All tests are synthetic fail-closed scenarios; the proof cannot be elevated to live gating on their strength alone.

Still **not proven**, and therefore prohibited as an actual skip prerequisite:

1. The immutable, successfully published **output commit** or validated same-revision semantic no-op tied to the observed run.
2. Complete Source→Derived→App output and dynamically configured future-draft content parity **at that publication revision**, for every current league.
3. Clock/week/finality/waiver validity and any source-independent change since that run.
4. Cross-workflow revisions between a preflight observation and a possible skip, including branch races and recovery from fail-soft retained output.

No workflow YAML, scheduler, generated data, publication class, writer scope, credentials, or productive job behavior is changed. The existing 7-/30-day cost census CLI remains available with its original `--start` and `--end` arguments. The new mode is opt-in only. Rollback: revert this report, existing tool and existing test updates. The Issue #1263 platform target remains open.
