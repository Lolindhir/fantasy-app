# G5 – Exact-run Source→Standings→League receipt correlation (read-only)

Date: 2026-11-06. Parent: [#1263](https://github.com/Lolindhir/fantasy-app/issues/1263). This is a **bounded offline audit**, not a production receipt protocol or an authorization to skip League Live stages.

## Purpose and concrete change

Prior G5 checkpoints:
- [PR #1357](https://github.com/Lolindhir/fantasy-app/pull/1357): fail-closed activation design and unresolved race/receipt/freshness questions.
- [PR #1363](https://github.com/Lolindhir/fantasy-app/pull/1363): synthetic evidence / finite interleaving rejection model.
- [PR #1365](https://github.com/Lolindhir/fantasy-app/pull/1365): immutable, selected Git output tree/blob inventory at a named commit, without any run attribution or provider freshness.

New opt-in tool: \`tools/league_live_run_receipt_audit.py\`. It composes *existing*, independent GET-only auditors for **one explicitly chosen League Live run** and the **current run attempt**:

| Owner / stage | Existing evidence used | Important limitation |
| --- | --- | --- |
| Source Raw + Canonical | \`league_source_receipt_audit.audit_source_sync\`: actual Source job identity; two-phase commit receipts or observed no-push/no-op | No-op is not an independent provider acquisition proof; Raw no-push is not automatically a verified no-op |
| Standings | \`audit_workflow_job_costs.audit_publication_receipt\`: actual job, confirmed pushed commit or observed no-op marker | No-op carries **no new commit SHA**; NFL finality may independently advance |
| League (PWF/TWP/Drafts/App) | Same published-commit / no-op audit for League writer | A green League job can retain older fail-soft products; no-op does not prove all outputs are current |
| Recovery | \`league_live_recovery_audit.audit_run\`: exact-attempt Derived product result rows and no blocked statuses observed | Source/Derived models and historic recovery debts are not independently reconstructed |
| Selected immutable output blobs | \`league_live_output_revision_audit.audit_immutable_outputs\` **only when the League writer produced a verified commit SHA** | Commit captures selected Git blobs at that revision, not completeness or semantic parity of *every* dynamically produced output |

The checker reads \`main\` before and after its observations and rejects changed refs. It compares the same run ID and relevant run/producer completion across all reports, verifies stable observed \`main\` for Source / Recovery and each published writer, requires exact canonical league IDs, rejects invented No-op SHA and incorrectly reused previous blob snapshots, and checks relative commit ancestry **only when an actual stage publication SHA exists**. Ancestry is a finite proof that particular commits descend from one another; **it does not serialize writers or prove data freshness after the read**.

For an individually confirmed publish, the resulting report may mark \`leagueCommitSelectedGitBlobsVerified=true\`; a no-op never sets that field. These are read-only historical facts, not safe-to-skip decisions. Even for all-green underlying evidence, these fields remain **false**:

\`completePublicationReceiptVerified\`, \`fullOutputInventoryVerified\`, \`providerFreshnessVerified\`, \`nflFinalityVerified\`, \`recoveryClean\`, \`raceFree\`, \`safeToSkip\`, \`enforced\`.

## No-op behavior is deliberately narrow

A normal current-scope Source no-push and Canonical no-op is classified as a **partial Source observation**; do not claim \`sourceTwoPhasePublicationChainVerified\`. A no-op Standings/League publisher is classified as \`no-op-observed\` without \`stagePublicationCommits\`. A historical snapshot or earlier successful job **cannot be substituted**. A recovered success log with no reported blocked Derived rows still does not certify full historical recovery or actual content parity.

A missing/failed job, retry ambiguity, malformed log, unverified source phase, inconsistent current-league membership, moving main, missing output/tree, inconsistent SHA, failed commit ancestry or mismatched run IDs **blocks correlation**. A complete successful run with source/publisher no-ops can still be a \`correlated-read-only-observations\` result, with explicit \`unproven\` fields; *that result is not clearance to skip*.

A "success" from the CLI means an internally consistent historical observation, **not** any production gate success.

## Execution mode

\`\`\`bash
GH_TOKEN=<READ_ONLY_TOKEN> python3 tools/league_live_run_receipt_audit.py \
  --repo Lolindhir/fantasy-app \
  --run-id <EXPLICIT_LEAGUE_LIVE_RUN_ID> \
  --league nfl-reise
\`\`\`

Repeat \`--league\` for every canonical league. All GitHub requests are GET-only. Job-log redirection remains credential-stripped through the existing \`fetch_job_log\` helper. No new token/secret, workflow/trigger, writer/branch, publication destination, data or persisted receipt. The tool does not choose an earlier run if the selected run fails and never searches for a conveniently successful historical one.

This checkpoint does not claim that the optional authenticated CLI has been executed against a **new, named production League Live run** unless separately recorded with the run ID and outputs; deterministic CI fixtures verify the observation logic.

## Validation and CI coverage

Add **15 deterministic methods** to already registered \`tools/tests/test_league_live_shadow_gate.py\`, covering:
- Genuine published Source, Standings and League receipts plus selected immutable blob inventory still not being a full proof.
- Normal no-op Source/Standings/League with no new SHA, attempted spoofing of a no-op with a stale publication SHA or old snapshot.
- Run/attempt identity mismatch, failed job, changed main ref between audits, changed Source/Standings/League/Recovery view of main.
- Producer-report/Derived recovery contradiction, incomplete or forged Source two-phase evidence.
- Missing/wrong blob revision, changed canonical league scope, invalid selected output fingerprint, broken stage commit ancestry and unresponsive comparison.
- Absence of credentials and the guarantee that a no-op never calls the immutable output auditor for an old commit.

Route the opt-in script through the existing \`league-pwf-twp\` and \`consumer-restore\` Fast families in \`tools/ci_test_impact.py\`; preserve their PowerShell closure. A routing negative test requires that genuinely unknown tool paths still select the fail-closed broad suite. No new test inventory entry or Deep suite is introduced. Verify exact-head CI selection, Core, selected Fast and Merge Gate; verify the test class ran in job logs before merge.

## Architecture review and remaining elevated decisions

- **Existing-first**: no second receipt store or orchestrator; reuse run, source, derived recovery and immutable Git evidence already audited. The tool does not become a new product owner.
- **Provenance**: Source producer commit, Standings and League writer each have *separate* evidence. A historical Git SHA may be identified for actual pushes. A no-op has **no new Git commit** and cannot magically supply a revision-bound successful-refresh receipt. Historical Tree output identity is not equivalent to a writer attestation.
- **Coverage**: this still does not certify metadata-driven *full* Draft partition horizon, all consumer outputs, NFL game finality, player scoring parity, active waiver/clock transitions, previous missing TWP products or other independently published historical corrections.
- **Race/reconciliation**: two reads of \`main\` and sequential ancestry cannot establish an atomic linearization point for a skip. A concurrent writer can commit immediately afterward; any real stage exit needs an approved lock/epoch and reliable invalidation/requeue strategy or remain inside the existing rebuild-and-retry writer.
- **Performance**: this multi-API audit is intentionally **not a cheap ten-minute hot-path precheck**. It has no runtime overhead on League Live. The observed optimistic 155 job-seconds for avoiding Standings+League are illustrative, not validated net benefit.
- **Authority**: all production skips remain **NO-GO**. A persisted producer receipt, new coordination/lock, broader job behavior or independent provider polling will need explicit impact, approval and rollback design.

Next checkpoint should measure *real authenticated runs*, including a no-op and a publish case, then assess whether a light **within-writer** optimization can avoid duplicate generation without any extra whole-job coordination.

**Rollback**: revert the new GET-only script, new tests/CI routing and this research note. Production data and operations remain unaffected.
