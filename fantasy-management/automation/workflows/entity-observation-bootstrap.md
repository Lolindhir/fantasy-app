# Entity Observation Bootstrap Workflow

## Current status

**Disabled legacy workflow.** The machine-readable policy `fantasy-management/automation/bootstrap/entity-observation-bootstrap.json` is currently `enabled: false`, and `FANTASY_OPERATIONS_ARCHITECTURE.md` explicitly prohibits autonomous bootstrap or baseline-backfill execution in scheduled monitoring.

Missing target/profile baselines do **not** activate this workflow in the current production architecture. Scheduled monitoring remains read-only, may build an internal first-observation comparison state for the current run, and proposes any durable baseline write for explicit human approval.

This document is retained as a historical implementation contract for the former autonomous bootstrap and for its useful deterministic checkpoint, hashing, validation and optimistic-concurrency semantics. It may not override the current Architecture or `runner-config.json`. Re-enabling this bootstrap would be a separate architecture/configuration change requiring explicit approval.

Purpose: initialize missing observation baselines efficiently without weakening state validation, publication safety, or monitoring priority.

Historically, this workflow was active while at least one active target/profile pair had no good stored baseline and superseded the fixed deep-evaluation pair budget in sections 3.1 and 3.3 of `entity-observation.md`. The rules below describe that legacy autonomous execution model and are not an activation condition today.

The machine-readable policy is:

```text
fantasy-management/automation/bootstrap/entity-observation-bootstrap.json
```

## 1. Preserve monitoring priority

Before baseline work, perform the normal cheap complete scan for every active pair.

Process these categories in order:

1. already-baselined pairs with changed relevant fingerprints;
2. already-baselined pairs with a concrete current change signal;
3. missing initial baselines;
4. retryable pending pairs;
5. retryable failed pairs.

Bootstrap work must never postpone a current material-change candidate merely to increase the number of initialized baselines.

## 2. Use a runtime budget, not a small pair quota

Start a monotonic runtime clock when the job begins.

- Soft deadline: 85 minutes.
- Hard deadline: 110 minutes.
- Safety cap: 500 deeply processed pairs in one wakeup.

Before the soft deadline, begin another coherent source or team group whenever useful work remains.

After the soft deadline, do not begin another group. Finish, validate, and publish the current completed group only when that can be done safely before the hard deadline.

At the hard deadline, do not attempt an unvalidated emergency write. Preserve the last successfully published checkpoint and continue from repository state on the next scheduled wakeup.

The external scheduler does not guarantee the full hard-deadline duration. Therefore every completed group must be independently checkpointable.

## 3. Batch by reusable source context

Do not count a dataset join for each player as a separate research operation.

### 3.1 Dynasty market batch

Load each configured FantasyPros and FantasyCalc snapshot once. Resolve every eligible active player against the in-memory datasets, create all successful `market-movement` baseline results, and publish one checkpoint for the complete coherent batch.

A missing row affects only that pair. It must not prevent other resolved players from entering the checkpoint.

### 3.2 Redraft ADP batch

Load both configured Fantasy Football Calculator snapshots once. Resolve all eligible active players in one pass and publish one checkpoint for the complete coherent `redraft-adp-movement` batch.

### 3.3 Injury batch

Load current player, roster, transaction, and reusable injury inputs once. Group unresolved players by NFL team. Publish a checkpoint after each completed team group or after a larger complete injury group when the evidence and runtime allow it.

Only ambiguous cases require deep player-specific external research.

### 3.4 Role and opportunity batch

Group players by NFL team and, where useful, position group. Reuse official team, depth-chart, transaction, and established beat evidence only when it supports every included player-specific signal.

Publish a checkpoint after every completed NFL-team or team-position group. Do not keep completed groups only in conversational memory while researching later teams.

## 4. Build deterministic checkpoint inputs

For each completed group, create a JSON checkpoint that validates against:

```text
fantasy-management/_ai/schemas/automation-observation-state-batch.schema.json
```

The checkpoint must include:

- the exact expected current State revision;
- the pinned current `main` parent commit SHA;
- the pinned current State blob SHA;
- one unique result for every included target/profile pair;
- the complete expected active profile-ID set for every included target;
- canonical structured material states rather than prose summaries;
- source fingerprints and confidence;
- the resulting top-level pending status;
- one concise operational recent event.

Unpublished findings from a failed checkpoint are not state and must not be reused as stored baselines on the next wakeup.

## 5. Generate the complete replacement State

The historical helper is:

```text
python fantasy-management/_ai/scripts/apply_observation_state_batch.py \
  --state fantasy-management/automation/state/entity-observation.json \
  --checkpoint <checkpoint.json> \
  --state-schema fantasy-management/_ai/schemas/automation-observation-state.schema.json \
  --checkpoint-schema fantasy-management/_ai/schemas/automation-observation-state-batch.schema.json \
  --output <replacement-state.json>
```

The helper:

1. rejects a stale State revision;
2. preserves every untouched State section;
3. rejects duplicate pair results, incomplete profile contracts, or changed entity fingerprints;
4. calculates SHA-256 over recursively sorted compact canonical JSON material states;
5. preserves the previous good material state on retryable failures when configured;
6. increments the State revision exactly once per checkpoint;
7. validates the complete replacement document against the observation-State schema.

The helper performs no research and makes no fantasy recommendation. Its historical presence does not authorize scheduled monitoring to execute it.

## 6. Cross-file validation and publication

The former autonomous checkpoint publication contract was:

1. place the generated complete replacement State at the canonical State path in a disposable or controlled working tree;
2. run `fantasy-management/_ai/scripts/validate_automation.py` against that complete tree;
3. confirm the job write scope contains only the State path for baseline progress;
4. confirm `main` still equals the checkpoint's `expected_parent_sha`;
5. confirm the current State blob still equals `expected_state_blob_sha`;
6. create a Git tree containing the full replacement State;
7. create one commit whose parent is exactly `expected_parent_sha`;
8. move `main` only by non-forced fast-forward;
9. read the committed State from `main` before considering the checkpoint successful.

If either SHA changed, discard the prepared replacement, reload `main`, and recalculate the next checkpoint. Never merge operational State automatically.

Historically, a bootstrap checkpoint was State-only and created no Observation Event or user notification. In the current architecture, scheduled monitoring does not publish such checkpoints at all.

## 7. Resume behavior

The historical autonomous behavior after a successful checkpoint was to use the newly committed State as the only continuation source and re-resolve the remaining queue against current `main`.

When a later group failed:

- retain all earlier published checkpoints;
- do not roll back successful progress;
- record or notify a new materially changed error only when the configured error policy permits it;
- leave the external daily task enabled;
- resume from the last committed checkpoint on the next wakeup.

This resume behavior remains historical documentation and is not current scheduled-monitoring behavior while bootstrap is disabled.

## 8. Bootstrap completion

Historically, bootstrap ended when every active target/profile pair had either:

- a valid baseline or later good material State; or
- a retryable state that preserves a previous good material State.

Pairs with no good State remained bootstrap work even when marked pending.

After completion the old runner returned to fingerprint- and event-oriented monitoring.

Under the current architecture there is no requirement to bootstrap every active pair before scheduled monitoring can operate. Persist only specifically approved qualitative baselines unless a future explicit architecture decision changes that policy.
