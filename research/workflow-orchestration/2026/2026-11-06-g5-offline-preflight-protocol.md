# G5 – Offline preflight protocol and deterministic negative fixtures

Date: 2026-11-06. Owner: #1263. Status: **offline feasibility only / NO-GO for live early exit**. This checkpoint follows the 2026-11-05 activation design (merged PR #1357).

## Exact implementation boundary

Extend the **existing** `tools/league_live_shadow_gate.py` with two pure functions:

- `assess_offline_preflight_protocol(receipt, observed, race_events)`: checks that *caller-supplied synthetic* evidence contains matching league/season scope, stage, publisher/source revisions, exact dependency tree hashes, canonical expected / published / observed output digests, successful producer and no reported recovery debt; a time-bound provider acquisition, NFL finality and clock/boundary evidence; plus the finite race trace.
- `replay_offline_skip_race(events, pinned_sha)`: deterministic state-machine model of a hypothetical all-writer lock, revision comparison, skip, release and post-release invalidation/rebuild. Rejects competing commits inside the critical section, stale compare, incomplete locking, missing enqueue or rebuild, invalid events and unknown revisions.

These functions are **not imported or invoked by any production job, publisher, scheduler or source consumer**. The existing `collect`/`decide` and GitHub workflow remain untouched in behavior. A synthetically complete input can return `decision=would-skip` to make the negative test oracle meaningful, but **always** returns `safeToSkip=false`, `enforced=false`, `independentEvidenceVerified=false`, `raceFree=false` and `recoveryClean=false`. No synthetic field may be used as actual attestation.

The fixture's `requiredOutputs` list represents a hypothetical canonical enumeration of exact output paths, not an implementable production discovery mechanism. It includes an illustrative future Draft partition beyond a one-year horizon plus TWP/PWF. It cannot prove that every real generator output or historic repair partition was discovered. Any production receipt design still needs this independent enumeration and verification.

## Negative test coverage and fast-tier ownership

Add cases in existing registered Fast module `tools/tests/test_league_live_shadow_gate.py` (Fast groups `league-pwf-twp` and `consumer-restore`). Covered:

- Known stages and strict canonical League+Season scope; unknown stage, missing/duplicate and changed scope; wrong receipt/schema SHA.
- Complete exact expected/persisted/observed output digests, missing extra/dynamic future-year Draft partition, missing TWP surface and forged paths.
- Source/Derived/Meta/App/code tree invalidation; blocked or ambiguous producer; any fail-soft retained TWP, Draft, unverified parity or unfinished recovery.
- Provider revision/identity mismatch, unknown or expired provider observation, unsupported NFL finality, active nonfinal games, missing kickoff.
- Kickoff, waiver, cap and season boundaries, clock reversal and invalid interval.
- Deterministic race interleavings: relevant commit between check and skip, commit while locked, commit before lock, after-skip commit with lost enqueue, enqueue without rebuild, and a *finite* post-release commit→enqueue→rebuild positive model case; lockless, duplicate, malformed and unknown actions.

CI inventory/routing: no new test file, no new workflow, no Deep test and no claimed replay against real NFL source data. The new cases are cheap, deterministic Python logic in an already registered Fast module. Confirm actual jobs and CI times on the PR; a green Merge Gate by itself is not evidence that this particular module ran.

## Why this is NOT the security acceptance

A test fixture can supply internally consistent false assertions about an unseen provider update, NFL finality, output inventory or lock ownership. The code does **not** authenticate these facts. A finite race trace does not establish the absence of events after its last entry, universal cross-writer participation, durable dispatch delivery or a linearization point in GitHub. The current `main` read/compare is not a CAS for an absent write.

The step is deliberately limited to verifying the **decision protocol's rejection properties under supplied evidence**. It cannot legitimately enable a productive `SKIP`. Next proof must bind output inventory/digests and revision to a real writer/immutable receipt, establish independent acquisition/finality invalidation and choose a real cross-writer race/reconciliation mechanism. That is a distinct elevated-scope review, not implicitly authorized here.

## Cost baseline and comparison to internal optimization

The prior report measured six naturally successful ten-minute ticks (descriptive medians, not paired sums):

| Job | Median runtime | Median checkout |
| --- | ---: | ---: |
| Source Validate | 13 s | 4 s |
| Source Sync | 59 s | 43 s |
| Standings | 51 s | 43 s |
| League | 104 s | 42 s |

A hypothetical whole-stage skip of Standings+League avoids at most approximately **155 job-seconds per eligible tick**, before added gate time and recovery overhead. If a gate cost is G seconds **on every tick**, and an independently confirmed eligible fraction is p, net rough job-time proxy is `155*p - G`. A 10-second gate needs >6.5% eligibility to break even; a 45-second gate >29%. Real runner and checkout changes must be measured; these figures are *not* a production prediction. The offline checker is **not installed in the ten-minute hot path**, so current overhead and saved time are both exactly zero.

**Existing-writer alternative:** preserving current `rebuild_and_publish.py` fetch/compare/rebuild-on-race and fail-closed repair checks avoids the new atomic absence-of-write coordination problem. Candidate optimizations are per-generator no-op/dirty-input filtering, reduced duplicate work and targeted read-only checkouts where dependency closure is proven. Measure each on real jobs without weakening canonical source acquisition or weekly recovery. Do not confuse generator-internal computation savings with eliminating the 42–43-second writer checkout.

## Next explicit Go/No-Go checkpoints

1. Prove a real **immutable producer receipt** with complete, metadata-discovered league/season/partition/consumer output inventory, independently verified blobs and healthy recovery, including no-change runs. Resolve the self-referencing commit-SHA problem.
2. Prove independent provider acquisition, NFL finality and clock/waiver invalidation for every skipped stage. A historical no-op or 60-minute age cap is not enough.
3. Specify and verify a real all-relevant-writer lock+guaranteed requeue **or** equivalent atomic epoch/CAS/reconciliation protocol; test late commits, lost dispatch and crashes. Document costs, privileges and rollback.
4. Run strictly observational Shadow with at least 30 real quiet/live ticks and synthetic missing edge cases; record full-gate overhead, qualified no-op fraction, missed refreshes, unknowns and end-to-end runtime versus equivalent baseline.
5. Independent architecture review, exact-head green Core/Fast (and targeted Deep where source/restore proof requires), specifically scoped elevated approval, feature-flagged one-stage canary and tested full-run fallback.

**Checkpoint validation/rollback:** existing `league-live.yml` and publisher semantics remain unchanged. No new source/derived/app data or auth/secret writes. Remove/revert the two scoped code/test changes and this research note to roll back, with no production runtime effect. `safeToSkip` is **never** asserted.
