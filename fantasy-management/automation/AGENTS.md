# Fantasy Automation Agent Instructions

This folder is the declarative control plane and retained automation contract area for recurring Fantasy Management automation.

These instructions apply to work under `fantasy-management/automation/` and to any scheduled or manually invoked process that reads automation jobs, profiles, target sets or State from the repository.

## Current production precedence

For current Fantasy Operations, `fantasy-management/_ai/FANTASY_OPERATIONS_ARCHITECTURE.md` is authoritative over older autonomous-runner execution instructions in this folder.

Current production rules include:

- scheduled Fantasy Operations monitoring is provider-neutral and read-only;
- the former autonomous Observation Bootstrap is disabled;
- missing persisted baselines do not authorize autonomous backfill or State publication;
- durable State, Knowledge, Decision, board, baseline or review writes require explicit human approval;
- approved qualitative entity-observation baselines are persisted interactively in `fantasy-management/automation/state/entity-observation.json` under the current Architecture;
- legacy runner, bootstrap, batch-writer and event-publication documents may remain as historical technical contracts but must not override the current Architecture or `runner-config.json`.

When a legacy workflow describes automatic State writing, automatic baseline backfill or publication-before-notification behavior that conflicts with the current Architecture, follow the current Architecture.

## Required reading order

1. `/AGENTS.md`
2. `fantasy-management/AGENTS.md`
3. `fantasy-management/_ai/FANTASY_MANAGEMENT_SOURCES.md`
4. `fantasy-management/_ai/FANTASY_MANAGEMENT_RULES.md`
5. `fantasy-management/_ai/FANTASY_OPERATIONS_ARCHITECTURE.md` for Fantasy Operations, scheduled monitoring, observation State or persistence work
6. this file
7. `fantasy-management/automation/README.md`
8. `fantasy-management/automation/runner-config.json`
9. enabled or otherwise relevant job definitions and their matching state files
10. job-specific workflows, schemas, configuration references, current repo data and current external sources

## Control-plane rule

The repository defines durable automation contracts. An external ChatGPT task or future technical scheduler only provides a wakeup or execution context.

Do not encode the complete job catalog, target sets, profiles, criteria, materiality rules or output paths only in a scheduled-task prompt. Keep durable job behavior in the repository.

The repository cannot dynamically reschedule the external task. Repo triggers determine job eligibility after a runner wakeup; they do not create the wakeup.

For the current provider-neutral monitoring architecture, the scheduled prompt may additionally define the read-only monitoring procedure and notification policy, but it must remain consistent with `FANTASY_OPERATIONS_ARCHITECTURE.md` and may not grant itself repository write authority.

## Managed-team identity

Use `managed_team` as the canonical neutral term for the fantasy team whose interests the automation optimizes.

- Resolve it from `runner-config.json`.
- Identify it by the stable configured team ID and identity field.
- Resolve the current display name from the configured league source at runtime.
- Never use a franchise display name as a durable key, path, schema enum, state key or automation perspective.
- A team-name change must not require job, target, profile or state migration.

`own_team` is avoided because ownership can be ambiguous in agent context. `master_team` is avoided because it is non-standard and semantically unclear. `managed_team` describes the operational relationship without depending on the current franchise name.

## Ownership

- `runner-config.json` owns global runner behavior and managed-team identity.
- `jobs/{job-id}.json` owns durable job intent and legacy/generic execution rules.
- `target-sets/{target-set-id}.json` owns manual targets and dynamic selectors.
- `profiles/{profile-id}.json` owns reusable signals, source policy and materiality criteria.
- `workflows/` owns job- and module-specific execution instructions and retained legacy mechanics.
- `state/{job-id}.json` owns mutable execution or approved comparison State for exactly one job.
- `public/data/` owns current league and generated application data.
- `fantasy-management/generated/operations/` owns deterministic provider-neutral Operations read models.
- `fantasy-management/analyses/` owns completed analysis outputs.

A scheduled read-only monitor must not update State or outputs. An explicitly approved interactive write may update only the approved State/output scope and must not rewrite its own job definition, global rules, profiles or target configuration unless the user explicitly requests that configuration change.

## Generic observation model

Observation automation separates five layers:

1. **Job**: wakeup eligibility, dependencies, allowed outputs and notification policy.
2. **Target set**: which entities are observed, manually or through selectors.
3. **Profile**: which signals and source standards apply.
4. **Criterion**: how a state change becomes material and how it is classified.
5. **Event/output or persisted baseline**: observation, interpretation, decision effect or approved comparison State.

Do not collapse these layers into one player-specific configuration file.

