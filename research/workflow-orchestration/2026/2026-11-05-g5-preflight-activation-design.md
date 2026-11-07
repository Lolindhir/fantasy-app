# G5 – Activation design for a safe League Live preflight (NOT approved)

Date: 2026-11-05. Parent: [#1263](https://github.com/Lolindhir/fantasy-app/issues/1263). Basis: current League Live, rebuild-and-retry publisher and the read-only G5 evidence through [PR #1355](https://github.com/Lolindhir/fantasy-app/pull/1355). This is a **design proposal**, not a decision to change production behavior.

## 1. Goal and non-goals

Goal: reduce *unnecessary* ten-minute League Live work without missing provider changes, temporal transitions, correction/recovery work or publication races. Preserve separate Source, Shared Derived and App owners, existing writer scopes/permissions and all current failure-isolation boundaries.

**Not in this checkpoint:** activation, any job skip, new GitHub Actions workflow, persistent receipt, provider polling or secret, scheduler change, new branch-writer/lock, product/metadata write, CI/test change or production dispatch. No assumption that six successful runs prove a long-term no-op ratio.

## 2. Observed ownership and existing protection

| Stage | Existing contract | Why a no-op alone does not authorize skipping |
| --- | --- | --- |
| Source | `sync-league-source-data.yml`: current-scope provider acquisition, Raw/Canonical validation, two-phase rebuild/retry | The provider may have changed after the last Git snapshot; a no-push log is a historical observation, not independent current freshness |
| Standings | `league-live.yml` → `rebuild_and_publish.py --scope standings`; semantic no-op | NFL finality can advance outside the source chain; Standings is derived from more than League-source input trees |
| League | `league-live.yml` → one rebuild/retry transaction for PWF, history, TWP, matchup/recaps/League/TeamCapOutlook | Clock/waivers, late revisions, dynamic future Draft seasons, and fail-soft TWP can invalidate apparently unchanged inputs |
| Recovery | Weekly `update-standings.yml` and `update-transactions.yml` own historical backstop | A green live job can retain stale TWP/History; it is not proof that all required partitions are restored |

Existing `tools/league_live_shadow_gate.py`, `league_current_noop_audit.py`, `league_source_receipt_audit.py`, `league_live_invalidation_audit.py` and `league_live_recovery_audit.py` are deliberately **observers**, not production skip gates. `workflow-publication.yaml` requires rebuild-and-retry on races. The workflow-level `concurrency: league-live` and Source Sync's separate group **do not serialize all main writers**.

## 3. The minimal candidate: stage-local, revision-bound skip

Do **not** try to skip provider acquisition at first. A Git-tree comparison cannot establish that Sleeper/other upstream facts have not changed. Continue the current Source synchronization, unless a *separate* independently verified provider freshness contract makes a Source-stage skip defensible.

Propose a **single existing-workflow stage-local gate**, initially *shadow-only*, evaluated after a successful current Source result and immediately before **each** downstream stage, not an extra full-checkout audit job. The candidate decision is one of:

- `RUN` (normal/default; includes unknown, missing evidence, stale output, time change, recovery debt and any branch race).
- `WOULD_SKIP` (observation only, never short-circuits execution in the current design).
- `SKIP` (future, only after an approved atomic/invalidation architecture and all gates below).

A green Source Sync cannot by itself skip Standings. A green Standings cannot by itself skip League. A League-stage skip would suppress *all* components of its transaction and therefore requires complete readiness for each one; do not hide partial no-ops as a whole-stage success.

### 3.1 Candidate verification tuple

Bind each candidate to `(CanonicalLeagueID set, canonical league season per ID, stage, producer/contract versions, upstream acquisition identity, input revision/tree hashes, full output inventory + content digests, successful producer run/attempt, observed UTC interval, publication revision)`. Include model selections, scoring profile, league metadata, current/previous transaction partitions, current plus **all configured future Draft partitions** (discovered from canonical metadata/provider records; no fixed year), newest scored-week TWP and previously failed partitions as explicit unresolved debt. The weekly historical correction path remains separate and must not be misrepresented as live coverage.

Receipt cannot merely list three top-level derived rows. For each affected output, record exact identity, status, expected existence, immutable blob digest and provenance from the actual writer transaction. The App output manifest must be discovered from the real generators, not guessed from `STAGE_OUTPUTS` or the paths allowed by the publisher (which are deliberately broader). A missing output, removed partition or unknown newer contract version rejects the candidate.

**Receipt design constraint:** a file committed to `main` cannot safely name its own commit SHA (self-reference). A proposed in-transaction manifest could bind the *base revision*, input-tree hashes and output blob identities, while an independent reader resolves and verifies the manifest's containing commit and successful writer attempt afterward. Source Raw→Canonical and Standings→League need a verified ancestor/causal chain even when unrelated writers insert commits. Whether receipts belong in an existing output prefix or an external immutable run artifact remains **unresolved**: either new persistence or external retention/replay semantics needs separately scoped approval and compatibility review. No receipt format or write path is activated here.

A no-change run creates **no new main commit** today. Reusing an earlier receipt only proves parity for the *old* observation; the next tick must still prove current provider freshness, clock/finality and recovery state. Do not introduce a timestamp-only commit on every ten-minute no-op.

### 3.2 Fail-closed decision predicate

An eventual `SKIP` would require **all** of the following, from independently checked evidence, for the exact targeted stage:

1. The complete league/season/partition/output manifest matches current canonical metadata and the selected model/code contracts. Every expected output exists with independently validated digest/semantic parity at an immutable repository revision.
2. The previous successful writer attempt and upstream Raw→Canonical→Derived→Consumer causal chain are unambiguous; no retry, partial commit or fail-soft `blocked`/`no-scored-week`/unverified parity survives as recovery debt.
3. A fresh, provider-specific **acquisition/freshness** fact covers all material current inputs (including transactions, drafts and corrections), with explicit expiry and error semantics. A successful historical no-op, HEAD equality, GitHub run conclusion or simple age threshold **does not count**.
4. Canonical NFL game finality, scoring basis, lineup/waiver/cap/season boundaries and all kickoff intervals between the previous computation and the decision are checked. Unknown kickoff, nonfinal active game, unsupported transition, changing current-time-sensitive output or crossed boundary forces `RUN`.
5. Any relevant dependency change from an unrelated main writer, source owner, model/config or app reader invalidates the receipt; Git tree hashes and dependencies must match the exact candidate revision. `main` reread alone is **not an atomic race boundary**.
6. The **race/commit linearization mechanism** described next is actually implemented and negative-tested. In its absence, even five satisfied predicates are `WOULD_SKIP` at most, not `SKIP`.

## 4. Race boundary: a design gap, not a solved feature

`rebuild_and_publish.py` fetches latest `main`, generates from it and on non-fast-forward rebuilds after resetting to the new head. A skip returns **without a push**, hence has no compare-and-swap failure that could reveal a concurrent writer. Two `main` reads are observations, not a lock. Any external writer can change relevant dependencies just after a read or skip.

Three possible models, none approved:

| Candidate | Safety condition | Cost / reason to defer |
| --- | --- | --- |
| A. In-process checked recomputation | Keep the classified writer and rebuild-and-retry transaction; optimize expensive individual derivations after a pinned fetch, always preserving existing publication and repair checks | **Preferred near-term low-risk alternative**; does not claim a no-job early exit but avoids new cross-writer atomic skip semantics |
| B. Repo-wide writer serialization + invalidation wake-up | ALL relevant source/derived/app writers honor one shared critical section, and a later dependency commit reliably schedules reconciliation; skip is linearized to an explicitly defined point in that section | High queue contention, cross-repo/external writes, missed webhook/dispatch and post-release races must be measured; changing existing workflow concurrency is elevated in effect |
| C. External or repository-state CAS/lease + invalidation journal | A durable lease/epoch binds the observed revision; relevant commits atomically invalidate it and reliably requeue skipped stages, including recovery when dispatch fails | New state owner, permissions, branch writer/retention, failure modes and operational complexity: elevated approval and independent review required |

**Important impossibility boundary:** an unconditional guarantee that an output remains up-to-date *after* a skip cannot be achieved by a one-time SHA check. The contract must either define a snapshot linearization point *and* an assured subsequent invalidation/reconciliation trigger, or decline to skip. Optimistic writes protect publish, but they do not automatically protect the absence of a write. Do not present A as atomically equivalent to B/C.

**Recommendation:** prefer A (internal fast no-change/partial recomputation within existing writers) before considering the new persistent coordination in B/C. An actually skipped entire Standings or League job is **not ready for activation**.

## 5. Runtime budget / go-no-go

Six natural successful League Live ticks from the previous checkpoint gave the following descriptive medians; these are **job runtimes**, not billed-minute or paired per-run savings:

| Job | Median wall clock | Median checkout |
| --- | ---: | ---: |
| Source Validate | 13 s | 4 s |
| Source Sync | 59 s | 43 s |
| Standings | 51 s | 43 s |
| League | 104 s | 42 s |

The most optimistic downstream Standings+League avoidance is **about 155 job seconds per eligible tick**. If the gate adds `G` seconds to *every* tick and fraction `p` qualifies, the first-order job-time budget is `p × 155 − G` seconds per tick, before scheduler latency/queues, retries and hidden downstream costs. Example break-even: `G=10 s` needs `p > 6.5%`; `G=45 s` needs `p > 29%`. For League alone substitute 104 s (10 s costs >9.6% of that potential saving). These are illustrative thresholds, **not** validated gate costs or an expected savings claim.

A full checkout/log scan in a new job likely erases some benefit. Benchmark a proposed gate *in the actual execution placement* including runner startup, checkout (if any), API calls, serialization and recovery fallbacks. Record matched run pairs plus real qualified-no-op rate and effect on end-to-end completion and freshness; do not use six medians as predictive distributions.

**Acceptance to even request activation:** no new unexplained outputs or permissions; all negative fixtures pass; compare at least 30 naturally occurring quiet and live ticks, explicitly covering any otherwise unobserved finality, waiver, trade, late correction and cross-writer concurrency cases with targeted simulations; measure gate overhead and net end-to-end savings versus equivalent baseline runs; no missed refresh, stale consumer receipt, skipped recovery or unobserved failed producer. 30 ticks are a measurement sample, not a statistical proof; missing edge classes must be simulated, not waived.

## 6. Required offline negative tests before any approval

- Source changed after the prior successful no-op; silent provider update despite identical Git trees; missing or expired source freshness evidence.
- Two concurrent main writers with a commit **between check and skip** and one **immediately after skip**; invalidation dispatch lost or delayed; head advance between input and output receipt reads.
- Failed/retired historical TWP partition, `no-scored-week`, unverified or accepted-divergence PWF parity, stale LeagueTransactions or dynamic future Draft season newly added.
- Successful overall run with an earlier blocked Derived product; ambiguous rebuild attempt; Raw published without valid Canonical; valid app with older model/scoring settings.
- NFL finality transition without League Source change, started nonfinal game, unknown kickoff, waiver run between equal lifecycle endpoints, cap/season rollover and time-dependent display output.
- Missing/deleted/extra output, corrupt receipt/blob, receipt self-reference, source ownership/league scope drift, expired artifact, PR/manual run mistaken for production, API outage or permission denial.

Every missing/ambiguous case must select normal `RUN`; this is independent from whether a resulting producer returns semantic no-op. Model all failure reasons in machine-readable Job Summary/observability and preserve existing workflow-monitoring classification.

## 7. Rollout and rollback (proposed only)

**Phase 0 (this document):** record rejected shortcuts, candidate protocol, cost gate and open decisions. No production changes.

**Phase 1 (separate bounded authorization):** choose one receipt/atomicity model; prototype *offline* on immutable fixtures, current code and test routing (Core/Fast for protocol decisions, Deep only for affected full restore families). Independent architecture review of concurrency, ownership and source freshness. No real skip.

**Phase 2 (separate elevated approval if persisted receipts, writer, concurrency, trigger or permissions change):** opt-in live shadow with explicit reason codes and actual overhead budget. Keep all writers, retries and products unchanged. Use natural runs to compare readiness and recovery.

**Phase 3 (targeted production activation approval only after proof):** dark-by-default flag, one narrowly scoped stage, monitored canary, forced full-run fallback on any missing evidence, and rapid rollback by disabling the flag; if any changed writer semantics were introduced, revert the scoped PR. Keep weekly recovery and Source acquisition active. Do not remove full-run capability or widen publication scope.

Current activation verdict: **NO-GO**. The supported next engineering candidate is a bounded **within-writer cost optimization / receipt feasibility study**, not a production early exit.

## 8. Architecture self-review / handoff decisions

Existing-first: reuse the current scheduler, Source/Standings/League jobs, `rebuild_and_publish.py`, shadow readers and weekly historical backstops. No new orchestrator is justified. Ownership: facts stay in `data-source`, models/products in `data-derived`, App output remains consumer; a future receipt is provenance *metadata*, not a new source of truth. Identity: all league, season, week, provider, model, settings, input and artifact revisions must be explicit, including dynamically configured future Drafts. Invalidation: external provider, NFL finality, timestamps, model/config, output and unrelated writers are all explicit. Multi-league/unknown: fail closed. Compatibility: an unrecognized schema/version forces full rebuild.

Open decisions requiring targeted review before implementation: **D1** receipt owner/storage/retention and no-op proof; **D2** independent provider/finality freshness and event coverage; **D3** actual atomic/reconciliation boundary; **D4** practical stage and gate placement; **D5** measured latency/no-op benefits, CI coverage and rollback controls. The present evidence resolves none of D1–D3 sufficiently to authorize skips.

Validation of this checkpoint is documentation/repository inspection only; no production code, tests, generated files, branch writer, permission or scheduler behavior is changed. Rollback: revert this design-note commit/PR; there is no runtime effect.
