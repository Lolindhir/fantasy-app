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

Run the source synchronizer from the repository root:

```bash
python tools/nfl_source_data.py sync
```

Useful modes:

```bash
# Validate and materialize from already persisted raw data without network access.
python tools/nfl_source_data.py sync --offline

# Refresh one provider dataset.
python tools/nfl_source_data.py sync --dataset nflverse.draft-picks

# Rebuild canonical identities, per-season draft files and the coverage audit.
python tools/nfl_source_data.py materialize

# Print the current relevant-player identity/draft coverage audit.
python tools/nfl_source_data.py audit
```

A failed download, missing required column or implausibly small source file must fail before replacing the last known good raw input. Unchanged content does not rewrite metadata only to advance a timestamp.

## Identity contract

The durable identity architecture is documented in `.ai-context/manual/player-identity.yaml`.

`NFLPlayerID` is the internal, provider-independent identity of one real NFL player. It is the stable person key for canonical NFL source data and historical facts. Sleeper, Tank01, GSIS, ESPN, PFR, PFF and other provider IDs are mappings to that person, not the permanent cross-provider key themselves.

Sleeper still has a special application role: it is the leading source for the current app and league state, and `public/data/Players.json -> ID` remains the Sleeper player ID. This preserves the current app contract without making Sleeper IDs globally timeless person identifiers.

Provider mappings are historical. The first implementation may express validity at season granularity, but the model must remain compatible with more precise observed/valid time ranges later. A provider ID can therefore be associated with different `NFLPlayerID` values in non-overlapping historical periods if the upstream provider reuses or corrects that ID.

Identity resolution must not merge two otherwise distinguishable people merely because one provider mapping collides. If the same provider ID claims multiple distinct people for an overlapping period, quarantine that mapping as ambiguous/conflicting. Do not choose a silent winner, do not collapse the people, and do not use display names as authoritative merge keys.

Historical canonical facts must persist the resolved `NFLPlayerID` together with the original provider ID/provenance needed to audit the resolution. Once an old trade, draft pick, roster snapshot or other historical fact is anchored to a person, it must not be reinterpreted only from today's provider mapping.

The current app contract is unchanged: `public/data/Players.json -> ID` remains the Sleeper player ID. Adding `NFLPlayerID` to generated app read models would be a separate contract change and is not part of the source-data bootstrap.

## Metadata and no-op contract

Technical fetch, generation and freshness metadata belongs in dedicated provider metadata, timestamp, manifest, audit or sidecar structures. Do not add fields such as `GeneratedAt`, `GeneratedAtUtc` or `UpdatedAt` to `Players.json`, `League.json`, `Drafts.json`, `Transactions.json` or their domain records merely to record that a pipeline ran.

Canonical source datasets must also preserve semantic no-op behavior. If the validated source content and derived canonical facts are unchanged, materialization must not rewrite the dataset solely because a runtime timestamp changed. Operational timestamps therefore must not participate in semantic payload equality for identity or historical canonical datasets.

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