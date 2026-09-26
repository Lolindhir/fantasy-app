# Current identity adjudications

`current-identity-adjudications.json` is the versioned source contract for rare **current-season** provider-identity corrections that remain unresolved after the ordinary automatic identity rules but can be deliberately confirmed from reviewable evidence.

This source is intentionally separate from `historical-identity-adjudications.json`. Historical adjudication fills a bounded past provider observation in `provider-mappings.json`; current adjudication is intended for a future identity-builder step that would change the **active** provider bridge in `source-data/nfl/identities/players.json`.

## Contract

- An adjudication is scoped to exactly one NFL `Season`.
- It targets one already-existing durable `TargetCanonicalPlayerID`.
- It must name one or more already-existing `SourceCanonicalPlayerIDs` whose explicitly enumerated provider tokens would be superseded.
- `ProviderAssignments` lists the exact `Provider + ExternalID` tokens that the decision is allowed to reassign. Nothing else is transferred implicitly.
- The decision never creates, renames or bulk-merges a CanonicalPlayerID.
- Display name, normalized name, position, team, age or other descriptive fields may support human review but are never sufficient automated merge keys.
- Only `Status=confirmed` belongs in the canonical source. Proposals or unresolved candidates remain outside this file.
- Every decision requires a stable `AdjudicationID`, decision authority/date, rationale and non-empty evidence references.
- `ResolutionKind` is fixed to `current-provider-reassignment`.
- `ConflictPolicy` is fixed to `reject-active-conflict`.
- A target may not already carry a different active value for an assigned provider.
- An assigned provider token may not be owned by an undeclared third CanonicalPlayerID.
- An adjudication may not override an active provider conflict.
- Decisions are active only for their exact observation season; they do not silently carry into a later season.
- Raw provider evidence is never rewritten.
- Future materialized provenance must retain `manual.current-identity-adjudication:<AdjudicationID>`.
- A future reversal or correction must be explicit and versioned; generated canonical files must never be hand-edited as the source of truth.

## Current implementation boundary

Checkpoint 6Z.7 establishes the contract, canonical empty source and fail-closed loader/state validator only.

The source is **not yet consumed by the productive identity builder**, and it currently contains no adjudications. Therefore this checkpoint has no productive identity or population effect.

A later explicitly authorized checkpoint may add reviewed decisions and integrate them into the identity builder. That integration must prove:

1. target/source CanonicalPlayerIDs still exist in the persisted pre-build identity graph;
2. exact assigned provider tokens still match the reviewed evidence;
3. no assigned token is in an active conflict;
4. the target has no different active value for the same provider;
5. no undeclared current owner exists;
6. the resulting identity/provider-mapping materialization is replay-idempotent;
7. the 6Z.4 population audit is rerun against the persisted result.

## Residual Issue #347 implication

The four non-conflict residuals from Checkpoint 6Z.6 may be evaluated for this contract in a later decision checkpoint.

Sam Hartman's current Sleeper disagreement is intentionally excluded by the fail-closed rules: a current adjudication cannot assign Sleeper `11558` to a target that already carries a different active Sleeper value (`11376`) unless a separate provider-conflict resolution changes the underlying evidence first.
