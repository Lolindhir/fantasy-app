# Fantasy Automation Agent Instructions

This folder is the declarative control plane for recurring Fantasy Management automation.

These instructions apply to work under `fantasy-management/automation/` and to any scheduled or manually invoked runner that reads automation jobs from the repository.

## Required reading order

1. `/AGENTS.md`
2. `fantasy-management/AGENTS.md`
3. `fantasy-management/_ai/FANTASY_MANAGEMENT_SOURCES.md`
4. `fantasy-management/_ai/FANTASY_MANAGEMENT_RULES.md`
5. this file
6. `fantasy-management/automation/README.md`
7. `fantasy-management/automation/runner-config.json`
8. enabled job definitions and their matching state files
9. job-specific workflows, schemas, configuration references, current repo data and current external sources

## Control-plane rule

The repository defines what automation should do. An external ChatGPT task or future technical scheduler only wakes the runner.

Do not encode the complete job catalog, target sets, profiles, criteria, materiality rules or output paths only in a scheduled-task prompt. Keep durable job behavior in the repository.

The repository cannot dynamically reschedule the external task. Repo triggers determine job eligibility after a runner wakeup; they do not create the wakeup.

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
- `jobs/{job-id}.json` owns durable job intent and execution rules.
- `target-sets/{target-set-id}.json` owns manual targets and dynamic selectors.
- `profiles/{profile-id}.json` owns reusable signals, source policy and materiality criteria.
- `workflows/` owns job- and module-specific execution instructions.
- `state/{job-id}.json` owns mutable execution state for exactly one job.
- `public/data/` owns current league and generated application data.
- `fantasy-management/analyses/` owns completed analysis outputs.

A runner may update state and permitted outputs. It must not rewrite its own job definition, global rules, profiles or target configuration unless the user explicitly requests that configuration change.

## Generic observation model

Observation automation separates five layers:

1. **Job**: wakeup eligibility, dependencies, allowed outputs and notification policy.
2. **Target set**: which entities are observed, manually or through selectors.
3. **Profile**: which signals and source standards apply.
4. **Criterion**: how a state change becomes material and how it is classified.
5. **Event/output**: observation, interpretation and decision effect.

Do not collapse these layers into one player-specific configuration file.

An entity type is extensible. Initial support includes player-oriented profiles, but the framework must allow later entities such as NFL teams, position groups, backfields, fantasy teams, draft picks, ranking sources, deadlines and league rules.

## Runner workflow

For every runner wakeup:

1. Read the required instructions and global runner config.
2. Stop without executing jobs when the runner is disabled.
3. Resolve `managed_team` by stable ID from the configured source.
4. Discover job files according to `job_discovery`.
5. Validate the runner config, each discovered job, each matching state and all required configuration references.
6. Skip disabled jobs without changing their state unless a user explicitly requests state normalization.
7. Apply each job's optional active window and season-phase restrictions.
8. Evaluate the job's repo trigger against its state. Do not treat the external task schedule as proof that the job is due.
9. Resolve every required dependency and verify freshness or completion conditions.
10. Mark an eligible job as pending rather than producing a partial result when required data is incomplete and the job allows retry.
11. Build the job's idempotency key before generating output.
12. Skip output generation when the same key has already completed successfully and inputs have not materially changed.
13. Execute the job-specific workflow using current league data, current external context when required and the configured perspective.
14. Write only inside the job's `write_scope` and only when the runner mode permits it.
15. Update only the matching state file, following the global state-write policy.
16. Notify according to the job rule and bundle notifications when the global config requires it.
17. Continue with independent jobs after a job error when `continue_on_job_error` is enabled.
18. Finish with a concise run summary covering completed, skipped, pending and failed jobs.

## Trigger rules

Supported trigger types are defined by `automation-job.schema.json`.

Interpret them as follows:

- `interval`: eligible only when the minimum interval since the relevant prior evaluation has elapsed.
- `calendar`: eligible only on configured weekdays and not before the configured local time.
- `league_week_finalized`: eligible only when the configured final-week field advanced beyond the last processed key and the dependent data is sufficiently fresh.
- `source_changed`: eligible only when the configured comparison detects a meaningful input change.
- `deadline_offset`: eligible once for each configured deadline offset and idempotency key.
- `manual`: never inferred as due; it requires an explicit manual invocation.

A trigger makes a job eligible. Dependencies and idempotency still decide whether it may execute.

## Target-set rules

