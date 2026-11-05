# G5: League Source two-phase receipt and no-op evidence boundary

Date: 2026-11-05. Owner: #1263. **Offline only**. This is a bounded source-publishing proof, not a new writer, scheduler, production gate, or persistent attestation.

## Source of truth and actual publication semantics

`.github/workflows/sync-league-source-data.yml` has a `sync` writer which executes within the ten-minute League Live reusable workflow or as a direct source-sync workflow. It first fetches source provider data and, if staged changes exist, commits and pushes **Raw Sleeper source**. Next it resets to latest main and materializes **Canonical League Source**, including a strict second semantic no-op pass. The canonical phase commits/pushes only when it detects changes. Each publisher may encounter a branch race; rebuild-and-retry is authoritative. A failed source fetch/materialization can also write a failure diagnostic and exit nonzero; a successful raw push alone never means the canonical phase succeeded.

The first source writer has different log and commit authorship from `tools/rebuild_and_publish.py`'s League/Standings publisher. We therefore **do not** reuse that single-commit regex or assume `run.head_sha` is a published commit.

## Implementation

Standalone **GET-only** auditor:

```sh
GH_TOKEN=... python3 tools/league_source_receipt_audit.py \
  --repo Lolindhir/fantasy-app --run-id 41962202248
```

The tool reuses the existing credential-safe GitHub API/Actions-log reader, reads the explicitly requested successful Source Sync or League Live run and the full current job-attempt list, checks required validation and sync success and observed main ancestry, then parses the **actual** (not shell-echo) GitHub job log. It binds at most one Raw and one Canonical push to their preceding `[main <short-SHA>] data(league-source): <phase>` commit output and the exact repository remote. Repeated source publishing attempts, ambiguous/missing commit markers, conflicting no-op observations and incomplete current runs fail closed.

For each detected phase, GitHub's commit API verifies the full SHA, unique previous parent, phase-specific commit message and bot author, commit time inside that exact job, constrained changed-path roots and intact ancestry to the observed main ref. A positive `sourcePublishChainVerified` additionally requires the **Canonical commit's parent to equal the verified Raw commit SHA**. Receipt checks do **not** validate the generator's complete data semantics, all eventual source products, freshness, or the next scheduled boundary.

## Real independently inspected examples

[Source Sync run #41962202248](https://github.com/Lolindhir/fantasy-app/actions/runs/41962202248) (regular dispatch, 2026-11-05 03:32 UTC) successfully published both phases:

| Stage | GitHub log evidence | Independently inspected Git commit |
| --- | --- | --- |
| Raw | `4454dcf..8c8bb71 HEAD -> main` | `8c8bb7159399170d4ae187b6923439a8f7d0daf9`, parent `4454dcf30e...`, 18 provider-source files |
| Canonical | `8c8bb71..3fc5691 HEAD -> main`, explicit canonical publish success | `3fc5691db879604c02ba0ff663d794abf771278c`, parent exact Raw SHA, ten canonical/refresh-witness files |

The commit metadata show the source bot author (`github-actions[bot]`) and published paths within the expected Source roots. The chain still exists on main. The above is a real GitHub observation; the new CLI's full network mode is not claimed to have been executed in this chat.

By contrast, recent ten-minute League Live `source / sync` jobs such as #41971443028 (05:02 UTC) ended successfully with `No canonical League data-source changes detected.` and **no raw/canonical push in the captured job log**. This is an *observed* no-change message, **not** independently proven semantic no-op or permission for a skipped run.

## Explicit fail-closed distinctions

- **Raw without a matching successful push:** `no-push-observed`. The current workflow emits no mandatory Raw no-op attestation. Absence of a push line is not proof of unchanged provider input.
- **Canonical without a push but with exactly one success log marker:** `no-op-observed`; log text is not a revision-bound output parity attestation.
- **Raw-only publish:** Raw commit may be correlated, but the Canonical phase has no commit and therefore the **complete two-commit chain is not verified**.
- **Both phases published:** independently correlate both immutable commits, enforce exact Raw→Canonical parent chain. Do not treat a successful job as data quality or safe-to-skip evidence.
- **Retry/branch race, missing job, failed validation, unknown author, truncated commit files, unexpected changed path, overwritten/diverged main or contradictory logs:** fail closed, never infer skipped work.

Every result sets `rawNoOpVerified:false`, `canonicalNoOpVerified:false`, `outputsValidated:false`, `timeAndFinalityVerified:false`, `raceFree:false`, `recoveryClean:false`, `safeToSkip:false`, `enforced:false`, even when actual commits are correlated. This artifact is neither a source write nor an actual Early Exit.

## Validation and subsequent work

Negative cases live in the already Core-registered `tools/tests/test_audit_workflow_job_costs.py` suite and exercise positive two-phase chaining, real marker/no-op syntax, raw-only publish, invalid repository, missing or failed jobs, conflicting/duplicated markers, retry evidence, wrong parent/author/phase/paths/time and League Live's nested source job naming.

**Next checkpoint (separately scoped):** independently verifiable revision-bound no-op and success attestation across Source and Shared Derived products, including a full semantic output witness and clock/finality/waiver boundaries; source failure and cross-workflow race/recovery remain mandatory negative cases. Any **productive** skip would require a new impact/rollback review and targeted authorization.

Rollback: revert the single offline script, registered tests and historical report. No workflow YAML, Source/Derived/App, permissions, scheduler or writer behavior changed; no additional production sync dispatched.
