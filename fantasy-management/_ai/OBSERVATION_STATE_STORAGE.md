# Entity Observation State Storage

## Status

This document is authoritative for the durable storage layout of approved qualitative `entity-observation` baselines. It supersedes older procedural text that requires every approved baseline change to replace the complete `fantasy-management/automation/state/entity-observation.json` file.

Scheduled Fantasy Operations monitoring remains read-only. Durable qualitative baseline persistence still requires explicit human approval.

## Storage model

The effective state has two layers:

1. Base snapshot: `fantasy-management/automation/state/entity-observation.json`
2. Target overlays: `fantasy-management/automation/state/entity-observation-targets/{target_id}.json`

The base snapshot contains all approved state that existed at migration time and is retained losslessly. It is no longer the normal write target for qualitative baseline changes.

A target overlay replaces exactly one `job_state.targets[target_id]` object from the base snapshot. A target that did not exist in the base may also be introduced by a shard when its configured target identity is otherwise valid.

The effective target map is produced by loading the base and then applying all target shards in deterministic filename order. Because target IDs map one-to-one to filenames, there can be at most one active shard per target.

## Target shard contract

Each file is pretty-printed UTF-8 JSON with one trailing newline:

```json
{
  "schema_version": 1,
  "target_id": "alec-pierce-2026",
  "base_state_revision": 17,
  "write_id": "interactive-approved-baseline:alec-pierce-2026:2026-08-30",
  "updated_at": "2026-08-30T00:00:00Z",
  "target": {
    "entity_fingerprint": "player:sleeper_id:8142",
    "target_set_ids": ["managed-roster-health"],
    "last_checked_at": "2026-08-30T00:00:00Z",
    "status": "active",
    "observations": {}
  }
}
```

The example is structural only; an actual shard must contain the complete validated target and its complete observation objects.

## Write rules

For an approved baseline update:

1. Read the base target and an existing shard for that target, if present.
2. Treat the existing shard as the current target state; otherwise use the base target.
3. Modify only the explicitly approved target/profile scope.
4. Preserve unrelated profile states in that target.
5. Recalculate changed `state_hash` values using the existing canonical compact sorted-JSON SHA-256 contract.
6. Keep the stable `entity_fingerprint`; an identity change fails closed.
7. Set a deterministic, descriptive `write_id` for the approved logical write.
8. Write only `entity-observation-targets/{target_id}.json`.
9. Validate Base + all shards before publication.
10. Pin the current target-shard blob when replacing an existing shard and publish only non-forced/fast-forward.

A normal approved target/profile update must not rewrite the large base snapshot.

## Revision and processed-state semantics

The base file's global `revision`, `last_processed_key`, `recent_events` and other historical job-level metadata are migration-time legacy metadata. They are not advanced by target-shard persistence.

Shard persistence is identified by the target path plus `write_id`. Repeating an already-persisted logical write with identical target content is a no-op. A later approved update to the same target replaces that target's shard and receives a new `write_id`.

This separation is intentional because current scheduled monitoring is read-only; there is no autonomous checkpoint queue whose progress needs a globally incremented observation-state revision.

## Validation

Canonical validator:

```text
fantasy-management/_ai/scripts/validate_observation_state_shards.py
```

It validates the base formatting, every shard's structure and formatting, filename/target identity, base-revision compatibility, duplicate write IDs, target shape and immutable base identity. It can also materialize a merged effective state for consumers that still need the legacy in-memory shape.

`CI • Fantasy Management` runs both the unit-test suite and the productive Base + Shard validator.

## Migration safety

This is an overlay migration rather than a destructive split of the existing large file. Therefore:

- no approved legacy baseline is copied by hand or dropped;
- rollback is immediate by ignoring/removing shards and returning to the untouched base snapshot;
- connector truncation of the base body can never justify a replacement write;
- all new normal writes are bounded to one target-sized file;
- readers can materialize the complete effective state deterministically when needed.

## Superseded legacy behavior

Any active documentation that still describes `apply_observation_state_batch.py` or a complete replacement of `entity-observation.json` as the normal approved interactive persistence path is historical for storage purposes. The current scheduled architecture remains read-only, and approved interactive qualitative persistence uses this Base + Target-Shard contract.
