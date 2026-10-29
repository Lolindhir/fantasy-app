# Historical identity adjudications

`historical-identity-adjudications.json` is the versioned source of truth for rare historical provider mappings that remain unresolved after the ordinary automated identity rules but can be confirmed through explicit human review.

## Contract

- An adjudication confirms exactly one `Provider + ExternalID + Season -> CanonicalPlayerID` observation.
- It may only point to an already existing `CanonicalPlayerID`; adjudication never creates a canonical person.
- Every record must carry a stable `AdjudicationID`, a human-readable subject label, rationale, decision authority/date, and non-empty evidence references.
- Only `Status=confirmed` belongs in the canonical source. Unresolved review candidates stay outside this file.
- The materializer retains `manual.identity-adjudication:<AdjudicationID>` in provider-mapping provenance.
- A confirmed observation may join same-owner mapping intervals only when the confirmed season makes them contiguous. It never bridges another unobserved gap.
- A manual confirmation cannot override an active provider-mapping conflict or a different season-valid owner. Those cases continue to fail closed.
- Raw provider evidence is never rewritten. Historical source disagreements remain visible in `HistoricalResolutionConflicts` even when the exact Sleeper identity is separately adjudicated.
- Display names are descriptive review context only; the automated identity graph must not start using names as merge keys because an adjudication exists.

## Review model

The normal path remains automated corroboration. Adjudication is a bounded fallback for the small residual set where the repository has enough reviewable evidence to make a deliberate decision but the machine-safe generic threshold cannot resolve the provider token.

A future correction must be explicit and versioned; do not silently edit generated `provider-mappings.json` or historical League outputs.
