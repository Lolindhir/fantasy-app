from __future__ import annotations

import json
from pathlib import Path

from .week_structure import resolve_nfl_regular_season_week_ceiling


def _parse_int(value: object, *, field: str, minimum: int = 0) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer, got boolean {value!r}")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be an integer, got {value!r}") from error
    if parsed < minimum:
        raise ValueError(f"{field} must be >= {minimum}, got {parsed}")
    return parsed


def load_persisted_current_league_payload(
    repo_root: Path,
    provider_league_id: str,
) -> dict:
    path = (
        repo_root
        / "source-data"
        / "providers"
        / "sleeper"
        / "leagues"
        / provider_league_id
        / "league.json"
    )
    if not path.exists():
        raise FileNotFoundError(f"Persisted current Sleeper league source is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Persisted Sleeper league source must be an object: {path}")
    return payload


def validate_current_transaction_identity(
    repo_root: Path,
    canonical_league_id: str,
    provider_league_id: str,
    season: int,
) -> None:
    manifest_path = repo_root / "source-data" / "leagues" / canonical_league_id / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Canonical League manifest is required for current transaction refresh: {manifest_path}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"Canonical League manifest must be an object: {manifest_path}")

    manifest_provider_id = str(manifest.get("CurrentProviderLeagueID") or "").strip()
    if manifest_provider_id != provider_league_id:
        raise ValueError(
            "Current transaction refresh refuses provider identity drift: "
            f"bootstrap/provider={provider_league_id!r}, manifest={manifest_provider_id!r}"
        )

    seasons = manifest.get("Seasons")
    if not isinstance(seasons, list):
        raise ValueError(f"Canonical League manifest Seasons must be an array: {manifest_path}")
    matches = [item for item in seasons if isinstance(item, dict) and item.get("Season") == season]
    if len(matches) != 1:
        raise ValueError(
            f"Canonical League manifest must contain exactly one current season {season}; found {len(matches)}"
        )
    season_entry = matches[0]
    mappings = season_entry.get("ProviderMappings")
    if not isinstance(mappings, list):
        raise ValueError(
            f"Canonical League season {season} ProviderMappings must be an array"
        )
    provider_matches = [
        item
        for item in mappings
        if isinstance(item, dict)
        and item.get("Provider") == "Sleeper"
        and str(item.get("ProviderLeagueID") or "").strip() == provider_league_id
    ]
    if len(provider_matches) != 1:
        raise ValueError(
            "Current Sleeper provider league is not uniquely attached to the canonical season: "
            f"{canonical_league_id} / {season} / {provider_league_id}"
        )

    current_season_id = str(manifest.get("CurrentCanonicalLeagueSeasonID") or "").strip()
    selected_season_id = str(season_entry.get("CanonicalLeagueSeasonID") or "").strip()
    if not current_season_id or current_season_id != selected_season_id:
        raise ValueError(
            "Current transaction refresh refuses canonical current-season drift: "
            f"manifest current={current_season_id!r}, season entry={selected_season_id!r}"
        )


def resolve_current_transaction_window(
    repo_root: Path,
    canonical_league_id: str,
    provider_league_id: str,
    league_payload: dict,
) -> dict:
    payload_provider_id = str(league_payload.get("league_id") or "").strip()
    if payload_provider_id != provider_league_id:
        raise ValueError(
            "Sleeper current league payload does not match the configured provider league: "
            f"expected {provider_league_id!r}, got {payload_provider_id!r}"
        )

    season = _parse_int(league_payload.get("season"), field="Sleeper league season", minimum=1)
    if season is None:
        raise ValueError("Sleeper current league payload has no season")
    validate_current_transaction_identity(
        repo_root,
        canonical_league_id,
        provider_league_id,
        season,
    )

    week_ceiling = resolve_nfl_regular_season_week_ceiling(repo_root, season)
    if week_ceiling < 1:
        raise ValueError(f"NFL regular-season week ceiling must be positive for season {season}")

    status = str(league_payload.get("status") or "").strip().lower()
    settings = league_payload.get("settings")
    if settings is None:
        settings = {}
    if not isinstance(settings, dict):
        raise ValueError("Sleeper league settings must be an object")

    if status == "complete":
        current_week = week_ceiling
        evidence = "league.status=complete"
    else:
        leg = _parse_int(settings.get("leg"), field="Sleeper settings.leg", minimum=0)
        last_scored_leg = _parse_int(
            settings.get("last_scored_leg"),
            field="Sleeper settings.last_scored_leg",
            minimum=0,
        )
        if leg is not None and leg > 0:
            current_week = leg
            evidence = "settings.leg"
        elif last_scored_leg is not None:
            current_week = last_scored_leg + 1
            evidence = "settings.last_scored_leg+1"
        else:
            current_week = 1
            evidence = "default-week-1"
        current_week = min(max(current_week, 1), week_ceiling)

    start_week = max(1, current_week - 1)
    weeks = list(range(start_week, current_week + 1))
    return {
        "CanonicalLeagueID": canonical_league_id,
        "ProviderLeagueID": provider_league_id,
        "Season": season,
        "WeekCeiling": week_ceiling,
        "CurrentWeek": current_week,
        "Weeks": weeks,
        "Evidence": evidence,
    }
