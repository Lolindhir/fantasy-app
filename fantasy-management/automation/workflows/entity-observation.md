# Entity Observation Workflow

Purpose: apply reusable observation profiles to configurable entities without coupling the observation model to players, one watchlist or one franchise display name.

## Current operating status

`fantasy-management/_ai/FANTASY_OPERATIONS_ARCHITECTURE.md` is authoritative for current production behavior.

Scheduled Fantasy Operations monitoring is **read-only**. It may resolve targets, research current evidence, normalize material state, compare against approved qualitative baselines and notify about material changes. It must not autonomously persist State, run a baseline backfill, publish Observation Events, advance checkpoint queues or execute the historical Replacement-State-Writer/Bootstrap path.

For every `entity-observation` baseline read, comparison, approved write or State repair, the mandatory storage contract is:

```text
fantasy-management/_ai/OBSERVATION_STATE_STORAGE.md
```

The current durable layout is:

```text
fantasy-management/automation/state/entity-observation.json
fantasy-management/automation/state/entity-observation-targets/{target_id}.json
```

`entity-observation.json` is only the bounded global job header. It contains no canonical target baseline payloads. Every durable qualitative target baseline lives in exactly one complete target shard.

## Inputs

- `fantasy-management/automation/runner-config.json`
- `fantasy-management/automation/jobs/entity-observation.json`
- all required `configuration_refs`
- `fantasy-management/_ai/OBSERVATION_STATE_STORAGE.md`
- `fantasy-management/automation/state/entity-observation.json`
- `fantasy-management/automation/state/entity-observation-targets/*.json`
- current repository data under `public/data/`
- current provider-neutral Operations datasets when applicable
- fresh external sources required by each profile

## 1. Resolve managed context

1. Read `managed_team` from the runner config.
2. Load the configured source.
3. Resolve exactly one team by `identity_field` and `team_id`.
4. Read the current display name only for human-facing output.
5. Fail closed when no team or more than one team matches.
6. Never use the current display name as a state key, path component or configuration identity.

## 2. Resolve target sets

For every relevant target set:

1. Validate the target set.
2. Skip it when disabled.
3. Apply its active target windows.
4. Add enabled manual targets.
5. Resolve enabled selectors against current data.
6. Merge duplicate target IDs only when their entity fingerprints are identical.
7. Merge default and target-specific profile bindings by profile ID.
8. Preserve all contributing target-set IDs.
9. Reject a target whose profile does not support its entity type.
10. Do not write resolved selector results back into configuration.

A canonical entity fingerprint should prefer stable identifiers:

```text
{entity_type}:{identifier_name}:{identifier_value}
```

For players, prefer `sleeper_id` when present.

## 3. Resolve approved baseline state

1. Read the bounded global header and validate that `job_state.targets` is empty.
2. Load all canonical target shards from `entity-observation-targets/`.
3. Validate every shard before using it.
4. Treat a shard's complete `target` object as the only durable qualitative baseline payload for that target.
5. Do not fall back to a historical embedded target payload in the global header.
6. A missing shard means no durable baseline exists for that target; it does not authorize autonomous persistence.

For consumers that require the historical in-memory shape, use the canonical validator/materializer:

```text
fantasy-management/_ai/scripts/validate_observation_state_shards.py
```

Its materialized state is a read model; it is not a second storage location.

## 4. Determine targets and profiles

The target/profile model decides what can be compared and how.

When no previous persisted profile state exists:

1. treat the current successful observation as an internal first-observation baseline for the current run;
2. do not notify merely because the pair was observed for the first time;
3. do not persist it automatically;
4. still notify when the current state itself is clearly materially decision-relevant;
5. propose the exact durable target/profile change when persistence would prevent duplicate future notifications;
6. persist only after explicit human approval.

A missing baseline backlog is not a scheduled-run queue and must not activate Bootstrap, State-only checkpoints or replacement-State publication.

## 5. Collect evidence

For each selected target/profile pair:

1. Read the profile signals and source policy.
2. Resolve current league context from repository data.
3. Use current provider-neutral materialized inputs where applicable.
4. Fetch fresh external evidence when required.
5. Resolve configured source bindings before using alternatives when those bindings remain relevant.
6. Prefer primary or authoritative sources for qualitative role and availability evidence.
7. Record source type, publisher, observed time and supported signals.
8. Deduplicate syndicated reports that originate from the same source.
9. Separate direct facts from reporter interpretation and model inference.
10. Preserve source conflicts rather than silently reconciling them.
11. Fail the profile check when mandatory source confidence cannot be met.
12. Keep a previous good material state when current evidence is incomplete.

Batch source work whenever the profile permits it. Reuse loaded datasets across targets and perform deep player-specific research only when missing qualitative context, changed inputs or concrete change signals justify it.

## 6. Normalize signals and hash material state

Return configured signal IDs with stable value types.

