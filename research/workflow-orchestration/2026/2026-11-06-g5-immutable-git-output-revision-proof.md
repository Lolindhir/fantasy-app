# G5 – Immutable Git output revision proof (GET-only)

Date: 2026-11-06. Parent: [#1263](https://github.com/Lolindhir/fantasy-app/issues/1263). Scope: bounded *offline and read-only* output-presence evidence; no skip activation or persisted publication receipt.

## Why this checkpoint is different

Existing [G5 offline protocol](2026-11-06-g5-offline-preflight-protocol.md) checks **synthetic** receipts and race interleavings. Existing `tools/audit_workflow_job_costs.py` binds a successful *observed push* to a Git commit, but explicitly does **not** verify all output contents; no-op logs cannot establish a publication SHA.

The new `tools/league_live_output_revision_audit.py` proves a narrower, real property: selected Git output files and a metadata-derived **minimum** Draft horizon are present as immutable Git blob objects under one explicitly selected 40-character commit SHA.

### Method

The tool uses the existing authenticated, GET-only GitHub API helper; does **not** checkout Git source data, require local PowerShell, call Sleeper or dispatch a workflow.

1. Resolve `commits/<sha>` to the commit's root tree and traverse Git trees **without recursive/truncation shortcuts**. Each returned Git object must match the requested SHA, with no missing/duplicate/unsafe tree entries. No moving `main` ref is used to relabel the committed state as current.
2. Independently enumerate canonical leagues from the immutable `data-meta` tree and check that `data-source/leagues` and all selected Shared-Derived product roots cover precisely that set.
3. Fetch `metadata.json` and the canonical source `manifest.json` as the Git blobs identified in those trees; verify actual decoded bytes against the Git blob SHA-1, JSON shape and current-league/provider identity.
4. Require the configured minimum Draft seasons, computed as `CurrentSeason .. CurrentSeason + UpcomingDraftCount` under the existing `PerDraftType` contract; never hard-code 2027–2029. **Additional observed seasons** are retained in the output inventory rather than discarded. Current transactions, current PWF and TWP week partitions must exist; reject invalid years/weeks.
5. Enumerate all present LeagueDrafts, LeagueTransactions, PWF and TWP seasonal/week partitions and selected App output paths from the existing `league_live_shadow_gate.STAGE_OUTPUTS`, anchored to the exact Git tree blob IDs; compute an order-independent SHA-256 fingerprint of the selected `(path, blob SHA)` inventory.

This provides *immutable output-file existence and Git object IDs*, not recomputed semantic parity. It is intended as evidence that a prior run's claimed output **can be located at a revision**, not that the run produced it. A SHA from Git history can remain available long after its inputs are stale.

### Explicit remaining NO-GO limitations

- No independent proof that all possible future Draft years were discovered. `UpcomingDraftCount` is a minimum for configured years; actual provider-backed future picks and model behavior can create additional partitions. The producer's dynamic provider status and a canonical enumeration/replay must still be checked.
- No proof of newest scored TWP week, PWF parity, skipped/blocked prior fail-soft refresh, corrected historical weeks, *every* App consumer output, or data-model/Scoring/League semantic correctness.
- No proof that the matching Git commit was actually written by the claimed successful League Live run, or that a *no-op* run completed the complete refresh. The existing separate publication and recovery log auditors remain observational and cannot be joined into a safe skip without a causally consistent chain.
- No current live provider freshness, NFL finality/waiver window, complete successful published-output attestation, atomic skip/commit lock, dispatch/requeue guarantee, or end-to-end latency proof.
- An immutable Git commit is **not** a CAS barrier for an absent write. GitHub `main` may advance immediately after a check. This tool is explicitly unsuitable for a ten-minute hot-path preflight.

All reports keep `completeOutputInventoryVerified`, `providerDraftHorizonVerified`, `outputSemanticParityVerified`, `successfulProducerRunVerified`, `independentProviderFreshnessVerified`, `independentNflFinalityVerified`, `recoveryClean`, `raceFree`, `safeToSkip` and `enforced` **false even on positive Git inventory observations**.

### Offline CLI (opt-in only)

```sh
GH_TOKEN=... python3 tools/league_live_output_revision_audit.py \
  --repo Lolindhir/fantasy-app \
  --commit-sha <EXPLICIT_FULL_40_CHARACTER_COMMIT>
```

Authentication and permissions remain read-only (Git contents GET only); no new token, workflow, secret or API write. The CLI is not part of a scheduler, writer, active observability job or production decision. Use an explicit immutable commit instead of assuming that the latest `main` is guaranteed current. The audit does not access all repository blob bytes, only the small canonical metadata/manifest blobs; selected output IDs come from verified Git tree entries.

### Regression and CI routing

Add **15** negative/positive test methods to the existing `tools/tests/test_league_live_shadow_gate.py` (already Fast-registered for `league-pwf-twp` and `consumer-restore`). Fixtures construct an isolated Git object graph, with actual Git blob SHA-1 verification for canonical metadata/manifest. Cases: multi-league enumeration, missing future Draft year, raised metadata draft horizon, extra observed future partition, missing current transaction or TWP/PWF, missing App file, malformed week/path, unauthorized extra league, missing or drifted canonical manifest, wrong blob digest, truncated/incorrect or duplicate Git tree, mutated output fingerprint and no runtime integration.

No new test path or CI inventory tier; exact-head CI must prove the specific existing Fast test class actually runs. No Deep required for a purely offline Git metadata verifier; an independent replay of real Source/Derived fidelity will require the relevant deeper categories in a separate approval.

### Cost and rollback

The GET tool is opt-in, with multiple Git tree/blob requests; **not designed as a cheap production hot-path precheck**. No new production cost or saved work in this checkpoint. Previous six-run descriptive medians remain Source Sync 59s, Standings 51s, League 104s (checkout ~42–43s for each). Prioritize internal no-op computation and approved narrow checkouts independently if net time is the main immediate goal.

No existing workflow YAML, scheduler, branch writer, publication class, permissions, new state/receipt, Source/Derived/App data, tests inventory or generated context changed. Rollback: revert the bounded read-only script, existing registered test additions and this report. Parent #1263 stays open; *actual safe SKIP activation remains NO-GO*.
