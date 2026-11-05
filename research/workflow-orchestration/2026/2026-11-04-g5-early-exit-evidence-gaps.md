# G5 League Live early-exit proof: evidence boundaries (2026-11-04)

Status: **offline-only, no enforcement, no production skip authorization**. Owner: #1263.

## Existing-first study

Reviewed `tools/league_live_shadow_gate.py`, `tools/tests/test_league_live_shadow_gate.py`, `.github/workflows/league-live.yml`, `.github/workflows/sync-league-source-data.yml`, `tools/rebuild_and_publish.py`, and the publication/recovery contracts. No new workflow, scheduler, writer, persistent attestation, or permission is introduced here.

The current shadow gate emits `would-run`/hypothetical `would-skip` observations, but it does not control a GitHub job. In production it deliberately sets `raceFree=None` and `recoveryClean=None`; no independent previous successful publication attestation is available. Therefore **current production observations cannot justify any skip**, even when two input tree fingerprints are equal.

The existing `STAGE_INPUTS` are repository-wide conservative tree fingerprints across all league/season scopes, not a full proof of state-dependent freshness. For League, the previous minimum `STAGE_OUTPUTS` did not explicitly check App Drafts/Transactions or the Shared Derived draft/transaction roots. This checkpoint adds these four **existence-only** observations. They are not an attestation that every configured future-season Draft partition is present, current, and consistent with Team DraftPicks.

## Real run observations

Read-only natural League Live runs: #41889788258, #41891411092, #41893002075, #41894664499, #41896280450, #41897887651, all successful. In all six, canonical League Source sync reported no canonical changes and Standings publisher reported no changes; League publisher reported no changes in **five of six** (not #41896280450). These are after-the-fact observations and cannot be turned into pre-execution authorization. Independent NFL finality, market/model/code changes, and race/recovery conditions remain relevant. No extra production run was dispatched.

## Offline proof matrix

| Case | Expected evaluation | Why |
| --- | --- | --- |
| Completely formed synthetic prior/current with equal input evidence and bounded clock | hypothetical `would-skip`; `enforced=false` | Exercises branch, **not** trusted production provenance |
| Missing previous successful attestation | `would-run` | No proof of last completed publication |
| Source, Derived, Meta or App revision change | `would-run` | Inputs no longer equal |
| Missing App Drafts/Transactions or shared Derived roots | `would-run` | Incomplete output inventory |
| Missing any specific configured future Draft partition | **not yet covered by directory existence** | Needs dynamic season-aware coverage and owner parity witnesses |
| New finality/waiver/week/season boundary or expired clock window | `would-run` | Time-sensitive output can change absent source-tree commit |
| Source/upstream failure, concurrent branch writer or unknown recovery | `would-run` | Must fail closed |
| String/int-substituted boolean attestation fields | `would-run` | Require exact Boolean truth, not truthiness |
| Equal prior/current shadow log signatures | `safeToSkip=false` | Logs do not certify job conclusion, outputs or cross-run race safety |

## Unproven requirements for a real production gate

1. **Attestation provenance**: independently verified prior successful job/commit and validated outputs on the target branch, not a log line, timestamp, or user-editable marker.
2. **Dynamic product coverage**: the full configured current/future draft season/type inventory, consumer parity and model/identity fingerprints, beyond existence of the `data-derived/league-drafts` directory.
3. **Time/finality**: explicit validity horizon that terminates before kickoff, scoring finality, waiver, transaction cutoff, or league season transitions, including source-independent clock changes.
4. **Cross-workflow invalidation**: NFL finality, PlayerWeekFantasy/TeamWeekPerformance, Salary, roster, league meta, and other consumed shared product revisions.
5. **Race and recovery**: proof that no competing main writer modified relevant inputs between preflight and the decision; stale/fail-soft products trigger rebuild; branch-race and retry guarantees retained.
6. **Failure isolation**: a blocked or failed Source validation/sync must never silently skip downstream recovery when required.
7. **Fast/Deep negative testing**: producer/recovery and dynamic league/season negative cases must pass on an exact PR head before any production gate is considered.

## Checkpoint boundaries

Only extends existing read-only shadow inventory and its already registered Fast tests. No generated data, canonical facts, workflow YAML, live skip branch, scheduler cadence, authorization boundary, or PR publication writer changes. Existing optional shadow observer remains `continue-on-error` and non-authoritative.

**Recommendation:** keep actual League Live unchanged. The next distinctly scoped checkpoint should produce independently verifiable prior-publication and temporal/dynamic-partition witnesses in **read-only shadow**, with negative race, clock and recovery cases, before discussing a real job skip. Any production gate needs a new targeted impact/rollback review.