An entity type is extensible. Initial support includes player-oriented profiles, but the framework must allow later entities such as NFL teams, position groups, backfields, fantasy teams, draft picks, ranking sources, deadlines and league rules.

## Current scheduled-monitoring workflow

For current Fantasy Operations scheduled monitoring:

1. Read the required instructions and `FANTASY_OPERATIONS_ARCHITECTURE.md`.
2. Read the current provider-neutral Operations datasets and data-quality report.
3. Resolve `managed_team` and current roster/ownership context from repository data.
4. Read confirmed persisted baselines from the matching State where they exist.
5. Perform fresh external research where qualitative injury, availability, role or opportunity verification is required.
6. Compare current observations with approved persisted baselines and prior successful monitoring context.
7. Treat a first observation as an internal baseline and do not notify solely because it is new.
8. Still notify when a first-observed current state is already materially decision-relevant.
9. Do not autonomously run bootstrap, baseline backfill, Replacement-State-Writer, State checkpoint publication or Observation Event publication.
10. Send only new or materially changed notifications under the current monitoring policy.
11. Include the exact durable repository change that would be proposed after approval.
12. Leave the repository unchanged until explicit human approval.

## Legacy generic runner workflow

The following model is retained for historical generic-runner semantics and for future explicitly approved reactivation work. It is not current scheduled write behavior while `runner-config.json` is `read_only`.

For a generic runner wakeup:

1. Read the required instructions and global runner config.
2. Stop without executing jobs when the runner is disabled.
3. Resolve `managed_team` by stable ID from the configured source.
4. Discover job files according to `job_discovery`.
5. Validate the runner config, each discovered job, each matching state and all required configuration references.
6. Skip disabled jobs without changing their state unless a user explicitly requests state normalization.
7. Apply each job's optional active window and season-phase restrictions.
8. Evaluate the job's repo trigger against its state. Do not treat the external task schedule as proof that the job is due.
9. Resolve every required dependency and verify freshness or completion conditions.
10. Historically, write-enabled operation could mark an eligible job pending when required data was incomplete and the job allowed retry.
11. Build the job's idempotency key before generating output.
12. Skip output generation when the same key has already completed successfully and inputs have not materially changed.
13. Execute the job-specific workflow using current league data, current external context when required and the configured perspective.
14. Write only inside the job's `write_scope` and only when the current Architecture, runner mode and explicit approval all permit it.
15. Update only the matching state file when an approved write requires it, following the current State-persistence rules.
16. Notify according to the current Architecture and active monitoring policy rather than assuming legacy publication ordering.
17. Continue with independent jobs after a job error when `continue_on_job_error` is enabled.
18. Finish with a concise run summary when the active execution mode calls for one.

## Trigger rules

Supported trigger types are defined by `automation-job.schema.json`.

Interpret them as follows:

- `interval`: eligible only when the minimum interval since the relevant prior evaluation has elapsed.
- `calendar`: eligible only on configured weekdays and not before the configured local time.
- `league_week_finalized`: eligible only when the configured final-week field advanced beyond the last processed key and the dependent data is sufficiently fresh.
- `source_changed`: eligible only when the configured comparison detects a meaningful input change.
- `deadline_offset`: eligible once for each configured deadline offset and idempotency key.
- `manual`: never inferred as due; it requires an explicit manual invocation.

A trigger makes a legacy/generic job eligible. It does not grant repository write authority and does not override the current scheduled-monitoring architecture.

## Target-set rules

- Target sets may be `manual`, `dynamic` or `hybrid`.
- Manual targets carry stable target IDs and entity identifiers.
- Dynamic selectors are declarative. The workflow resolves them against current data at runtime.
- A target may use defaults from its target set and add or override profile bindings.
- A target may appear in multiple target sets. Identical target IDs must resolve to the same entity fingerprint.
- Merge profile bindings by profile ID and retain all contributing target-set IDs.
- Never persist a dynamically resolved list as configuration unless the user explicitly asks to convert it into a manual list.
- Expired or disabled targets are not researched when the active workflow uses those target-set activation rules.

## Profile and criterion rules

- Profiles are reusable across target sets.
- Profile applicability must include the entity type.
- Signals describe what is observed; they are not themselves recommendations.
- Source policy defines minimum confidence and independence requirements.
- Structured criteria determine materiality and classification.
- Target-level overrides may change thresholds but must not weaken mandatory source-safety rules without explicit configuration.
- Qualitative AI evaluation may interpret evidence, but it must return structured signal values before criteria are applied when those profile contracts are used.
- A single flattering quote, isolated clip or unsupported aggregator claim is not a material role change.

