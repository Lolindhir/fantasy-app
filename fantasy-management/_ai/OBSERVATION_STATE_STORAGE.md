# Entity Observation State Storage

## Status

This document is authoritative for durable approved qualitative `entity-observation` baseline storage. Scheduled Fantasy Operations monitoring remains read-only. Durable qualitative persistence still requires explicit human approval.

The former monolithic Target payload in `fantasy-management/automation/state/entity-observation.json` and the transitional Base + Overlay interpretation are retired. The path remains only as a bounded global State header for backward-compatible job/state discovery.

## Canonical storage model

The durable State consists of exactly two layers with distinct ownership:

1. Global bounded State header: `fantasy-management/automation/state/entity-observation.json`
2. One complete Target shard per persisted Target: `fantasy-management/automation/state/entity-observation-targets/{target_id}.json`

The global header preserves job-level metadata such as schema/job identity, historical revision, evaluation metadata, input fingerprints, recent events and target-set resolution metadata. Its `job_state.targets` object must always be empty. It is not a baseline payload store and is not touched by a normal approved Target/profile update.

All current qualitative baseline payloads live directly in Target shards. There is no Base fallback and no overlay precedence after the full-shard migration.

## Target shard contract

Each shard is canonical pretty UTF-8 JSON with one trailing newline and contains:

```json
{
  "schema_version": 1,
  "target_id": "managed-roster-player-8142",
  "base_state_revision": 17,
  "write_id": "interactive-approved-baseline:managed-roster-player-8142:2026-08-30",
  "updated_at": "2026-08-30T09:22:00Z",
  "target": {
    "entity_fingerprint": "player:sleeper_id:8142",
    "target_set_ids": ["managed-roster-health"],
    "last_checked_at": "2026-08-30T09:22:00Z",
    "status": "active",
    "observations": {}
  }
}
```

The example is structural only. A real shard contains the complete Target and all of its persisted observations.

`base_state_revision` is retained as the migration-anchor revision for wrapper compatibility. It must equal the current global State-header revision. Normal Target-shard writes do not increment the global revision.

## Effective State

For consumers that still need the legacy in-memory shape:

1. read the global State header;
2. require `job_state.targets == {}`;
3. read every canonical Target shard;
4. populate an in-memory `job_state.targets[target_id]` map from those shards.

No consumer may treat absence of a shard as permission to recover a Target payload from Git history, an old monolith, connector cache or another fallback.

## Approved write rules

For an approved qualitative Target/profile update:

1. Read `entity-observation-targets/{target_id}.json` when it exists.
2. Treat that shard as the complete current durable Target state.
3. Modify only the explicitly approved Target/profile scope.
4. Preserve every unrelated observation in that Target.
5. Recalculate changed `state_hash` values with canonical compact sorted-JSON SHA-256 semantics.
6. Preserve the stable `entity_fingerprint`; an identity change fails closed.
7. Preserve the migration-anchor `base_state_revision` unless a separately approved storage-schema migration changes it.
8. Set a deterministic descriptive `write_id` for the approved logical write.
9. Write only that Target shard for a normal Target/profile update.
10. Validate the global header plus all shards before publication.
11. Pin the current Target-shard blob when replacing an existing shard and publish only non-forced/fast-forward.

A normal approved baseline update must not rewrite `entity-observation.json`.

## Validation

Canonical validator:

```text
fantasy-management/_ai/scripts/validate_observation_state_shards.py
```

It validates canonical formatting, the bounded header invariant, shard structure, filename/Target identity, revision-anchor compatibility, unique write IDs, unique entity fingerprints, Target shape and target-set references. It can materialize the legacy in-memory State shape with `--dump-merged` for compatibility consumers.

`CI • Fantasy Management` runs the unit-test suite, validates the bounded header formatting, and validates the complete full-shard State.

## Migration provenance

The full-shard migration was built from the effective pre-migration Base + Overlay State and was required to round-trip exactly before publication. The migration contained 22 persisted Targets. The already approved Alec Pierce Target shard was preserved as the newer effective Target; the remaining 21 shards were generated deterministically from the legacy State.

The verified effective pre-migration canonical-State SHA-256 was:

```text
41deb08044c0bbe71ca5f8f0ff541c9567249ee865950468dd95acf64683a790
```

The old large Target payload remains recoverable from Git history, so no separate active archive copy is required.

## Superseded behavior

The following are historical only and must not be used as active persistence instructions:

- complete replacement of the former monolithic `entity-observation.json` Target payload;
- Base + Target-Overlay resolution;
- autonomous Observation Bootstrap State checkpoints;
- the legacy complete Replacement-State Writer as the normal interactive persistence path.
