# Entity Observation Workflow

Purpose: apply reusable observation profiles to configurable entities without coupling the observation model to players, one watchlist or one franchise display name.

## Current operating status

This document contains two things that must be kept separate:

1. the still-reused **entity-observation contract** for target identity, profile normalization, material-state hashing, evidence quality and persisted approved baselines;
2. the **former autonomous runner execution model**, which is now legacy.

`fantasy-management/_ai/FANTASY_OPERATIONS_ARCHITECTURE.md` is authoritative for current production behavior. The scheduled Fantasy Operations monitoring is read-only. It must not autonomously run baseline backfill, the Observation Bootstrap, the Replacement-State-Writer, State-only checkpoints or Observation Event publication.

The canonical persisted approved qualitative baseline State remains:

```text
fantasy-management/automation/state/entity-observation.json
```

A durable change to that State happens only after explicit human approval and is performed interactively with full State validation and optimistic-concurrency safeguards.

Historically, the first manual baseline and controlled atomic-write test made the generic runner eligible for `write_enabled` production execution. PR #94 later deliberately returned the runner to `read_only` and disabled autonomous bootstrap as part of the provider-neutral migration. The historical mechanics below remain documented where useful, but they do not override the current Architecture or `runner-config.json`.

## Inputs

- `fantasy-management/automation/runner-config.json`
- `fantasy-management/automation/jobs/entity-observation.json`
- all required `configuration_refs`
- `fantasy-management/automation/state/entity-observation.json`
- current repository data under `public/data/`
- current provider-neutral Operations datasets when applicable;
- fresh external sources required by each profile.

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

## 3. Determine targets and profiles

The target/profile model remains useful for deciding what can be compared and how. The old autonomous runner additionally used job cadence, deep-evaluation budgets and a persisted missing-baseline queue. Those queue-management rules are legacy and are not a scheduled-monitoring write policy today.

### 3.1 Legacy deep-evaluation budget

The former runner limited one wakeup to at most **12 target/profile pairs** for deep evaluation.

Of those 12 slots:

- at most **8** could be used for previously missing initial baselines;
- remaining capacity was reserved first for already-baselined pairs whose relevant input fingerprints changed;
- unused reserved capacity could be used for additional retryable pairs, while the total remained 12.

A pair did not consume the deep-evaluation budget when all relevant reusable input fingerprints were unchanged and the profile workflow permitted a deterministic unchanged result without new player-specific research.

This budget is historical runner behavior. Current scheduled monitoring may prioritize research from the provider-neutral prepared datasets and the task's explicit monitoring rules instead.

### 3.2 Legacy deterministic pair ordering

The former autonomous candidate queue used this order:

1. already-baselined pairs with changed relevant input fingerprints or a concrete current change signal;
2. missing or `never_checked` profile states;
3. retryable `pending` profile states;
4. retryable `failed` profile states.

Within each bucket it sorted by target priority, target ID and profile ID.

This ordering remains useful historical context but does not authorize autonomous persistence.

### 3.3 Legacy incremental baseline backfill

The old write-enabled runner treated a missing baseline backlog as normal operational work and could persist bounded batches across scheduled wakeups.

That behavior is no longer active. Under the current Architecture:

- missing persisted baselines do not block scheduled monitoring;
- missing baselines do not activate Bootstrap or State-only checkpoint publication;
- scheduled monitoring may form an internal first-observation baseline for the current run;
- first observation alone is silent;
- a currently observed state may still be reported immediately when it is already materially decision-relevant;
- durable baseline persistence requires explicit approval.

The earlier `pending` backfill mechanics remain historical runner documentation only.

### 3.4 Pending and failed evidence

When a current evaluation cannot meet mandatory source confidence:

1. preserve a previous good material state when one exists;
2. do not replace a good baseline with unsupported assumptions;
3. surface a new or materially changed technical/evidence problem only when notification rules justify it;
4. do not repeatedly notify an unchanged retryable problem.

The historical runner could persist `pending` or `failed` operational states. Scheduled read-only monitoring does not autonomously persist those transitions.

## 4. Collect evidence

For each selected target/profile pair:

1. Read the profile signals and source policy.
2. Resolve current league context from repository data.
3. Use current provider-neutral materialized inputs where applicable.
4. Fetch fresh external evidence when required.
5. Resolve configured source bindings before using alternative sources when those bindings remain relevant.
6. Prefer primary or authoritative sources for qualitative role evidence.
7. Record source type, publisher, observed time and supported signals.
8. Deduplicate syndicated reports and articles that originate from the same source.
9. Separate direct facts from reporter interpretation and model inference.
10. Preserve source conflicts rather than silently reconciling them.
11. Fail the profile check when mandatory source confidence cannot be met.
12. Keep the previous good material state when current evidence is incomplete.

Batch source work whenever the profile permits it:

- load each current repo file once per run;
- load each configured ranking, ADP, projection or external-signal dataset once per run;
- join all selected players against the same loaded dataset;
- reuse official team, transaction, injury-report or position-group evidence for multiple selected players only when it actually supports each player-specific signal;
- perform deep player-specific web research only for missing qualitative context, changed inputs or concrete change signals.

## 5. Normalize signals

