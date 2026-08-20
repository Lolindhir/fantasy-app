# NFL source data

`source-data/` is the persistent input layer for provider-backed NFL facts. It is intentionally separate from both generated app read models under `public/data/` and Fantasy Management source material under `fantasy-management/sources/`.

## Layers

```text
external provider
      |
      v
source-data/providers/<provider>/   provider-shaped raw input + provenance
      |
      v
source-data/nfl/                    provider-independent canonical NFL data
      |
      v
public/requests/**                  app generators / downstream consumers
      |
      v
public/data/**                      generated app read models
```

The provider layer preserves the successfully validated input used by normalization. The canonical layer must not expose provider-specific download paths or field names as its contract.

## Registry

`registry.json` owns the technical source definition for each dataset: URL, expected columns, minimum plausible row count, refresh/retention behavior, provider/upstream identity, license and attribution.

The first vertical slice registers:

- `nflverse.players`
- `nflverse.ff-player-ids` (DynastyProcess player IDs as exposed by nflverse/ffverse)
- `nflverse.draft-picks`

## Tooling

Run the complete source synchronizer from the repository root:

```bash
python tools/nfl_source_data.py sync
```

Useful modes:

```bash
# Fetch/validate provider data and persist only the raw layer.
# This is the publication boundary used before canonical materialization in CI.
python tools/nfl_source_data.py sync --raw-only

# Validate and materialize from already persisted raw data without network access.
python tools/nfl_source_data.py sync --offline

# Refresh one provider dataset and materialize when all registered raw inputs exist.
python tools/nfl_source_data.py sync --dataset nflverse.draft-picks

# Rebuild canonical identities, historical provider mappings, per-season draft files and the coverage audit.
python tools/nfl_source_data.py materialize

# Print the already materialized audit without rebuilding canonical data.
python tools/nfl_source_data.py audit
```

`audit` is intentionally read-only. A normal workflow materializes once and then reads the resulting audit; it must not perform a second materialization merely to print coverage.

A failed download, missing required column or implausibly small source file must fail before replacing the last known good raw input. Unchanged content does not rewrite metadata only to advance a timestamp. The workflow publishes successfully validated provider raw data before canonical normalization, so a later identity/materialization failure does not discard the raw evidence that caused it. Canonical publication remains fail-closed and keeps the last known good canonical state.

## Identity contract

The durable identity architecture is documented in `.ai-context/manual/player-identity.yaml`.

`NFLPlayerID` is the internal, provider-independent identity of one real NFL player. It is the stable person key for canonical NFL source data and historical facts. Sleeper, Tank01, GSIS, ESPN, PFR, PFF and other provider IDs are mappings to that person, not the permanent cross-provider key themselves.

Sleeper still has a special application role: it is the leading source for the current app and league state, and `public/data/Players.json -> ID` remains the Sleeper player ID. This preserves the current app contract without making Sleeper IDs globally timeless person identifiers.

The resolver establishes person components from corroborated NFL identity evidence and an already persisted `NFLPlayerID`. Sleeper and Tank01 are attachment/provider mappings: they can attach provider-only or app-only rows to one unambiguous person, but they must not transitively merge two otherwise distinguishable people. When one provider ID currently claims multiple people, that provider mapping is suppressed from canonical reverse lookup and recorded as ambiguous instead.

Known same-person provider aliases remain evidence-gated. Exact birth-date disagreement blocks a person merge. ESPN aliasing requires at least one other matching strong identity; PFR aliasing requires at least two. A contradictory FF-ID row with no corroborating NFL anchor remains fully quarantined, while a row that has at least one exact-birthdate corroborating anchor suppresses only the specific contradictory anchor mappings.

### Canonical persons and provider mapping history

Canonical persons are stored in:

```text
source-data/nfl/identities/players.json
```

Historical provider mappings are stored separately in:

```text
source-data/nfl/identities/provider-mappings.json
```

The mapping file uses season-level observation intervals in the first implementation. Its main records contain:

- `Provider`
- `ExternalID`
- `NFLPlayerID`
- `FirstObservedSeason`
- `LastObservedSeason`
- source/provenance labels

A provider ID may therefore map to different `NFLPlayerID` values in non-overlapping seasons. An overlapping claim for multiple people is recorded in `Conflicts` and resolves fail-closed.

The current provider snapshot establishes current observations. In addition, existing app archives `public/data/past_seasons/Players_<season>.json` are used as historical Sleeper/Tank01 evidence. An archived row is accepted only when its available provider IDs resolve to one canonical person. If Sleeper and Tank01 from the same archived row resolve to different people, neither historical mapping is guessed; the row is recorded under `HistoricalResolutionConflicts` and surfaced in the audit.

`provider_mapping_lookup(...)` supports season-aware lookup against the historical mapping payload. It returns a person only when exactly one non-conflicting mapping covers the requested season.

Historical canonical facts must persist the resolved `NFLPlayerID` together with the original provider ID/provenance needed to audit the resolution. Once an old trade, draft pick, roster snapshot or other historical fact is anchored to a person, it must not be reinterpreted only from today's provider mapping.

The current app contract is unchanged: `public/data/Players.json -> ID` remains the Sleeper player ID. Adding `NFLPlayerID` to generated app read models would be a separate contract change and is not part of the source-data bootstrap.

## Metadata and no-op contract

Technical fetch, generation and freshness metadata belongs in dedicated provider metadata, timestamp, manifest, audit or sidecar structures. Do not add fields such as `GeneratedAt`, `GeneratedAtUtc` or `UpdatedAt` to `Players.json`, `League.json`, `Drafts.json`, `Transactions.json` or their domain records merely to record that a pipeline ran.

Canonical source datasets must also preserve semantic no-op behavior. If the validated source content and derived canonical facts are unchanged, materialization must not rewrite the dataset solely because a runtime timestamp changed. Operational timestamps therefore do not participate in the semantic identity, provider-mapping, draft or audit payloads.

The materializer computes and validates identities, provider mapping history, draft facts and the audit before it writes any canonical file. A normalization failure therefore must not leave a partially rebuilt canonical source-data state.

## Audit contract

The materialized audit lives at:

```text
source-data/audits/nfl-source-data-audit.json
```

It reports, among other things:

- relevant-player identity coverage and which app provider resolved the player;
- draft-status coverage by position;
- duplicate canonical link-provider IDs;
- weak-provider collisions and verified aliases;
- quarantined source mapping conflicts;
- ambiguous historical/current provider mappings;
- coverage from archived app-player snapshots;
- archived Sleeper/Tank01 disagreement rows;
- relevant players that remain unmatched or have unknown draft status.

An ambiguous provider mapping is an auditable data-quality result, not a reason to merge canonical people or choose a silent winner.

## Draft contract

`source-data/nfl/draft/<season>.json` stores completed NFL selections as stable historical facts with:

- round
- position within round
- overall pick
- drafting NFL team
- canonical `NFLPlayerID` when resolved
- source GSIS/PFR IDs for provenance

The draft status audit distinguishes:

- `drafted`: a canonical NFL draft-pick row exists;
- `undrafted`: FF Player IDs names a concrete completed draft year, contains no pick fields, and the authoritative draft dataset contains no resolved pick;
- `unknown`: evidence is missing or contradictory; in particular `draft_year = 0` is never treated as proof of UDFA;
- `not_yet_drafted`: the identity source points to a draft year later than the newest materialized draft season.

`public/data/Players.json` is not enriched by this first slice. That integration is intentionally a later, separately validated step.