Do not include fetch timestamps, source URLs, prose-only restatements or unsupported speculation in the material state unless an output field explicitly makes such a value material.

Serialize normalized material state with deterministic JSON semantics:

- UTF-8
- object keys sorted recursively
- compact separators
- no insignificant whitespace

Use SHA-256 over those canonical UTF-8 bytes for `state_hash`.

## 7. Evaluate criteria and compare

1. Apply target overrides to profile defaults when applicable.
2. Evaluate atomic and grouped profile criteria.
3. Use profile source policy as a mandatory gate.
4. Compare the current normalized material state to the approved shard baseline when one exists.
5. Treat identical material state as unchanged.
6. Apply materiality criteria to semantic signal changes, not merely source or fetch churn.
7. Use the highest justified severity.
8. A recommendation change cannot make weak evidence material by itself.

## 8. Separate observation, interpretation and decision effect

Every material development keeps three layers:

### Observation

Evidence-backed changes only: role/usage, competitor or injury context, market/rank/value, official status or another configured signal.

### Interpretation

State the reasoned meaning and confidence while preserving unresolved uncertainty or source disagreement.

### Decision effect

Translate the interpretation into the configured perspective. For `managed_team`, resolve current roster, ownership, format, salary, picks and relevant decisions before stating whether future action changes.

## 9. Output and notification

Scheduled monitoring output is notification-only.

When a new material development is found:

- notify according to the current monitoring task and Architecture;
- include the proposed durable target/profile change when persistence is useful;
- identify the target-shard path that would be written after approval;
- do not write State, JSON events or Markdown events before approval;
- do not repeat an unchanged already-known state.

No-change runs remain silent and produce no repository heartbeat.

## 10. Human-approved qualitative baseline update

After explicit approval, update exactly one canonical shard unless the approved logical change explicitly spans multiple targets:

```text
fantasy-management/automation/state/entity-observation-targets/{target_id}.json
```

For a normal approved target/profile write:

1. Read `fantasy-management/_ai/OBSERVATION_STATE_STORAGE.md`.
2. Read the existing complete target shard when present.
3. Preserve unrelated observation profiles in that target.
4. Apply only the approved target/profile change.
5. Recalculate every changed `state_hash` from canonical normalized JSON.
6. Preserve the stable `entity_fingerprint`; identity drift fails closed.
7. Give the logical write a new deterministic descriptive `write_id`.
8. Keep `base_state_revision` equal to the bounded global header revision.
9. Validate the bounded header plus all target shards before publication.
10. Pin the current target-shard blob when replacing an existing shard.
11. Publish only by non-forced fast-forward and recompute on concurrency conflict.
12. Do not rewrite the global header merely because one qualitative target baseline changed.
13. Do not alter jobs, profiles, target sets or generated data as a side effect.

An approved interactive baseline write is not an autonomous runner execution and must not advance `last_successful_run` merely because persistence succeeded.

## Player role-opportunity module

For `player` entities using `role-opportunity`:

- verify current player identity and NFL team;
- inspect official transactions and injury status;
- inspect official or clearly labeled unofficial depth charts;
- use established beat reporters for practice roles;
- prefer repeated first-team usage over isolated clips;
- use `role.first_team_usage_class` when percentages are unavailable;
- inspect snaps, routes, touches and high-value usage when games exist;
- account for competition changes;
- distinguish coach praise from actual role evidence;
- treat one unsupported camp report as insufficient for a material change.

## Market-movement module

For entities using `market-movement`:

- prefer current provider-neutral prepared market signals when available;
- use dated ranking and market snapshots when source-level verification is needed;
- keep independent sources independent;
- do not substitute an unconfigured provider silently;
- do not average incompatible source formats blindly;
- translate market changes into the actual league format;
- require profile thresholds or a documented tier change;
- distinguish role-driven movement from noise;
- record disagreement when sources move in opposite directions.

## Current production readiness

Current scheduled monitoring does **not** require every active target/profile pair to have a persisted baseline. It requires:

1. usable current provider-neutral prepared inputs and their quality/readiness contract;
2. resolvable current repository identity and ownership context;
3. fresh external verification where qualitative injury, availability, role or opportunity evidence is required;
4. read-only execution for the scheduled run;
5. comparison against approved target-shard baselines where they exist;
6. explicit human approval before any durable repository write.

## Legacy autonomous runner

The former write-enabled runner, Observation Bootstrap, complete Replacement-State-Writer, State-only checkpoint queue and autonomous Observation Event publication are historical implementation paths. They are not part of current scheduled production monitoring and do not define current qualitative baseline storage.

Historical files may remain only where another explicitly documented legacy or migration purpose still requires them. They do not override `FANTASY_OPERATIONS_ARCHITECTURE.md`, `OBSERVATION_STATE_STORAGE.md`, the current job definition or the current runner configuration.
