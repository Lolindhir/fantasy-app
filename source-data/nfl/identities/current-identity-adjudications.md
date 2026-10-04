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
- `ResolutionKind` is one of:
  - `current-provider-reassignment` with `ConflictPolicy` `reject-active-conflict` (split identities);
  - `upstream-claim-override` with `ConflictPolicy` `override-named-upstream-claim` (a wrong upstream crosswalk claim). Entry fields beyond the common ones: `OverriddenUpstreamClaim` (`Source`, `Provider`, `ExternalID`), `IndependentAnchors` (strong provider `GSIS`/`ESPN`/`PFR`/`PFF`, different from the overridden provider, optional `SourceProvider`), `ReplacementTokenConsistency` (`Position`, `Team`, `Summary`) and `OverriddenTokenInconsistency` (`Summary`); `ProviderAssignments` holds exactly the one replacement token.
- For `current-provider-reassignment`, a target may not already carry a different active value for an assigned provider, and the decision may not override an active provider conflict.
- An `upstream-claim-override` names exactly one upstream claim (`Source`, `Provider`, `ExternalID`, target) that is declared wrong for one season, plus the replacement token. It requires at least one independent strong anchor (GSIS, ESPN, PFR or PFF) tying the replacement token's record to the target, platform-data consistency of the replacement token (position, current team) and documented inconsistency of the overridden token. If the named upstream claim changes or disappears, the decision is reported as obsolete instead of being applied.
- An assigned provider token may not be owned by an undeclared third CanonicalPlayerID.
- Decisions are active only for their exact observation season; they do not silently carry into a later season.
- Raw provider evidence is never rewritten.
- Future materialized provenance must retain `manual.current-identity-adjudication:<AdjudicationID>`.
- A future reversal or correction must be explicit and versioned; generated canonical files must never be hand-edited as the source of truth.

## Current implementation boundary

Checkpoint 6Z.7 establishes the contract, canonical empty source and fail-closed loader/state validator only. Issue #347 step B3 extends the loader and state validator to `upstream-claim-override` (including the `active`/`obsolete`/`superseded-by-upstream` status report) and adds the open-gap hold to the population audit; the source still contains no entries.

The source is **not yet consumed by the productive identity builder**, and it currently contains no adjudications. Therefore this checkpoint has no productive identity or population effect.

A later explicitly authorized checkpoint may add reviewed decisions and integrate them into the identity builder. That integration must prove:

1. target/source CanonicalPlayerIDs still exist in the persisted pre-build identity graph;
2. exact assigned provider tokens still match the reviewed evidence;
3. no assigned token is in an active conflict;
4. the target has no different active value for the same provider;
5. no undeclared current owner exists;
6. the resulting identity/provider-mapping materialization is replay-idempotent;
7. the 6Z.4 population audit is rerun against the persisted result.

## Gap classes and open-gap hold (Issue #347, 2026-10-04)

The canonical rule set is `currentIdentityGapResolution` in `.ai-context/manual/player-identity.yaml`. In short:

| Class | Resolution | Cases on 2026-10-04 |
|---|---|---|
| `placeholderGsisUpgrade` | automatic in the identity builder (shared ESB, placeholder or missing GSIS on one side, valid GSIS on the other) | Layne Pryor |
| `splitIdentity` | this file, `current-provider-reassignment` | Grant Finley, Gregory Desrosiers, Roydell Williams |
| `wrongUpstreamClaim` | this file, `upstream-claim-override` | Sam Hartman |

A classified gap that is not yet resolved stays in the player population with status `identity_hold` and does not block a consumer cutover. Only unclassified gaps block.

Sam Hartman: nflverse ff-player-ids assigns Sleeper `11376` to the durable record; Sleeper lists `11376` as an OL without team. Sleeper `11558` is the QB at WAS, and its Tank01 ID `4361994` equals the durable record's ESPN ID. This case is resolved by an `upstream-claim-override`, not by a reassignment.
