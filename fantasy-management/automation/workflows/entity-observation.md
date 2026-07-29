# Entity Observation Workflow

Purpose: apply reusable observation profiles to configurable entities without coupling the runner to players, one watchlist or one franchise display name.

The first manual baseline and the controlled atomic-write test have been completed. The job is eligible for production execution when both `runner-config.json` and the job definition are enabled.

## Inputs

- `fantasy-management/automation/runner-config.json`
- `fantasy-management/automation/jobs/entity-observation.json`
- all required `configuration_refs`
- `fantasy-management/automation/state/entity-observation.json`
- current repository data under `public/data/`
- fresh external sources required by each profile

## 1. Resolve managed context

1. Read `managed_team` from the runner config.
2. Load the configured source.
3. Resolve exactly one team by `identity_field` and `team_id`.
4. Read the current display name only for human-facing output.
5. Fail closed when no team or more than one team matches.
6. Never use the current display name as a state key, path component or configuration identity.

## 2. Resolve target sets

For every required target set:

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

## 3. Determine due targets and profiles

The job-level interval limits how often the job may run. Within a due job:

- skip disabled or expired targets;
- skip disabled profile bindings;
- permit target-level threshold overrides;
- evaluate profiles independently;
- do not recheck a target/profile pair before any stricter future per-profile cadence unless explicitly configured later.

The initial framework uses the job cadence for every profile. Profile-specific cadence can be added without changing state identity.

## 4. Collect evidence

For each target/profile pair:

1. Read the profile signals and source policy.
2. Resolve current league context from repository data.
3. Fetch fresh external evidence when required.
4. Resolve configured source bindings before using alternative sources.
5. Prefer primary or authoritative sources for qualitative role evidence.
6. Record source type, publisher, observed time and supported signals.
7. Deduplicate syndicated reports and articles that originate from the same source.
8. Separate direct facts from reporter interpretation and model inference.
9. Preserve source conflicts rather than silently reconciling them.
10. Fail the profile check when mandatory source confidence cannot be met.
11. Keep the previous good material state when current evidence is incomplete.

## 5. Normalize signals

Return the configured signal IDs with stable value types.

Do not include:

- fetch timestamps in the material state;
- prose-only restatements of unchanged values;
- source URLs in the material-state hash;
- speculative values not supported by evidence.

The normalized material state contains only fields listed in the profile's `output_fields` plus explicitly approved structured support fields.

## 6. Evaluate criteria

1. Apply target overrides to profile defaults.
2. Evaluate atomic and grouped criteria.
3. Use profile source policy as a mandatory gate.
4. A criterion classification describes the type of material change.
5. Multiple matching criteria may be combined into one event when they describe the same underlying change.
6. Use the highest justified severity.
7. A recommendation change cannot make weak evidence material by itself.

Supported operators are defined in `automation-criterion.schema.json`.

## 7. Baseline and comparison

When no previous profile state exists:

1. store or propose a baseline;
2. mark the profile state as `baseline`;
3. do not create an event unless `notify_on_initial_baseline` is true.

For later checks:

1. hash normalized material state;
2. compare it to the stored state hash;
3. treat an identical hash as unchanged;
4. apply criteria to actual signal changes;
5. create an event only when at least one material criterion matches.

## 8. Separate observation, interpretation and decision effect

Every event must contain three distinct layers.

### Observation

Only evidence-backed changes:

- changed role or metric;
- changed competitor or injury context;
- changed ranking, tier or value;
- changed official status.

### Interpretation

A reasoned meaning with explicit confidence:

- likely role upgrade or downgrade;
- likely increase or decrease in future opportunity;
- source disagreement;
- unresolved uncertainty.

### Decision effect

Translate the interpretation into the configured perspective.

For `managed_team`:

1. resolve the current team by stable ID;
2. load current roster, ownership, format, salary, picks and relevant decisions;
3. apply the target's effect rules;
4. state whether action changes and how urgently;
5. use the current franchise name only in prose when helpful.

## 9. Output and notification

A material change produces matching Markdown and JSON under:

```text
fantasy-management/analyses/{season}/observation-events/
```

The JSON must validate against `automation-observation-event.schema.json`.

Publication must follow `atomic-publication.md`. State, JSON event and Markdown event are one atomic material-change bundle.

Notify only when:

- the job notification rule permits it;
- severity meets the threshold;
- the event is not a duplicate;
- the baseline policy permits it;
- the atomic repository publication succeeded.

No-change runs produce no analysis file, no state heartbeat, no commit and no notification.

## 10. State update

When write mode is enabled:

- update only `state/entity-observation.json`;
- increment revision only for a real state change;
- update target/profile states independently;
- retain the previous good state on profile failure;
- record bounded operational events;
- never alter jobs, profiles or target sets.

For material events, the State update must be committed atomically with both event files. A status or changed-error-state write may update only the State when the global state policy permits it.

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

- resolve every configured source binding through `source-binding-resolution.md`;
- use current dated ranking and market snapshots;
- keep independent sources independent;
- do not substitute an unconfigured provider silently;
- do not average incompatible source formats blindly;
- translate market changes into the actual league format;
- require profile thresholds or a documented tier change;
- distinguish role-driven movement from noise;
- record disagreement when sources move in opposite directions.

## Production readiness

Production execution requires all of the following:

1. a stored initial baseline for every active target/profile pair;
2. successful deterministic source-binding resolution;
3. a successful controlled atomic-write test;
4. `runner-config.json` in `write_enabled`;
5. the job definition enabled;
6. an external scheduled task or runner wakeup.

The repository controls job eligibility and writes. The external task only wakes the runner.
