# Atomic Publication Workflow

Purpose: publish a material Fantasy Management observation without allowing partial state, duplicate events or concurrent overwrites.

This workflow is mandatory whenever a write-enabled runner publishes an `entity-observation` material-change bundle.

## Scope

A material observation bundle contains exactly:

1. the updated matching job state;
2. the JSON observation event;
3. the matching Markdown observation event.

All three artifacts belong to one logical publication and must be committed together.

State-only writes remain permitted only for a real status transition, a changed error state or another state-write reason explicitly allowed by `runner-config.json`. No-change evaluations do not write state.

## 1. Read and pin the current repository state

Before preparing a write:

1. resolve the current target branch, normally `main`;
2. record its current commit SHA as `expected_parent_sha`;
3. read the current blob SHA of `fantasy-management/automation/state/entity-observation.json`;
4. retain that blob SHA as `expected_state_blob_sha`;
5. build the evaluation from this exact repository version.

Do not publish from a stale state snapshot.

## 2. Build the complete bundle before publishing

For a material event:

1. normalize and hash the new material state;
2. create the JSON event and validate it against `automation-observation-event.schema.json`;
3. create the matching Markdown event from the same observation;
4. update the state with the same classification, severity, event time and material-state hash;
5. validate the updated state against `automation-observation-state.schema.json`;
6. verify that all output paths are inside the job's `execution.write_scope`;
7. verify that no configuration file, profile, target set, workflow or file under `public/data/` is included.

The JSON event is the structured contract. The Markdown event is the human-readable representation of the same event. They must not disagree.

## 3. Publish atomically

Create one Git tree based on `expected_parent_sha` containing every changed path in the bundle.

Create one commit whose parent is exactly `expected_parent_sha`.

Move the target branch to that commit only as a non-forced fast-forward.

Never publish the state and event files through separate commits.

## 4. Optimistic concurrency

Immediately before moving the branch ref:

1. confirm that the target branch still points to `expected_parent_sha`;
2. confirm that the state file still has `expected_state_blob_sha`.

When either value changed:

- do not force the ref;
- do not merge the prepared state automatically;
- do not publish a partial bundle;
- discard the prepared write;
- reload the current branch and state;
- reevaluate on the next permitted attempt.

A concurrent unrelated commit is also treated as a conflict. Safety is preferred over publishing against an unreviewed parent.

## 5. No-op and non-material behavior

When no material criterion matches:

- create no event;
- create no commit;
- send no notification;
- do not update timestamps merely to record a heartbeat.

When the normalized material state changes but no criterion is material, retain the previous material baseline unless a future profile explicitly defines a different non-material-state policy.

## 6. Failure behavior

If validation, tree creation, commit creation or ref movement fails:

- consider the publication unsuccessful;
- do not claim that state or events were stored;
- do not send a success notification;
- preserve the last good state on the target branch;
- report the failure according to the configured error-state policy.

If a commit object was created but the branch ref was not moved, it is not a published runner result.

## 7. Notification ordering

Send a material-change notification only after the branch ref update succeeded and the committed bundle is readable from the target branch.

A notification must identify the committed event and must not precede repository publication.

## 8. Idempotency

The event identity is derived from:

```text
target_id + profile_id + material_state_hash
```

Before publishing, verify that the same successful idempotency key and event path do not already exist on the target branch.

Repeated evidence with an identical material-state hash creates no duplicate event or commit.
