# League Context

This folder stores Fantasy Management context that is specific to the user's dynasty league but is not generated app data.

Use this folder for:

- owner and team identity resolution
- user perspective and aliases
- league format interpretation
- manager tendencies
- trade negotiation history
- negotiation strategy notes

Productive current league state is now consumer-scoped during Phase 2. `public/data/League.json` and `public/data/Metadata.json` remain the active contract for unmigrated league, salary, draft, standings and ownership consumers. `owner-registry.json` carries the explicit stable `TeamID -> CanonicalLeagueMemberID` bridge; provider roster IDs are provenance only and must not be treated as stable TeamIDs. Since Checkpoint 6Q, `managed-roster-signals` uses that bridge plus Canonical League Source Data productively for TeamID 1 `Roster`, `Reserve`, `Taxi` and `Starter`. Checkpoint 6R extends Canonical League ownership to the complete league-wide Roster/Reserve/Taxi union used by `external-signal-relevance`; Checkpoint 6S extends the same union to `player-signals`. `League.json` remains non-membership enrichment and the existing trigger/freshness bridge in those migrated consumers; for `player-signals` it still supplies managed-team display metadata and `ScoringType` for projection reconciliation.

Files in this folder are strategic or identity context. Re-check the current source contract for the specific consumer before dynamic roster, pick, salary, trade or standings conclusions; the canonical ownership adapter does not by itself migrate every Fantasy Management ownership path.
