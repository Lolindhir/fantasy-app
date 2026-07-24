# Observation Source Binding Resolution

Purpose: make repeated observation runs deterministic by binding profile signals to stable providers, datasets, access paths and field mappings.

## Binding precedence

1. A profile with `source_bindings` must use those bindings.
2. The runner must not substitute another provider or dataset merely because it is easier to access.
3. A required binding that cannot be resolved makes the affected profile incomplete.
4. The previous good profile state remains intact when a required binding is unavailable.
5. A different provider may be added only through an explicit profile change or target-level binding override supported by a later schema version.

## Resolution steps

For each binding:

1. Validate the binding and referenced signal IDs.
2. Resolve `access.location` according to `access.type`.
3. For `repo_latest_pointer`, read the pointer and then the exact referenced snapshot.
4. Apply `selection_policy`; never choose an older or alternate dataset silently.
5. Verify freshness according to `freshness_policy`.
6. Resolve the entity using `entity_join` in declared order.
7. Read only the declared `signal_mappings`.
8. Normalize each mapped field to the declared signal `value_type`.
9. Preserve provider, dataset, snapshot timestamp and source fingerprint outside the material-state hash.
10. Deduplicate sources by `independence_group`.
11. Fail the profile check when a required binding is missing, stale beyond policy without a successful refresh, cannot resolve the entity or cannot normalize a mapped value.

## Roles

- `primary`: authoritative source for the mapped signal. A signal may have at most one primary binding.
- `supporting`: corroborates or contextualizes a signal but does not replace its primary value.
- `derived`: computes a signal from already resolved bindings and has no external location.

## Field mappings and normalization

`signal_mappings` maps a normalized signal ID to one exact source field. The target signal's `value_type` controls normalization.

- `integer`: accept a real integer or a documented rank form such as `RB55`, from which the trailing numeric rank is extracted.
- `number`: parse a numeric value without changing its scale.
- `string`: normalize to a stable string without changing its meaning.
- `enum`: accept only values declared in `allowed_values`.
- `boolean`: accept only documented boolean forms.
- `list` and `object`: preserve structured values after schema-compatible normalization.
- A share-valued signal remains in the `0..1` range. The runner must not guess whether an undocumented number is a percentage.

A failed normalization leaves the mapped signal unresolved. The runner must not silently coerce malformed source data.

## Deterministic market mapping

The initial market profile binds:

- FantasyPros `dynasty-superflex-ppr` to dynasty overall rank, position rank and FantasyPros tier.
- FantasyCalc `dynasty-superflex-ppr-8-team` to market value and roster rate.
- A derived cross-source binding to source disagreement and evidence confidence.

FantasyPros and FantasyCalc remain independent signals. Their raw ranks, tiers and values must not be averaged because they measure different concepts and use different formats.

## Material-state hashing

Provider names, dataset IDs and normalized signal values belong in the reproducible observation context. Fetch timestamps, URLs and snapshot paths do not belong in the material-state hash when the normalized values are unchanged.

A provider or dataset change is a configuration change, not a player event. Establish a new baseline or run an explicit migration when bindings change.

## Qualitative role usage

`role.first_team_usage_class` supports practice evidence that cannot honestly be expressed as a numeric share.

Allowed ordered classes:

1. `unknown`
2. `none`
3. `occasional`
4. `rotational`
5. `majority`
6. `exclusive`

Rules:

- `unknown` means the evidence is insufficient; it is not equivalent to `none`.
- Use a class only when the underlying reports describe actual unit usage, not praise or speculation.
- Prefer repeated observations or two independent reports.
- A single isolated rep does not justify moving above `occasional`.
- When a reliable numeric share exists, keep `role.first_team_usage` as the primary quantitative signal and use the class only as a consistent qualitative summary.
- A class change is material only after the profile source-confidence gate is met.
