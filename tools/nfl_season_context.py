#!/usr/bin/env python3
"""Resolve provider-independent NFL season context from canonical schedule data."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

POSTSEASON_TYPES = {"WC", "DIV", "CON", "SB"}
VALID_PHASES = {
    "pre_regular_season",
    "regular_season",
    "postseason",
    "post_regular_season",
}


class NflSeasonContextError(RuntimeError):
    """Raised when canonical schedule data cannot resolve a season context safely."""


def _as_date(value: date | datetime | str | None) -> date:
    if value is None:
        return datetime.now(timezone.utc).date()
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date() if value.tzinfo else value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _load_schedule(root: Path, season: int) -> dict[str, Any]:
    path = root / "source-data" / "nfl" / "schedules" / f"{season}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise NflSeasonContextError(f"Missing canonical NFL schedule: {path}") from exc
    except json.JSONDecodeError as exc:
        raise NflSeasonContextError(f"Invalid canonical NFL schedule: {path}") from exc
    games = payload.get("Games")
    if payload.get("Season") != season or not isinstance(games, list) or not games:
        raise NflSeasonContextError(f"Invalid canonical NFL schedule contract for {season}")
    return payload


def _schedule_bounds(payload: dict[str, Any]) -> dict[str, Any]:
    games = payload["Games"]
    regular = [game for game in games if game.get("GameType") == "REG"]
    if not regular:
        raise NflSeasonContextError(f"Season {payload.get('Season')} has no REG games")

    def game_day(game: dict[str, Any]) -> date:
        try:
            return date.fromisoformat(str(game["GameDay"]))
        except (KeyError, ValueError, TypeError) as exc:
            raise NflSeasonContextError(
                f"Invalid GameDay in season {payload.get('Season')}"
            ) from exc

    regular_days = [game_day(game) for game in regular]
    postseason = [game for game in games if game.get("GameType") in POSTSEASON_TYPES]
    postseason_days = [game_day(game) for game in postseason]

    return {
        "first_regular_season_date": min(regular_days),
        "last_regular_season_date": max(regular_days),
        "first_postseason_date": min(postseason_days) if postseason_days else None,
        "last_postseason_date": max(postseason_days) if postseason_days else None,
        "regular_games": regular,
    }


def _available_seasons(root: Path) -> list[int]:
    directory = root / "source-data" / "nfl" / "schedules"
    seasons = []
    for path in directory.glob("*.json"):
        try:
            seasons.append(int(path.stem))
        except ValueError:
            continue
    if not seasons:
        raise NflSeasonContextError(f"No canonical NFL schedules found under {directory}")
    return sorted(seasons)


def resolve_season_for_date(root: Path, as_of: date | datetime | str | None = None) -> int:
    day = _as_date(as_of)
    evaluated: list[tuple[int, dict[str, Any]]] = []
    for season in _available_seasons(root):
        payload = _load_schedule(root, season)
        evaluated.append((season, _schedule_bounds(payload)))

    upcoming_same_year = [
        (season, bounds)
        for season, bounds in evaluated
        if bounds["first_regular_season_date"].year == day.year
        and day < bounds["first_regular_season_date"]
    ]
    if upcoming_same_year:
        return min(
            upcoming_same_year,
            key=lambda item: item[1]["first_regular_season_date"],
        )[0]

    covering = []
    for season, bounds in evaluated:
        end = bounds["last_postseason_date"] or bounds["last_regular_season_date"]
        if bounds["first_regular_season_date"] <= day <= end:
            covering.append((season, bounds))
    if covering:
        return max(covering, key=lambda item: item[0])[0]

    prior = [
        (season, bounds)
        for season, bounds in evaluated
        if bounds["first_regular_season_date"] <= day
    ]
    if prior:
        return max(prior, key=lambda item: item[1]["first_regular_season_date"])[0]

    return min(evaluated, key=lambda item: item[1]["first_regular_season_date"])[0]


def resolve_nfl_season_context(
    root: Path,
    *,
    as_of: date | datetime | str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    day = _as_date(as_of)
    resolved_season = season if season is not None else resolve_season_for_date(root, day)
    payload = _load_schedule(root, resolved_season)
    bounds = _schedule_bounds(payload)

    first_reg = bounds["first_regular_season_date"]
    last_reg = bounds["last_regular_season_date"]
    first_post = bounds["first_postseason_date"]
    last_post = bounds["last_postseason_date"]

    if day < first_reg:
        phase = "pre_regular_season"
    elif day <= last_reg:
        phase = "regular_season"
    elif last_post is not None and day <= last_post:
        phase = "postseason"
    else:
        phase = "post_regular_season"

    current_week = None
    if phase == "regular_season":
        completed_or_started = [
            game
            for game in bounds["regular_games"]
            if date.fromisoformat(str(game["GameDay"])) <= day
        ]
        if completed_or_started:
            current_week = max(int(game["Week"]) for game in completed_or_started)

    return {
        "schema_version": 1,
        "season": resolved_season,
        "phase": phase,
        "as_of_date": day.isoformat(),
        "current_week": current_week,
        "regular_season": {
            "first_game_date": first_reg.isoformat(),
            "last_game_date": last_reg.isoformat(),
        },
        "postseason": {
            "first_game_date": first_post.isoformat() if first_post else None,
            "last_game_date": last_post.isoformat() if last_post else None,
        },
        "source": {
            "kind": "canonical_nfl_schedule",
            "path": f"source-data/nfl/schedules/{resolved_season}.json",
        },
    }
