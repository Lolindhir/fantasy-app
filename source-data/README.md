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

## Dataset registry and lifecycle

`registry.json` is the machine-readable source contract. Schema v2 owns each active or planned dataset's lifecycle in addition to its provider, upstream, URL, schema guard, minimum plausible row count, license and attribution.

Supported lifecycle classes are deliberately constrained:

| Lifecycle | Refresh | Retention | Partition | Finalization / repair |
| --- | --- | --- | --- | --- |
| `dynamic` | `periodic` | `latest-with-git-history` | none | never finalized; normal replacement |
| `immutable-history` | `discover-new-partitions` | `permanent-by-season` | season | prior seasons are frozen; repair requires explicit `--force` |
| `seasonal-finalizable` | `current-season` | `permanent-by-season` | season or season-week | prior seasons are frozen; repair requires explicit `--force` |
| `snapshot` | `snapshot` | `permanent-snapshots` | snapshot-time | append-only snapshots; repair requires explicit `--force` |

Invalid combinations fail while loading the registry. The lifecycle fields are therefore executable policy, not descriptive free text.

For season-partitioned historical datasets the current `League.Season` remains refreshable. This prevents a partially available current Draft or Combine class from being frozen by an early source sync. Once the league season advances, an already materialized prior-season partition is retained unchanged by normal materialization. A deliberate historical correction must use the explicit force/repair path.

Active datasets:

- `nflverse.players` — dynamic identity source
- `nflverse.ff-player-ids` — dynamic identity-mapping source
- `nflverse.draft-picks` — immutable season history
- `nflverse.combine` — immutable season history

Planned datasets are also lifecycle-classified before activation: Rosters, Weekly Rosters, Schedules, Player Stats, Snap Counts, Depth Charts and Contracts.

The durable architecture is documented in `.ai-context/manual/nfl-source-data.yaml` and ADR-026.

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

# Refresh one provider dataset and materialize when all registered raw inputs exist.
python tools/nfl_source_data.py sync --dataset nflverse.combine

# Rebuild canonical identities, mappings, Draft, Combine and coverage audit.
python tools/nfl_source_data.py materialize

# Explicitly repair frozen historical canonical partitions.
python tools/nfl_source_data.py materialize --force

# Print the already materialized audit without rebuilding canonical data.
python tools/nfl_source_data.py audit
```

`audit` is intentionally read-only. A normal workflow materializes once and then reads the resulting audit; it must not perform a second materialization merely to print coverage.

A failed download, missing required column or implausibly small source file must fail before replacing the last known good raw input. Unchanged content does not rewrite metadata only to advance a timestamp. The workflow publishes successfully validated provider raw data before canonical normalization, so a later identity/materialization failure does not discard the raw evidence that caused it. Canonical publication remains fail-closed and keeps the last known good canonical state.

The existing production workflow intentionally performs normal, non-forced canonical materialization. `--force` is a deliberate repair operation and is not implicit in routine source refreshes.

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

The mapping file uses season-level observation intervals. A provider ID may map to different `NFLPlayerID` values in non-overlapping seasons. An overlapping claim for multiple people is recorded in `Conflicts` and resolves fail-closed.

Archived app player snapshots may contribute historical Sleeper/Tank01/ESPN observations only when at least two independently resolvable provider IDs agree on the same `NFLPlayerID`. A single historical Sleeper ID is deliberately insufficient, so later provider-ID reuse cannot silently rewrite old history. If resolved provider IDs disagree, no mapping from that archived row is guessed.

Historical canonical facts persist the resolved `NFLPlayerID` together with source provenance. Once an old trade, draft pick, roster snapshot or other historical fact is anchored to a person, it must not be reinterpreted only from today's provider mapping.

The current app contract is unchanged: `public/data/Players.json -> ID` remains the Sleeper player ID. Adding `NFLPlayerID` or Combine fields to generated app read models is a separate contract change.

## Draft contract

`source-data/nfl/draft/<season>.json` stores NFL selections as historical facts with:

- round
- position within round
- overall pick
- drafting NFL team
- canonical `NFLPlayerID` when resolved
- source GSIS/PFR IDs for provenance

The draft status audit distinguishes `drafted`, `undrafted`, `unknown` and `not_yet_drafted`. In particular, `draft_year = 0` is never treated as proof of UDFA.

Draft is an `immutable-history` dataset. Existing prior-season canonical files are preserved in normal materialization; the current league season can continue to refresh until it becomes historical.

## Combine contract

Provider raw Combine data is persisted at:

```text
source-data/providers/nflverse/combine/raw-latest.csv
```

Canonical Combine data is season-partitioned at:

```text
source-data/nfl/combine/<season>.json
```

The upstream data is the nflverse Combine release, which exposes NFL Combine data courtesy of Pro Football Reference. Canonical records retain the descriptive player name, position, school and source IDs plus normalized measurements:

- height in inches
- weight in pounds
- 40-yard dash seconds
- bench-press reps
- vertical jump inches
- broad jump inches
- three-cone seconds
- shuttle seconds

Combine identity resolves to `NFLPlayerID` only through an unambiguous PFR provider mapping. `player_name`, position and school are descriptive evidence and are never authoritative identity joins. `cfb_id` is retained as provenance rather than promoted into a matching shortcut.

The normalized `Draft` link comes from the canonical `source-data/nfl/draft/<season>.json` facts. Combine's own draft year/round/overall fields remain under `SourceDraftEvidence`. If those facts disagree, canonical Draft remains authoritative and the disagreement is emitted in the audit rather than silently overwritten.

Duplicate PFR identities or duplicate resolved `NFLPlayerID` values inside the same Combine season fail closed.

## Metadata and no-op contract

Technical fetch, generation and freshness metadata belongs in dedicated provider metadata, timestamp, manifest, audit or sidecar structures. Do not add fields such as `GeneratedAt`, `GeneratedAtUtc` or `UpdatedAt` to app domain records merely to record that a pipeline ran.

Canonical source datasets preserve semantic no-op behavior. If the validated source content and derived canonical facts are unchanged, materialization must not rewrite the dataset solely because a runtime timestamp changed.

The materializer computes and validates identities, provider mapping history, Draft, Combine and the audit before writing any canonical file. A normalization failure therefore must not leave a partially rebuilt canonical source-data state.

## Audit contract

The materialized audit lives at:

```text
source-data/audits/nfl-source-data-audit.json
```

It reports, among other things:

- registry schema plus active/planned dataset IDs;
- current app-player identity coverage and which provider resolved the player;
- draft-status coverage by position;
- Combine season/record coverage, resolved/unresolved identity counts and current-app coverage;
- Combine-to-canonical-Draft conflicts;
- duplicate canonical link-provider IDs;
- weak-provider collisions and verified aliases;
- quarantined source mapping conflicts;
- ambiguous historical/current provider mappings;
- archived provider disagreement rows and insufficiently corroborated history.

An ambiguous provider mapping or source disagreement is an auditable data-quality result, not a reason to merge canonical people or choose a silent winner.
