# G5 League Live · Immutable publication-commit receipt

Date: 2026-11-05. Issue: #1263. State: read-only, separately invoked, **no productive early exit**.

## What this checkpoint proves

The previous audit distinguishes a completed successful League Live run from its starting Git revision. This checkpoint additionally correlates **one explicit, completed and successful League/Standings publisher job** with a concrete Git commit. It does *not* assume that `run.head_sha` was published or that a green job necessarily produced a commit.

Usage (with read-only GitHub Actions and repository access):

```sh
GH_TOKEN=... python3 tools/audit_workflow_job_costs.py --repo Lolindhir/fantasy-app \
  --audit-publication-run-id 41967384414 --publication-stage league
```

This extends the existing opt-in cost/provenance auditor; the command is **not** invoked by the 10-minute League Live workflow. It makes GET-only calls. GitHub's Actions job-log endpoint may redirect to signed storage; its API authorization header is explicitly **not forwarded** across the redirect, only HTTPS is accepted, and the log download is size-bounded.

The witness checks:

1. The requested run is a regular, successful League Live `repository_dispatch` on main, with its required source validation, source sync, standings and league jobs successful in the latest attempt, coherent identities/timestamps, and main descendant-of-run-start evidence.
2. The authenticated GitHub job log for the **exact** successful writer job includes exactly one actual `old..new HEAD -> main` push line adjacent to the expected repository remote and the rebuild-and-retry helper's success message. The shell script as echoed by Actions is not evidence.
3. The abbreviated new SHA resolves via GitHub's commits API to a full immutable SHA whose unique parent matches the old SHA prefix, whose commit author/message indicate the matching `data(league)` or `data(standings)` publisher, whose timestamp fits the job window and whose changed file paths are within the declared broad writer roots.
4. GitHub compare evidence confirms that exact full SHA is an ancestor of the observed main ref; an unrelated or rewritten branch is rejected. A regular generator no-op is **not** a publication commit receipt.

Each positive *per-job* result sets `publicationCommitVerified: true` but **always** `outputsValidated: false`, `timeAndFinalityVerified: false`, `raceFree: false`, `recoveryClean: false`, `safeToSkip: false`, `enforced: false`. Successful completion and one stage's push cannot attest an entire multi-writer run, the state of all Source/Derived/App products, or time/finality boundaries.

## Concrete natural production example

Read-only inspection of [League Live run #41967384414](https://github.com/Lolindhir/fantasy-app/actions/runs/41967384414) found the League writer's Git push line `2dfce6c..5ab7486 HEAD -> main`, directly followed by `Rebuilt generated-data publish succeeded on attempt 1.`. GitHub's commit API independently resolves the published SHA to `5ab7486dc61d6e4274d45a95fca71a5b4bed0bec`, with single parent `2dfce6c20e68986d300250aac9352fbb5e12db38`, author `github-actions@github.com`, timestamp `2026-11-05T04:26:01Z`, and changes to `public/data/FantasyGameContext.json` and `public/data/Timestamps.json`. A GitHub comparison confirmed the commit remains an ancestor of the observed main head. This is a *specific published commit*, not proof that every downstream output in that run was validated or up to date.

In the same run the Standings job logged `Generator produced no repository changes. Nothing to publish.`. It has **no new commit to attest**. The Source Sync writer has a different raw+canonical publication contract and is **not** covered by this initial single-commit parser; it must be audited separately without conflating raw and canonical writes.

## Negative tests and remaining G5 proof requirements

Existing registered Core audit tests now reject an absent/multiple/suspicious push, a wrong repository remote, wrong SHA parent, Git-author/message mismatch, unexpected generated-file roots, impossible time ordering, divergent main ancestry, failed or incomplete run, and a no-op treated as publication. A redirect regression explicitly verifies that the API bearer token is removed before accessing signed log storage.

Remaining:

- A run-level **per-stage receipt ledger** including Source Sync's raw/canonical phases, with a recognized semantic no-op witness tied to a specific revision.
- Revision-bound output validation for all configured leagues and current/future Draft partitions, and stale/fail-soft recovery detection.
- Clock, scoring finality, waiver, transaction and week-transition invalidation.
- Cross-writer/race protection between preflight and any eventual decision.

These are prerequisites for activation, not assumptions or approval. No scheduler, workflow YAML, writer, permissions, generated data or persisted state changes. No additional production run dispatched. Rollback: revert this focused read-only auditor, regression tests and research report.