- Target sets may be `manual`, `dynamic` or `hybrid`.
- Manual targets carry stable target IDs and entity identifiers.
- Dynamic selectors are declarative. The workflow resolves them against current data at runtime.
- A target may use defaults from its target set and add or override profile bindings.
- A target may appear in multiple target sets. Identical target IDs must resolve to the same entity fingerprint.
- Merge profile bindings by profile ID and retain all contributing target-set IDs.
- Never persist a dynamically resolved list as configuration unless the user explicitly asks to convert it into a manual list.
- Expired or disabled targets are not researched.

## Profile and criterion rules

- Profiles are reusable across target sets.
- Profile applicability must include the entity type.
- Signals describe what is observed; they are not themselves recommendations.
- Source policy defines minimum confidence and independence requirements.
- Structured criteria determine materiality and classification.
- Target-level overrides may change thresholds but must not weaken mandatory source-safety rules without explicit configuration.
- Qualitative LLM evaluation may interpret evidence, but it must return structured signal values before criteria are applied.
- A single flattering quote, isolated clip or unsupported aggregator claim is not a material role change.

## Observation-state rules

For entity observation:

- State is stored per target and profile.
- The first successful check creates a baseline.
- A baseline is silent unless the target set enables `notify_on_initial_baseline`.
- Hash only normalized material state, not timestamps or prose formatting.
- Different profiles may succeed or fail independently.
- Do not erase the last good material state because one current source is unavailable.
- Record source fingerprints so unchanged evidence does not create duplicate events.
- Substantive history belongs in dated observation-event analyses, not the operational state.

## Observation-event rules

Every material observation event separates:

1. `observation`: what changed in the evidence and signals;
2. `interpretation`: what the change likely means and with what confidence;
3. `decision_effect`: what changes for the configured perspective.

For `managed_team` effects, resolve the current roster, ownership, league format, draft capital and relevant decisions from current repo data. Do not embed the current franchise name in paths or keys.

## Data-readiness rules

- Read current league state from current repository data, not from prior analysis files.
- Check `public/data/Timestamps.json` when generated-data freshness matters.
- Do not infer completeness only from a frontend version or deployment timestamp.
- Treat missing, stale or internally conflicting required data as incomplete.
- Do not silently fill data gaps with assumptions.
- Do not create a final weekly report before the configured scored week and all required inputs are ready.

## State rules

- Keep exactly one state file per job.
- The state filename must match the job ID.
- Increment `revision` only when the state file is actually changed.
- Do not write heartbeat-only state changes.
- Keep `recent_events` bounded by the runner config.
- Store only operational history in state; store substantive conclusions in analyses.
- Preserve the last successful key and input fingerprints so reruns remain idempotent.
- Record retryable and non-retryable failures explicitly.
- Use `job_state` only for job-specific operational state validated by a specific schema.

## Write-safety rules

Runner modes:

- `read_only`: no repository writes.
- `proposal`: describe exact proposed state and output changes without writing them.
- `write_enabled`: write only to paths allowed by both the global config and the job's `write_scope`.

Always:

- avoid unrelated repository changes;
- never write Fantasy Management analysis into `public/data/`;
- never modify generated application data as an automation side effect;
- never change GitHub Actions workflows without explicit approval;
- never create daily no-op commits;
- never let one job write another job's state;
- never let a runner alter target sets or profiles during normal execution.

## Notification rules

Notifications must follow the configured mode and severity threshold.

For material Fantasy Management changes, include when relevant:

- what changed;
- evidence and source freshness;
- previous known state;
- managed-team or league impact;
- updated recommendation;
- confidence and unresolved conflicts.

Do not notify on no-change runs unless configuration explicitly permits it.

## Source and analysis rules

All Fantasy Management source and plausibility rules remain in force.

- Dynamic player roles, injuries, rankings, ADP, values and news require fresh external checks when material.
- Current ownership, format, roster, salary, draft and transaction context must come from current repo data.
- Stored analyses and states are historical context, not current truth.
- External sources supplement league data and must be translated into the actual six-team, fixed-2QB, fixed-2TE context.
- Recommendations for the managed team must be derived from the stable team identity, never from a hard-coded display name.

## Configuration changes

When adding or changing a job:

1. validate the job against `automation-job.schema.json`;
2. create or update the same-ID state file;
3. keep new jobs disabled until their workflow, dependencies and outputs are complete;
4. document new reusable trigger, notification or output semantics before using them;
5. add new schemas to `fantasy-management/_ai/schema-list.json`;
6. create optional folders only when they contain real configuration or output files;
7. run `validate_automation.py` and its unit tests.
