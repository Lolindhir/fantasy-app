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
- For `current-provider-reassignment`, a target may not already carry a different active value for an assigned provider, and the decision may not override an active provider conflict. Exception (Issue #347 B4): a conflict whose parties are exactly the declared target and declared sources is the split being resolved and is allowed; a third party in the conflict keeps it fail-closed.
- An `upstream-claim-override` names exactly one upstream claim (`Source`, `Provider`, `ExternalID`, target) that is declared wrong for one season, plus the replacement token. It requires at least one independent strong anchor (GSIS, ESPN, PFR or PFF) tying the replacement token's record to the target, platform-data consistency of the replacement token (position, current team) and documented inconsistency of the overridden token. If the named upstream claim changes or disappears, the decision is reported as obsolete instead of being applied.
- An assigned provider token may not be owned by an undeclared third CanonicalPlayerID.
- Decisions are active only for their exact observation season; they do not silently carry into a later season.
- Raw provider evidence is never rewritten.
- Future materialized provenance must retain `manual.current-identity-adjudication:<AdjudicationID>`.
- A future reversal or correction must be explicit and versioned; generated canonical files must never be hand-edited as the source of truth.

## Current implementation boundary

Checkpoint 6Z.7 establishes the contract, canonical empty source and fail-closed loader/state validator only. Issue #347 step B3 extends the loader and state validator to `upstream-claim-override` (including the `active`/`obsolete`/`superseded-by-upstream` status report) and adds the open-gap hold to the population audit; the source received its first reviewed entries in step B4 (2026-10-04).

The source is **consumed by the productive identity builder since #347 B5** (`tools/nfl_source_data_lib/identity.py`, `current_identity_adjudication_state` and `_apply_current_adjudications`). Since #347 B4 it contains 12 confirmed entries (Robert, 2026-10-04): `current-provider-reassignment` for Grant Finley, Gregory Desrosiers and Roydell Williams (RB, born 2001-12-08) and for the eight cases where an empty persisted provisional record and the full nflverse record both claim the Sleeper token (Charlie Smyth, Ben Sauls, Dominic Zvada, Trey Smack, Drew Stevens, Matt Hibner, Jack Strand, Malik McClain), and `upstream-claim-override` for Sam Hartman. The evidence per case is in the entry's `Evidence`.

The builder integration proves the following on every materialization (steps 1-5 as a fail-closed check before the build, steps 6-7 as the replay and population-audit evidence):

1. target/source CanonicalPlayerIDs still exist in the persisted pre-build identity graph;
2. exact assigned provider tokens still match the reviewed evidence;
3. no assigned token is in an active conflict;
4. the target has no different active value for the same provider;
5. no undeclared current owner exists;
6. the resulting identity/provider-mapping materialization is replay-idempotent;
7. the 6Z.4 population audit is rerun against the persisted result.

How a decision is applied: the declared source records give up the assigned provider tokens, the target's persisted record carries them (an existing different value is never replaced) and, for `upstream-claim-override`, the named upstream claim is removed from the named upstream source and from the target. The ordinary component builder then attaches the current provider evidence to the target; no CanonicalPlayerID is created, renamed, merged or deleted. Movable tokens are the `ProviderAssignments` plus, for an override, the token under an anchor's `SourceProvider` (the link between the two records); nothing else transfers. Moved provider claims carry `manual.current-identity-adjudication:<AdjudicationID>`; the previous owner's current-season mapping and conflict for a moved token are retired with a `HistoricalMappingReconciliations` entry (reason `current_identity_adjudication_transfers_current_claim`, earlier seasons stay). An overridden upstream claim stays visible as an identity source conflict with reason `upstream_claim_overridden_by_current_adjudication`; its historical mapping interval is not rewritten. A decision reported `obsolete` is not applied; `superseded-by-upstream` (the target already carries the replacement token, which is the normal state after the first materialization) keeps suppressing the overridden claim while the upstream still makes it.

## Gap classes and open-gap hold (Issue #347, 2026-10-04)

The canonical rule set is `currentIdentityGapResolution` in `.ai-context/manual/player-identity.yaml`. In short:

| Class | Resolution | Cases on 2026-10-04 |
|---|---|---|
| `placeholderGsisUpgrade` | automatic in the identity builder (shared ESB, placeholder or missing GSIS on one side, valid GSIS on the other); implemented in Issue #347 B2 | Layne Pryor |
| `splitIdentity` | this file, `current-provider-reassignment` | Grant Finley, Gregory Desrosiers, Roydell Williams |
| `wrongUpstreamClaim` | this file, `upstream-claim-override` | Sam Hartman |

A classified gap that is not yet resolved stays in the player population with status `identity_hold` and does not block a consumer cutover. Only unclassified gaps block.

Sam Hartman: nflverse ff-player-ids assigns Sleeper `11376` to the durable record; Sleeper lists `11376` as an OL without team. Sleeper `11558` is the QB at WAS, and its Tank01 ID `4361994` equals the durable record's ESPN ID. This case is resolved by an `upstream-claim-override`, not by a reassignment.
