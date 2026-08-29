# NFL source data

`source-data/` is the persistent input layer for provider-backed NFL facts. It is intentionally separate from generated app read models under `public/data/` and from Fantasy Management source material under `fantasy-management/sources/`.

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

The provider layer preserves the successfully validated input used by normalization. The canonical layer must not expose provider-specific download paths or field names as its contract. Registering a source does not automatically make it an app provider or change `public/data/**`.

## Dataset registry, source modes and lifecycle

`registry.json` is the machine-readable source contract. Registry schema v3 keeps the existing lifecycle policy and adds an executable source/acquisition contract.

Every active dataset declares:

- `sourceMode`: `fixed` or `season-partitioned`;
- `sourceFormat`: currently `csv` or `json`;
- `sourceUrl`, `rawPath` and `metadataPath`;
- required fields/columns and a minimum plausible record count;
- `availabilityPolicy`;
- `materialize`, which distinguishes raw-only registered sources from datasets already consumed by the current canonical materializer;
- refresh, retention, lifecycle, repair, license and attribution metadata.

### Source modes

`fixed` sources resolve one URL to one validated raw snapshot. Their URL/path fields must not contain a `{season}` template.

`season-partitioned` sources resolve one upstream file per season. `sourceUrl`, `rawPath` and `metadataPath` must all contain `{season}`. Normal sync defaults to the current source season; explicit backfill/repair can select one or more seasons with `--season`.

### Availability

`availabilityPolicy: required` is the fail-closed default.

`availabilityPolicy: current-season-may-be-unavailable` is intentionally narrow: only a 404 for the current, not-yet-persisted season of a season-partitioned dataset may become the stable state `not-yet-available`. It is not treated as an empty dataset or numeric zero. Historical 404s, schema mismatches, malformed input and implausibly small/empty datasets remain errors. If a last-known-good raw partition already exists, a later fetch failure does not replace it with `not-yet-available`.

A `not-yet-available` metadata record intentionally has no per-run timestamp, so repeated checks without a state change remain semantic no-ops.

### Lifecycle classes

| Lifecycle | Refresh | Retention | Partition | Finalization / repair |
| --- | --- | --- | --- | --- |
| `dynamic` | `periodic` | `latest-with-git-history` | none | never finalized; normal replacement |
| `immutable-history` | `discover-new-partitions` | `permanent-by-season` | season | prior seasons are frozen; repair requires explicit `--force` |
| `seasonal-finalizable` | `current-season` | `permanent-by-season` | season or season-week | prior seasons are frozen; repair requires explicit `--force` |
| `snapshot` | `snapshot` | `permanent-snapshots` | snapshot-time | append-only snapshots; repair requires explicit `--force` |

Invalid combinations fail while loading the registry. Lifecycle and source fields are executable policy, not descriptive free text.

For season-partitioned raw sources, an already persisted season older than the current source season is reused as `frozen-existing` during a normal sync and is not fetched again. `--force` is the explicit repair path. The current source season is resolved from `public/data/League.json -> Season`, then `public/data/Metadata.json -> LeagueYear`, with the UTC calendar year only as a final technical fallback.

Current active datasets:

- `nflverse.players` — dynamic identity source
- `nflverse.ff-player-ids` — dynamic identity-mapping source
- `nflverse.draft-picks` — immutable season history
- `nflverse.combine` — immutable season history

Additional schedules, finality, player stats, snap counts, rosters, weekly rosters and Sleeper player snapshots are being added under Issue #184 before any app-generator migration.

The durable architecture is documented in `.ai-context/manual/nfl-source-data.yaml` and ADR-029.

## Tooling

Run the complete source synchronizer from the repository root:

```bash
python tools/nfl_source_data.py sync
```

Useful modes:

```bash
# Fetch/validate provider data and persist only the raw layer.
python tools/nfl_source_data.py sync --raw-only

# Validate and materialize from already persisted raw data without network access.
python tools/nfl_source_data.py sync --offline

# Refresh one provider dataset.
python tools/nfl_source_data.py sync --dataset nflverse.combine

# For a season-partitioned dataset, target one or several seasons explicitly.
python tools/nfl_source_data.py sync --dataset <dataset-id> --season 2025 --season 2026 --raw-only

# Rebuild current canonical identities, mappings, Draft, Combine and coverage audit.
python tools/nfl_source_data.py materialize

# Explicitly repair frozen historical canonical partitions.
python tools/nfl_source_data.py materialize --force

# Print the already materialized audit without rebuilding canonical data.
python tools/nfl_source_data.py audit
```

