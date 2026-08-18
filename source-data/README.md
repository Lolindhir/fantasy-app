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

`source-data/nfl/identities/players.json` uses `NFLPlayerID` as an internal, provider-independent identity. GSIS, Sleeper, Tank01, ESPN, PFR and other provider IDs are mappings, not the canonical key.

The first materialization derives a deterministic `NFLPlayerID` from the strongest available external identity. Later materializations reuse the persisted `NFLPlayerID` whenever any known external ID overlaps, so adding a newly discovered GSIS/ESPN/PFR/etc. mapping does not rename an existing internal player.

Identity joins are ID-based. Names are descriptive metadata and are not authoritative merge keys. Conflicting one-to-many/provider mappings fail closed instead of choosing a silent winner.

The current app contract is unchanged: `public/data/Players.json -> ID` remains the Sleeper player ID until a separate migration is explicitly designed.

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
