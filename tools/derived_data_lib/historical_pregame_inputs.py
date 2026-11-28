"""Shared historical input adapters for AC6A (#1451).

Both Season Statistics and Weekly Recaps consume the same canonical weekly
matchups, roster identities and conditional PWF projection partition. Preserve
legacy parsing, unknown handling and exception names; no new model, data
product, clock or numerical policy. The legacy error names and private
adapter aliases remain available from weekly_recaps for existing callers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT
from .matchup_context import collection, value_of


class WeeklyRecapsError(ValueError):
    """Incomplete or contradicting evidence (fail closed)."""


class EvidenceGap(WeeklyRecapsError):
    """A week lacks the starter, identity or game evidence the recap needs (the week is left out of the season model)."""


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _read(path: Path, what: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise WeeklyRecapsError(f"{what} is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WeeklyRecapsError(f"{what} is unreadable: {path}: {exc}") from exc


def roster_identity_map(rows: list[Any]) -> dict[str, dict[str, dict[str, str]]]:
    """Canonical player ID and Sleeper player ID to the week-specific team and position (New-WrRosterIdentityMap)."""
    by_canonical: dict[str, dict[str, str]] = {}
    by_player: dict[str, dict[str, str]] = {}
    for row in rows:
        canonical_id = _text(value_of(row, "CanonicalPlayerID"))
        team_ref = value_of(row, "Team")
        team = _text(value_of(row, "TeamAbbr", "TeamAbv")).upper()
        if team == "" and isinstance(team_ref, str):
            team = team_ref.strip().upper()
        position = _text(value_of(row, "Position")).upper()
        player_id = _text(value_of(value_of(row, "SourceIDs"), "Sleeper"))
        identity = {"CanonicalPlayerID": canonical_id, "PlayerID": player_id, "TeamAbbr": team, "Position": position}
        if canonical_id:
            by_canonical[canonical_id] = identity
        if player_id:
            by_player[player_id] = identity
    return {"ByCanonical": by_canonical, "ByPlayer": by_player}


def _pwf_projections(repo_root: Path, league_id: str, season: int, week: int) -> dict[str, Any]:
    """Projection per CanonicalPlayerID of the PlayerWeekFantasy partition; empty when the partition is missing (unknown)."""
    path = repo_root / DATA_DERIVED_ROOT / "player-week-fantasy" / league_id / str(season) / f"{week:02d}.json"
    if not path.is_file():
        return {}
    document = _read(path, "PlayerWeekFantasy partition")
    return {
        _text(value_of(record, "CanonicalPlayerID")): value_of(record, "Projection")
        for record in collection(value_of(document, "Records"))
        if _text(value_of(record, "CanonicalPlayerID")) != ""
    }


def _load_matchup_rows(season_dir: Path, week: int) -> list[Any] | None:
    path = season_dir / "matchups" / f"week-{week}.json"
    if not path.is_file():
        return None
    payload = _read(path, f"Canonical matchups week {week}")
    return payload if isinstance(payload, list) else [payload]


def _weekly_roster_rows(repo_root: Path, season: int, week: int) -> list[Any]:
    path = repo_root / DATA_SOURCE_ROOT / "nfl" / "weekly-rosters" / str(season) / f"{week:02d}.json"
    try:
        document = _read(path, f"WeeklyRecaps canonical weekly-roster evidence for {season} Week {week}")
    except WeeklyRecapsError as exc:
        raise EvidenceGap(str(exc)) from exc
    return collection(value_of(document, "Records", "Rows", "Players", "Data"))
