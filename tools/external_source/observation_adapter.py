"""Read-only, version-pinned provider Source Evidence adapters for #988 step 4A.4.

This is *not* market-observations materialization or a source-normalization
writer. It validates recorded snapshots, preserves attributed provider values,
and never guesses a CanonicalPlayerID from a name or a team.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .snapshot_discovery import Snapshot
from .identity import MappingIndex, resolve_entry
from nfl_season_context import resolve_season_for_date
from datetime import datetime, timezone

# Only observed/published versions are accepted. An upstream parser contract
# change must be registered and reviewed before consuming the new version.
RANKED_VERSIONS: dict[str, frozenset[int]] = {
    "fantasypros": frozenset({5, 6, 7}),
    "fantasycalc": frozenset({2, 3, 4}),
    "fantasy-football-calculator": frozenset({1, 2}),
    "fftoday": frozenset({1}),
    "cbs-sports": frozenset({1, 2}),
}
JSON_VERSIONS: dict[str, frozenset[int]] = {"sleeper": frozenset({1})}
RANKED_REQUIRED_COLUMNS: dict[str, frozenset[str]] = {
    "fantasypros": frozenset({"name", "Rank", "position", "source_player_id"}),
    "fantasycalc": frozenset({"name", "Rank", "position", "asset_type", "source_asset_id", "value", "sleeper_id"}),
    "fantasy-football-calculator": frozenset({"name", "Rank", "position", "source_player_id", "adp"}),
    "fftoday": frozenset({"name", "Rank", "position", "source_player_id", "projected_fantasy_points"}),
    "cbs-sports": frozenset({"name", "Rank", "position", "source_player_id", "projected_fantasy_points"}),
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ObservationAdapterError(ValueError):
    """Unsupported or incomplete provider evidence; do not silently coerce it."""


@dataclass(frozen=True)
class RankedEvidence:
    dataset_id: str
    provider: str
    source_version: int
    snapshot_key: str
    observed_at: str | None
    ranking_sha256: str
    columns: tuple[str, ...]
    rows: tuple[Mapping[str, str], ...]
    source_metadata: Mapping[str, Any]


@dataclass(frozen=True)
class RosterActivityEvidence:
    dataset_id: str
    provider: str
    source_version: int
    observed_at: str
    source_fingerprint: str
    players: tuple[Mapping[str, Any], ...]
    source_document: Mapping[str, Any]


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ObservationAdapterError(f"Missing or malformed Source JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ObservationAdapterError(f"Source JSON must be an object: {path}")
    return value


def _version(value: Mapping[str, Any], supported: frozenset[int], path: Path) -> int:
    version = value.get("schema_version")
    if type(version) is not int or version not in supported:
        raise ObservationAdapterError(
            f"Unsupported Source schema_version {version!r} at {path}; supported {sorted(supported)}"
        )
    return version


def _digest(value: str, path: Path) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ObservationAdapterError(f"Missing/invalid ranking SHA-256: {path}")
    return value


def load_ranked_evidence(dataset: Mapping[str, Any], snapshot: Snapshot) -> RankedEvidence:
    """Validate one legacy/intraday snapshot from its recorded source version.

    No rank/value conversion: CSV strings and per-provider column semantics are
    returned unchanged. Snapshot identity is the caller's discovered Source key.
    """
    provider = str(dataset["provider"])
    if provider not in RANKED_VERSIONS or dataset.get("kind") == "roster-activity":
        raise ObservationAdapterError(f"Not a registered ranked Source adapter: {provider}")
    metadata = _read_object(snapshot.metadata_file)
    version = _version(metadata, RANKED_VERSIONS[provider], snapshot.metadata_file)
    expected_ranking_id = str(dataset["id"]).split(".", 2)[2]
    if metadata.get("ranking_id") != expected_ranking_id:
        raise ObservationAdapterError(
            f"Ranked Source dataset identity mismatch: {snapshot.metadata_file}"
        )
    info = metadata.get("snapshot")
    info = info if isinstance(info, dict) else metadata

    expected_columns = info.get("csv_columns")
    expected_hash = _digest(info.get("ranking_sha256"), snapshot.metadata_file)
    try:
        content = snapshot.ranking_file.read_bytes()
        decoded = content.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise ObservationAdapterError(f"Missing/invalid ranked Source CSV: {snapshot.ranking_file}") from exc
    actual_hash = hashlib.sha256(content).hexdigest()
    if actual_hash != expected_hash:
        raise ObservationAdapterError(f"Ranked Source SHA-256 mismatch: {snapshot.ranking_file}")

    from io import StringIO
    reader = csv.DictReader(StringIO(decoded))
    columns = reader.fieldnames
    if not columns or len(set(columns)) != len(columns):
        raise ObservationAdapterError(f"Missing or duplicated Source CSV columns: {snapshot.ranking_file}")
    if expected_columns is not None and tuple(expected_columns) != tuple(columns):
        raise ObservationAdapterError(f"Recorded Source CSV schema differs from evidence: {snapshot.ranking_file}")
    required = RANKED_REQUIRED_COLUMNS[provider]
    if not required.issubset(columns):
        raise ObservationAdapterError(f"Required Source columns missing for {provider}: {sorted(required - set(columns))}")
    rows = list(reader)
    if not rows or any(None in row for row in rows):
        raise ObservationAdapterError(f"Empty or malformed Source CSV rows: {snapshot.ranking_file}")
    if "row_count" in info and info["row_count"] != len(rows):
        raise ObservationAdapterError(f"Recorded Source row_count mismatch: {snapshot.ranking_file}")

    # Preserve source rank fields as strings; our normalized Rank must be
    # unique/contiguous so historical observation identity cannot be ambiguous.
    try:
        ranks = [int(row["Rank"]) for row in rows]
    except (TypeError, ValueError) as exc:
        raise ObservationAdapterError(f"Non-integral normalized Rank: {snapshot.ranking_file}") from exc
    if ranks != list(range(1, len(rows) + 1)):
        raise ObservationAdapterError(f"Non-contiguous normalized Rank: {snapshot.ranking_file}")

    return RankedEvidence(
        dataset_id=str(dataset["id"]),
        provider=provider,
        source_version=version,
        snapshot_key=snapshot.key,
        observed_at=snapshot.observed_at.isoformat() if snapshot.observed_at else None,
        ranking_sha256=actual_hash,
        columns=tuple(columns),
        rows=tuple(rows),
        source_metadata=metadata,
    )


def load_roster_activity_evidence(
    dataset: Mapping[str, Any], document_path: Path,
) -> RosterActivityEvidence:
    """Read the existing combined Sleeper add/drop *latest* observation.

    Historical Sleeper archive is not present yet. comparison represents FM
    derived rolling-window state and is never used as a canonical Source fact.
    """
    if dataset.get("provider") != "sleeper" or dataset.get("kind") != "roster-activity":
        raise ObservationAdapterError("Sleeper roster activity requires a roster-activity registry entry")
    value = _read_object(document_path)
    version = _version(value, JSON_VERSIONS["sleeper"], document_path)
    if value.get("provider") != "sleeper" or value.get("signal_kind") != "roster_activity":
        raise ObservationAdapterError(f"Unexpected Sleeper Source provider/signal: {document_path}")
    stamp = value.get("generated_at")
    if not isinstance(stamp, str) or not stamp:
        raise ObservationAdapterError(f"Sleeper observation timestamp missing: {document_path}")
    digest = value.get("semantic_fingerprint")
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise ObservationAdapterError(f"Sleeper observation fingerprint missing: {document_path}")
    players = value.get("players")
    if not isinstance(players, list):
        raise ObservationAdapterError(f"Sleeper Source players must be an array: {document_path}")
    seen: set[str] = set()
    for player in players:
        if not isinstance(player, dict):
            raise ObservationAdapterError("Sleeper Source player must be an object")
        player_id = player.get("sleeper_player_id")
        if not isinstance(player_id, str) or not player_id or player_id in seen:
            raise ObservationAdapterError("Missing or duplicate Sleeper player identity")
        seen.add(player_id)
        for action in ("add", "drop"):
            state = player.get(action)
            if not isinstance(state, dict) or state.get("status") not in ("listed", "not_listed"):
                raise ObservationAdapterError(f"Invalid Sleeper {action} status for {player_id}")
            if state["status"] == "not_listed" and (
                state.get("rank") is not None or state.get("count") is not None
            ):
                raise ObservationAdapterError(f"Unlisted Sleeper activity cannot mean zero for {player_id}")
            if state["status"] == "listed" and not (
                type(state.get("rank")) is int and state["rank"] >= 1
                and type(state.get("count")) is int and state["count"] >= 0
            ):
                raise ObservationAdapterError(f"Invalid listed Sleeper activity for {player_id}")

    return RosterActivityEvidence(
        dataset_id=str(dataset["id"]),
        provider="sleeper",
        source_version=version,
        observed_at=stamp,
        source_fingerprint=digest,
        players=tuple(players),
        # Comparison is a consumer-side window delta, not provider observation.
        source_document={key: part for key, part in value.items() if key != "comparison"},
    )


@dataclass(frozen=True)
class NeutralObservationRow:
    """Provider-attributed neutral row, prior to #988 4B derived materialization.

    The provider-specific values are preserved without invented consensus or
    conversions. No league-local context is carried into global observations.
    """

    dataset_id: str
    provider: str
    schema_version: int
    observation_season: int
    snapshot_key: str
    source_row_number: int
    provider_player_id: str
    asset_type: str
    canonical_player_id: str | None
    identity_status: str
    identity_method: str | None
    provider_team_count: int | None
    provider_values: Mapping[str, Any]


def _mapping_index(repo_root: Path, index: MappingIndex | None) -> MappingIndex:
    return index if index is not None else MappingIndex.load(repo_root)


def normalize_ranked_observations(
    repo_root: Path,
    dataset: Mapping[str, Any],
    snapshot: Snapshot,
    *,
    mapping_index: MappingIndex | None = None,
) -> tuple[NeutralObservationRow, ...]:
    """Convert one verified ranked snapshot to provider-attributed neutral rows.

    Reuses exactly the Source Identity mapping/status owner; no name/team join
    and no fallbacks. Old actual_league_team_count is historical consumer context
    and is excluded, while registry providerTeamCount remains the source format.
    """
    evidence = load_ranked_evidence(dataset, snapshot)
    season = resolve_season_for_date(repo_root, snapshot.day.isoformat())
    index = _mapping_index(repo_root, mapping_index)
    field = dataset["identity"]["column"]
    provider_key = dataset["identity"]["providerKey"]
    format_team_count = dataset["format"].get("providerTeamCount")
    results: list[NeutralObservationRow] = []
    for row_number, row in enumerate(evidence.rows, start=1):
        asset_type = (row.get("asset_type") or "player").strip()
        provider_id = (row.get(field) or "").strip()
        identity = resolve_entry(provider_key, provider_id, asset_type, season, index)
        source_values = {
            key: value for key, value in row.items()
            if key != "actual_league_team_count"
        }
        results.append(
            NeutralObservationRow(
                dataset_id=evidence.dataset_id,
                provider=evidence.provider,
                schema_version=evidence.source_version,
                observation_season=season,
                snapshot_key=evidence.snapshot_key,
                source_row_number=row_number,
                provider_player_id=provider_id,
                asset_type=asset_type,
                canonical_player_id=identity["CanonicalPlayerID"],
                identity_status=identity["Status"],
                identity_method=identity["Method"],
                provider_team_count=format_team_count,
                provider_values=source_values,
            )
        )
    return tuple(results)


def normalize_sleeper_activity_observations(
    repo_root: Path,
    dataset: Mapping[str, Any],
    latest_path: Path,
    *,
    mapping_index: MappingIndex | None = None,
) -> tuple[NeutralObservationRow, ...]:
    """Expose one action from the combined Source latest; no fictitious history."""
    evidence = load_roster_activity_evidence(dataset, latest_path)
    action = str(dataset["id"]).rsplit(".", 1)[-1]
    if action not in ("add", "drop"):
        raise ObservationAdapterError(f"Unknown Sleeper roster activity dataset action: {action}")
    try:
        instant = datetime.fromisoformat(evidence.observed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ObservationAdapterError("Invalid Sleeper observation timestamp") from exc
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ObservationAdapterError("Sleeper observation timestamp lacks UTC offset")
    season = resolve_season_for_date(repo_root, instant.astimezone(timezone.utc).date().isoformat())
    index = _mapping_index(repo_root, mapping_index)
    rows: list[NeutralObservationRow] = []
    for row_number, player in enumerate(evidence.players, start=1):
        provider_id = player["sleeper_player_id"]
        identity = resolve_entry(
            dataset["identity"]["providerKey"], provider_id, "player", season, index
        )
        rows.append(
            NeutralObservationRow(
                dataset_id=evidence.dataset_id,
                provider=evidence.provider,
                schema_version=evidence.source_version,
                observation_season=season,
                # Only latest is retained pre-4A.3. Do not pretend this is archived.
                snapshot_key="latest",
                source_row_number=row_number,
                provider_player_id=provider_id,
                asset_type="player",
                canonical_player_id=identity["CanonicalPlayerID"],
                identity_status=identity["Status"],
                identity_method=identity["Method"],
                provider_team_count=dataset["format"].get("providerTeamCount"),
                provider_values=dict(player[action]),
            )
        )
    return tuple(rows)