Return the configured signal IDs with stable value types.

Do not include:

- fetch timestamps in the material state;
- prose-only restatements of unchanged values;
- source URLs in the material-state hash;
- speculative values not supported by evidence.

The normalized material state contains only fields listed in the profile's `output_fields` plus explicitly approved structured support fields.

Serialize normalized material state with deterministic JSON semantics before hashing:

- UTF-8;
- object keys sorted recursively;
- compact separators;
- no insignificant whitespace;
- no timestamps or source URLs unless an output field explicitly makes them material.

Use SHA-256 over those canonical UTF-8 bytes for `state_hash`.

These normalization and hashing semantics remain active for approved interactive baseline persistence.

## 6. Evaluate criteria

1. Apply target overrides to profile defaults when applicable.
2. Evaluate atomic and grouped criteria.
3. Use profile source policy as a mandatory gate.
4. A criterion classification describes the type of material change.
5. Multiple matching criteria may be combined when they describe the same underlying change.
6. Use the highest justified severity.
7. A recommendation change cannot make weak evidence material by itself.

Supported operators are defined in `automation-criterion.schema.json`.

## 7. Baseline and comparison

### Current scheduled-monitoring behavior

When no previous persisted profile state exists:

1. treat the current successful observation as an internal comparison baseline for the run;
2. do not notify merely because the pair was observed for the first time;
3. do not persist it automatically;
4. still notify when the current state itself is clearly materially decision-relevant under the current monitoring rules;
5. propose the exact durable baseline change when persistence would prevent duplicate future notifications;
6. persist only after explicit human approval.

For later checks against a persisted approved state:

1. normalize and hash the current material state;
2. compare it to the stored state hash and actual semantic fields;
3. treat an identical material state as unchanged;
4. apply materiality criteria to actual signal changes;
5. notify only when a new or materially changed development meets the current notification policy.

### Historical autonomous-runner behavior

The former write-enabled runner automatically stored a successful missing baseline and marked it `baseline`. That automatic persistence behavior is legacy and is not part of scheduled production monitoring.

## 8. Separate observation, interpretation and decision effect

Every material development should keep three distinct layers.

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
3. apply relevant effect rules;
4. state whether action changes and how urgently;
5. use the current franchise name only in prose when helpful.

## 9. Output and notification

### Current scheduled-monitoring behavior

A scheduled monitoring notification is external output and does not itself modify repository State or create an Observation Event bundle.

When a new material development is found:

- notify according to the current monitoring task and Architecture;
- include the proposed durable repository change;
- do not write State, JSON events or Markdown events before approval;
- do not repeat an unchanged already-known state.

No-change runs remain silent and produce no repository heartbeat.

### Historical autonomous event publication

The former write-enabled runner produced matching Markdown and JSON under:

```text
fantasy-management/analyses/{season}/observation-events/
```

and published State + JSON event + Markdown event atomically through `atomic-publication.md` before notifying.

That autonomous event-publication ordering is legacy. The event schema and atomic-publication workflow remain historical contracts and may still be used if a future explicitly approved stored event workflow requires them.

## 10. Human-approved State update

After explicit approval, an interactive qualitative baseline write may update:

```text
fantasy-management/automation/state/entity-observation.json
```

For that write:

- persist only the approved target/profile scope;
- increment revision exactly once for the complete logical State change;
- preserve unrelated previous good states and input fingerprints;
- retain previous good material state on unresolved evidence rather than inventing a replacement;
- calculate every changed `state_hash` from canonical normalized JSON;
- validate the complete replacement State against `automation-observation-state.schema.json` and `validate_automation.py` cross-file rules;
- pin the expected target-branch parent commit SHA and current State blob SHA;
- publish only by non-forced fast-forward;
- discard and recompute on concurrency conflict;
- do not alter jobs, profiles, target sets or generated data as a side effect.

An approved interactive baseline write is not an autonomous runner execution and must not advance `last_successful_run` merely because persistence succeeded.

The historical Replacement-State-Writer and Bootstrap checkpoint path are not invoked automatically by scheduled monitoring.

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

- prefer the current provider-neutral prepared market signals when available;
- use current dated ranking and market snapshots when source-level verification is needed;
- keep independent sources independent;
- do not substitute an unconfigured provider silently;
- do not average incompatible source formats blindly;
- translate market changes into the actual league format;
- require profile thresholds or a documented tier change;
- distinguish role-driven movement from noise;
- record disagreement when sources move in opposite directions.

## Current production readiness

Current scheduled monitoring does **not** require every active target/profile pair to have a persisted baseline. It requires:

1. current provider-neutral prepared inputs and their quality report to be usable for the requested scope;
2. current repository identity and ownership context to resolve the relevant player;
3. fresh external verification where qualitative injury, availability, role or opportunity evidence is required;
4. read-only execution for the scheduled run;
5. comparison against approved persisted baselines where they exist;
6. explicit human approval before any durable repository write.

## Legacy autonomous production readiness

The former autonomous runner additionally required `runner-config.json` in `write_enabled`, an enabled job, automatic baseline-backfill mechanics, controlled atomic-write testing and an external wakeup. Those requirements document the retired autonomous write path and are not conditions for current scheduled monitoring.
