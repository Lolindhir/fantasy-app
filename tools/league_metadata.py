"""Loader for hand-maintained league metadata under data-meta/<CanonicalLeagueID>/metadata.json.

Contract: .ai-context/manual/league-metadata.yaml (ADR-054). The loader is fail-closed: a missing
file, a missing season, an unknown key or an unknown model ID raises LeagueMetadataError. It never
assumes exactly one league; load_all_league_metadata iterates every league directory.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from data_roots import data_meta_dir

# Optional override of the metadata root (tests, fixtures); the default comes from data_roots.
DATA_META_ROOT_ENV = "DATA_META_ROOT"
METADATA_FILE_NAME = "metadata.json"
SCHEMA_VERSION = 1
SUPPORTED_PROVIDERS = {"Sleeper"}
LEAGUE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEASON_PATTERN = re.compile(r"^[0-9]{4}$")

# Interim model catalogue; replaced by the model registry of Issue #919 once it exists.
KNOWN_MODEL_IDS: dict[str, frozenset[str]] = {
    "Salary": frozenset({"salary-v1"}),
    "SalaryCap": frozenset({"salary-cap-v1"}),
    "Grading": frozenset({"grading-v1"}),
    "Standings": frozenset({"standings-v1"}),
    "Awards": frozenset({"awards-v1"}),
}

TOP_LEVEL_KEYS = {
    "SchemaVersion", "CanonicalLeagueID", "Provider", "CurrentProviderLeagueID",
    "LeagueTimeZone", "Owners", "Drafts", "Seasons",
}
SEASON_KEYS = {"CapDeadline", "CapDeadlineBufferDays", "Models"}


class LeagueMetadataError(ValueError):
    """Raised when league metadata is missing, malformed or inconsistent."""


def data_meta_root(repo_root: Path | None = None) -> Path:
    override = os.environ.get(DATA_META_ROOT_ENV)
    if override:
        return Path(override)
    base = repo_root if repo_root is not None else Path(__file__).resolve().parents[1]
    return data_meta_dir(base)


def list_league_ids(root: Path | None = None) -> list[str]:
    root = root or data_meta_root()
    if not root.is_dir():
        raise LeagueMetadataError(f"data-meta root not found: {root}")
    return sorted(p.name for p in root.iterdir() if p.is_dir() and (p / METADATA_FILE_NAME).exists())


def load_league_metadata(league_id: str, root: Path | None = None) -> dict[str, Any]:
    root = root or data_meta_root()
    path = root / league_id / METADATA_FILE_NAME
    if not path.is_file():
        raise LeagueMetadataError(f"League metadata not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LeagueMetadataError(f"Invalid JSON in {path}: {exc}") from exc
    validate_league_metadata(raw, expected_league_id=league_id, source=str(path))
    return raw


def load_all_league_metadata(root: Path | None = None) -> dict[str, dict[str, Any]]:
    root = root or data_meta_root()
    ids = list_league_ids(root)
    if not ids:
        raise LeagueMetadataError(f"No league metadata found under {root}")
    return {league_id: load_league_metadata(league_id, root) for league_id in ids}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LeagueMetadataError(message)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_league_metadata(raw: Any, expected_league_id: str | None = None, source: str = "metadata") -> None:
    _require(isinstance(raw, dict), f"{source}: must be a JSON object")
    missing, extra = TOP_LEVEL_KEYS - set(raw), set(raw) - TOP_LEVEL_KEYS
    _require(not missing and not extra, f"{source}: missing={sorted(missing)}, unknown={sorted(extra)}")
    _require(raw["SchemaVersion"] == SCHEMA_VERSION, f"{source}: unsupported SchemaVersion {raw['SchemaVersion']!r}")

    league_id = raw["CanonicalLeagueID"]
    _require(isinstance(league_id, str) and LEAGUE_ID_PATTERN.fullmatch(league_id), f"{source}: invalid CanonicalLeagueID {league_id!r}")
    if expected_league_id is not None:
        _require(league_id == expected_league_id, f"{source}: CanonicalLeagueID {league_id!r} != directory {expected_league_id!r}")
    _require(raw["Provider"] in SUPPORTED_PROVIDERS, f"{source}: unsupported Provider {raw['Provider']!r}")
    provider_id = raw["CurrentProviderLeagueID"]
    _require(isinstance(provider_id, str) and provider_id.isdigit(), f"{source}: invalid CurrentProviderLeagueID {provider_id!r}")
    try:
        ZoneInfo(raw["LeagueTimeZone"])
    except (ZoneInfoNotFoundError, ValueError, TypeError, KeyError) as exc:
        raise LeagueMetadataError(f"{source}: invalid LeagueTimeZone {raw['LeagueTimeZone']!r}") from exc

    owners = raw["Owners"]
    _require(isinstance(owners, dict) and owners, f"{source}: Owners must be a non-empty object")
    _require(all(_is_int(v) for v in owners.values()), f"{source}: Owners values must be integers")
    _require(len(set(owners.values())) == len(owners), f"{source}: Owners values must be unique")

    _validate_drafts(raw["Drafts"], source)
    _validate_seasons(raw["Seasons"], source)


def _validate_drafts(drafts: Any, source: str) -> None:
    _require(isinstance(drafts, dict), f"{source}: Drafts must be an object")
    _require(_is_int(drafts.get("UpcomingDraftCount")) and drafts["UpcomingDraftCount"] >= 0, f"{source}: Drafts.UpcomingDraftCount must be a non-negative integer")
    _require(drafts.get("UpcomingDraftCountMode") == "PerDraftType", f"{source}: Drafts.UpcomingDraftCountMode must be PerDraftType")
    types = drafts.get("Types")
    _require(isinstance(types, list) and types, f"{source}: Drafts.Types must be a non-empty list")
    seen: set[tuple[str, int]] = set()
    for entry in types:
        _require(isinstance(entry, dict), f"{source}: Drafts.Types entries must be objects")
        draft_type, instance = entry.get("DraftType"), entry.get("DraftInstance")
        _require(isinstance(draft_type, str) and draft_type, f"{source}: draft entry without DraftType")
        _require(_is_int(instance) and instance >= 1, f"{source}: {draft_type} needs DraftInstance >= 1")
        _require((draft_type, instance) not in seen, f"{source}: duplicate draft slot {draft_type}/{instance}")
        seen.add((draft_type, instance))
        _require(_is_int(entry.get("Rounds")) and entry["Rounds"] >= 1, f"{source}: {draft_type} needs Rounds >= 1")
        ids = entry.get("SleeperDraftIDs", {})
        _require(isinstance(ids, dict) and all(SEASON_PATTERN.fullmatch(k) and isinstance(v, str) and v.isdigit() for k, v in ids.items()),
                 f"{source}: {draft_type} has invalid SleeperDraftIDs")


def _validate_seasons(seasons: Any, source: str) -> None:
    _require(isinstance(seasons, dict) and seasons, f"{source}: Seasons must be a non-empty object")
    for season, entry in seasons.items():
        where = f"{source}: Seasons.{season}"
        _require(SEASON_PATTERN.fullmatch(season) is not None, f"{where}: season key must be four digits")
        _require(isinstance(entry, dict), f"{where}: must be an object")
        extra = set(entry) - SEASON_KEYS
        _require(not extra and "Models" in entry, f"{where}: unknown={sorted(extra)}, Models required")
        has_deadline, has_buffer = "CapDeadline" in entry, "CapDeadlineBufferDays" in entry
        _require(has_deadline == has_buffer, f"{where}: CapDeadline and CapDeadlineBufferDays go together")
        if has_deadline:
            try:
                datetime.fromisoformat(str(entry["CapDeadline"]).replace("Z", "+00:00"))
            except ValueError as exc:
                raise LeagueMetadataError(f"{where}: invalid CapDeadline {entry['CapDeadline']!r}") from exc
            buffer = entry["CapDeadlineBufferDays"]
            _require(_is_int(buffer) and buffer >= 0, f"{where}: CapDeadlineBufferDays must be a non-negative integer")
        models = entry["Models"]
        _require(isinstance(models, dict) and set(models) == set(KNOWN_MODEL_IDS), f"{where}: Models must name exactly {sorted(KNOWN_MODEL_IDS)}")
        for kind, model_id in models.items():
            _require(model_id in KNOWN_MODEL_IDS[kind], f"{where}: unknown {kind} model {model_id!r}")


def season_entry(metadata: dict[str, Any], season: int | str) -> dict[str, Any]:
    entry = metadata["Seasons"].get(str(season))
    if entry is None:
        raise LeagueMetadataError(f"{metadata['CanonicalLeagueID']}: no metadata for season {season}")
    return entry


def model_for(metadata: dict[str, Any], season: int | str, kind: str) -> str:
    models = season_entry(metadata, season)["Models"]
    if kind not in models:
        raise LeagueMetadataError(f"Unknown model kind {kind!r}")
    return models[kind]


def cap_deadline(metadata: dict[str, Any], season: int | str) -> tuple[str, int]:
    """Return (CapDeadline, CapDeadlineBufferDays); fail closed when the season has none."""
    entry = season_entry(metadata, season)
    if "CapDeadline" not in entry:
        raise LeagueMetadataError(f"{metadata['CanonicalLeagueID']}: season {season} has no CapDeadline")
    return entry["CapDeadline"], entry["CapDeadlineBufferDays"]


def validate_against_manifest(metadata: dict[str, Any], manifest: dict[str, Any]) -> None:
    """Every season of the league manifest needs a model choice; ids and provider must agree."""
    league_id = metadata["CanonicalLeagueID"]
    _require(manifest.get("CanonicalLeagueID") == league_id, f"{league_id}: manifest belongs to another league")
    _require(manifest.get("CurrentProviderLeagueID") == metadata["CurrentProviderLeagueID"],
             f"{league_id}: CurrentProviderLeagueID differs from manifest")
    for item in manifest.get("Seasons", []):
        season_entry(metadata, item["Season"])
    current = str(manifest["CurrentCanonicalLeagueSeasonID"]).rsplit("-", 1)[-1]
    cap_deadline(metadata, current)
