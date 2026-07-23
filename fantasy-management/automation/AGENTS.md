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
9. job-specific workflows, schemas, current repo data and current external sources

## Control-plane rule

The repository defines what automation should do. An external ChatGPT task or future technical scheduler only wakes the runner.

Do not encode the complete job catalog, watch targets, materiality rules or output paths only in a scheduled-task prompt. Keep durable job behavior in the repository.

The repository cannot dynamically reschedule the external task. Repo triggers determine job eligibility after a runner wakeup; they do not create the wakeup.

## Ownership

- `runner-config.json` owns global runner behavior.
- `jobs/{job-id}.json` owns durable job intent and execution rules.
- `state/{job-id}.json` owns mutable execution state for exactly one job.
- `public/data/` owns current league and generated application data.
- `fantasy-management/analyses/` owns completed analysis outputs.
- job-specific target lists may be added later under `automation/targets/` when real target files exist.

A runner may update state and permitted outputs. It must not rewrite its own job definition, global rules or target configuration unless the user explicitly requests that configuration change.

## Runner workflow

For every runner wakeup:

1. Read the required instructions and global runner config.
2. Stop without executing jobs when the runner is disabled.
3. Discover job files according to `job_discovery`.
4. Validate the runner config, each discovered job and each matching state against the registered schemas.
5. Skip disabled jobs without changing their state unless a user explicitly requests state normalization.
6. Apply each job's optional active window and season-phase restrictions.
7. Evaluate the job's repo trigger against its state. Do not treat the external task schedule as proof that the job is due.
8. Resolve every required dependency and verify freshness or completion conditions.
9. Mark an eligible job as pending rather than producing a partial result when required data is incomplete and the job allows retry.
10. Build the job's idempotency key before generating output.
11. Skip output generation when the same key has already completed successfully and inputs have not materially changed.
12. Execute the job-specific workflow using current league data, current external context when required and the configured perspective.
13. Write only inside the job's `write_scope` and only when the runner mode permits it.
14. Update only the matching state file, following the global state-write policy.
15. Notify according to the job rule and bundle notifications when the global config requires it.
16. Continue with independent jobs after a job error when `continue_on_job_error` is enabled.
17. Finish with a concise run summary covering completed, skipped, pending and failed jobs.

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
- never let one job write another job's state.

## Notification rules

Notifications must follow the configured mode and severity threshold.

For material Fantasy Management changes, include when relevant:

- what changed;
- evidence and source freshness;
- previous known state;
- Mighty Giants or league impact;
- updated recommendation;
- confidence and unresolved conflicts.

Do not notify on no-change runs unless configuration explicitly permits it.

## Source and analysis rules

All Fantasy Management source, plausibility and Mighty Giants rules remain in force.

- Dynamic player roles, injuries, rankings, ADP, values and news require fresh external checks when material.
- Current ownership, format, roster, salary, draft and transaction context must come from current repo data.
- Stored analyses and states are historical context, not current truth.
- External sources supplement league data and must be translated into the six-team, fixed-2QB, fixed-2TE context.

## Configuration changes

When adding or changing a job:

1. validate the job against `automation-job.schema.json`;
2. create or update the same-ID state file;
3. keep new jobs disabled until their workflow, dependencies and outputs are complete;
4. document new reusable trigger, notification or output semantics before using them;
5. add new schemas to `fantasy-management/_ai/schema-list.json`;
6. create optional folders only when they contain real configuration or output files.