## Observation-state rules

For entity observation:

- State is stored per target and profile.
- Persisted approved qualitative baselines live in `state/entity-observation.json`.
- A baseline is silent unless the active monitoring policy explicitly permits an initial-state notification because the current state is itself materially relevant.
- Hash only normalized material state, not timestamps or prose formatting.
- Different profiles may succeed or fail independently.
- Do not erase the last good material state because one current source is unavailable.
- Record source fingerprints so unchanged evidence does not create duplicate events or alerts.
- Substantive history belongs in dated analyses/events when such storage is explicitly approved; operational comparison State stays bounded and structured.
- Missing persisted baselines do not authorize autonomous bootstrap or backfill.

## Observation-event rules

The historical event contract separates:

1. `observation`: what changed in the evidence and signals;
2. `interpretation`: what the change likely means and with what confidence;
3. `decision_effect`: what changes for the configured perspective.

For `managed_team` effects, resolve the current roster, ownership, league format, draft capital and relevant decisions from current repo data. Do not embed the current franchise name in paths or keys.

Current scheduled monitoring may deliver these layers directly in the notification without first persisting an Observation Event. Persist event files only when the current Architecture and explicit approval call for them.

## Data-readiness rules

- Read current league state from current repository data, not from prior analysis files.
- Check `public/data/Timestamps.json` when generated-data freshness matters.
- Use the current Fantasy Operations data-quality report before relying on prepared monitoring inputs.
- Do not infer completeness only from a frontend version or deployment timestamp.
- Treat missing, stale or internally conflicting required data as incomplete when the active data contract says it is blocking or material.
- Do not silently fill data gaps with assumptions.
- Do not create a final weekly report before the configured scored week and all required inputs are ready.

## State rules

- Keep exactly one state file per job.
- The state filename must match the job ID.
- Increment `revision` exactly once per complete real State change.
- Do not write heartbeat-only state changes.
- Keep `recent_events` bounded by the runner config.
- Store only operational comparison/history in State; store substantive conclusions in analyses when explicitly persisted.
- Preserve the last successful key and input fingerprints so reruns remain idempotent.
- Record retryable and non-retryable failures explicitly only when the active persistence policy calls for storing them.
- Use `job_state` only for job-specific operational state validated by a specific schema.
- An approved interactive State write must not falsely advance `last_successful_run` as though an autonomous runner completed.

## Write-safety rules

Runner modes remain defined as:

- `read_only`: no repository writes.
- `proposal`: describe exact proposed state and output changes without writing them.
- `write_enabled`: historically allowed writes inside configured scopes; current use still requires consistency with the current Architecture and explicit approval policy.

Always:

- avoid unrelated repository changes;
- never write Fantasy Management analysis into `public/data/`;
- never modify generated application data as an observation side effect;
- never change GitHub Actions workflows without explicit approval;
- never create daily no-op commits;
- never let one job write another job's state;
- never let a scheduled monitor alter target sets or profiles during normal execution;
- for approved State writes, pin the branch parent and current State blob, validate the complete replacement and publish only by non-forced fast-forward.

## Notification rules

Notifications must follow the current Architecture and active monitoring policy.

For material Fantasy Management changes, include when relevant:

- what changed;
- evidence and source freshness;
- previous known state;
- managed-team or league impact;
- updated recommendation or roster implication;
- confidence and unresolved conflicts;
- the exact durable change proposed for later approval.

Do not notify on no-change runs unless configuration explicitly permits it.

## Source and analysis rules

All Fantasy Management source and plausibility rules remain in force.

- Dynamic player roles, injuries, rankings, ADP, values and news require fresh external checks when material.
- Current ownership, format, roster, salary, draft and transaction context must come from current repo data.
- Stored analyses and states are historical comparison context, not unquestionable current truth.
- External sources supplement league data and must be translated into the actual six-team, fixed-2QB, fixed-2TE context.
- Recommendations for the managed team must be derived from the stable team identity, never from a hard-coded display name.

## Configuration changes

When adding or changing a job or reactivating legacy autonomous behavior:

1. validate the job against `automation-job.schema.json`;
2. create or update the same-ID state file when required;
3. keep new autonomous jobs disabled until their workflow, dependencies and outputs are complete;
4. document new reusable trigger, notification or output semantics before using them;
5. add new schemas to `fantasy-management/_ai/schema-list.json`;
6. create optional folders only when they contain real configuration or output files;
7. run `validate_automation.py` and its unit tests;
8. obtain explicit approval for any architecture change that would re-enable autonomous State publication or GitHub Actions behavior.