`--season` is valid only for `sync` and requires at least one selected season-partitioned dataset. If no season is supplied, season-partitioned sources use the current source season automatically.

`audit` is intentionally read-only. A normal workflow materializes once and then reads the resulting audit; it must not perform another materialization merely to print coverage. The production workflow separately performs an explicit second materialize pass as an idempotence guard.

A failed download, missing required field or implausibly small source file must fail before replacing the last-known-good raw input. Unchanged available content does not rewrite metadata only to advance a timestamp. The workflow publishes successfully validated provider raw data before canonical normalization, so a later identity/materialization failure does not discard the raw evidence that caused it. Canonical publication remains fail-closed and keeps the last-known-good canonical state.

## Identity contract

The durable identity architecture is documented in `.ai-context/manual/player-identity.yaml` and ADR-025.

`CanonicalPlayerID` is the application-defined, provider-independent identity of one real NFL player. It is issued in the `fantasy-app` namespace. Sleeper, Tank01, GSIS, ESPN, PFR, PFF and other provider IDs are mappings/evidence, not the permanent cross-provider person key.

Sleeper still has a special application role: `public/data/Players.json -> ID` remains the Sleeper player ID until a separate app-contract migration. That current app field is not the canonical timeless person key.

The resolver establishes person components from corroborated NFL identity evidence and already persisted canonical identities. Attachment/provider mappings may attach provider-only or app-only rows to one unambiguous person but must not silently merge otherwise distinguishable people. Ambiguous provider claims are quarantined rather than resolved by name.

Canonical persons are stored in:

```text
source-data/nfl/identities/players.json
```

Historical provider mappings are stored in:

```text
source-data/nfl/identities/provider-mappings.json
```

Provider mappings use season-level observation intervals. A provider ID may map to different `CanonicalPlayerID` values in non-overlapping seasons; overlapping contradictory claims fail closed and are recorded as conflicts.

The legacy field name `NFLPlayerID` is accepted only for migration reads. Current canonical outputs write `CanonicalPlayerID`, while preserving existing ID values during schema migration.

## Draft contract

`source-data/nfl/draft/<season>.json` stores NFL selections as historical facts with round, position within round, overall pick, drafting NFL team, canonical `CanonicalPlayerID` when resolved, and source GSIS/PFR IDs for provenance.

The draft status audit distinguishes `drafted`, `undrafted`, `unknown` and `not_yet_drafted`. In particular, `draft_year = 0` is never treated as proof of UDFA.

Draft is an `immutable-history` dataset. Existing prior-season canonical files are preserved in normal materialization; deliberate historical repair uses `--force`.

## Combine contract

Provider raw Combine data is persisted at:

```text
source-data/providers/nflverse/combine/raw-latest.csv
```

Canonical Combine data is season-partitioned at:

```text
source-data/nfl/combine/<season>.json
```

Combine identity resolves to `CanonicalPlayerID` only through an unambiguous PFR provider mapping. `player_name`, position and school are descriptive evidence and never authoritative identity joins. `cfb_id` remains provenance rather than a matching shortcut.

The normalized `Draft` link comes from canonical `source-data/nfl/draft/<season>.json`; Combine's own draft evidence remains separately preserved. Conflicts are audited instead of silently selecting a winner. Duplicate PFR identities or duplicate resolved `CanonicalPlayerID` values inside the same Combine season fail closed according to the documented invariants.

## Metadata and no-op contract

Technical fetch, generation and freshness metadata belongs in dedicated provider metadata, manifests, audits or sidecars. Do not add runtime timestamps to domain records merely to record that a pipeline ran.

Canonical source datasets preserve semantic no-op behavior. If validated source content and derived canonical facts are unchanged, materialization must not rewrite the dataset solely because runtime time advanced.

The materializer computes and validates semantic payloads before publishing canonical files. A normalization failure must not leave a partially rebuilt canonical source-data state.

## Audit contract

The materialized audit lives at:

```text
source-data/audits/nfl-source-data-audit.json
```

It reports registry coverage, current app-player identity coverage, draft status coverage, Combine coverage/conflicts, duplicate or ambiguous provider mappings, historical resolution conflicts and other data-quality invariants. As new Phase-1 datasets become canonical, their availability/freshness/coverage and join conflicts must be added to the same audit contract.

An ambiguous provider mapping or source disagreement is an auditable data-quality result, not permission to merge canonical people or choose a silent winner.
