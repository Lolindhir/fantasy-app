# League Context

This folder stores Fantasy Management context that is specific to the user's dynasty league but is not generated app data.

Use this folder for:

- owner and team identity resolution
- user perspective and aliases
- league format interpretation
- manager tendencies
- trade negotiation history
- negotiation strategy notes

Productive current league state is now consumer-scoped during Phase 2. `public/data/League.json` and `public/data/Metadata.json` remain the active contract for unmigrated league, salary, draft, standings and ownership consumers. `owner-registry.json` carries the explicit stable `TeamID -> CanonicalLeagueMemberID` bridge; provider roster IDs are provenance only and must not be treated as stable TeamIDs. Since Checkpoint 6Q, `managed-roster-signals` uses that bridge plus Canonical League Source Data productively for TeamID 1 `Roster`, `Reserve`, `Taxi` and `Starter`, while `League.json` remains display enrichment for that consumer.

Files in this folder are strategic or identity context. Re-check the current source contract for the specific consumer before dynamic roster, pick, salary, trade or standings conclusions; the canonical ownership adapter does not by itself migrate every Fantasy Management ownership path.
