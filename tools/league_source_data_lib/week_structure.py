from __future__ import annotations

import json
from pathlib import Path


def resolve_nfl_regular_season_week_ceiling(repo_root: Path, season: int) -> int:
    path = repo_root / "source-data" / "nfl" / "schedules" / f"{season}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Canonical NFL schedule is required for league week acquisition: {path}"
        )
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Canonical NFL schedule must be an object: {path}")
    try:
        payload_season = int(payload.get("Season"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Canonical NFL schedule has invalid Season: {path}") from exc
    if payload_season != int(season):
        raise ValueError(
            f"Canonical NFL schedule season mismatch: requested {season}, got {payload_season}"
        )
    games = payload.get("Games")
    if not isinstance(games, list) or not games:
        raise ValueError(f"Canonical NFL schedule Games must be a non-empty array: {path}")

    regular_weeks: set[int] = set()
    for game in games:
        if not isinstance(game, dict):
            raise ValueError(f"Canonical NFL schedule contains a non-object game: {path}")
        if str(game.get("GameType") or "").upper() != "REG":
            continue
        week = game.get("Week")
        if isinstance(week, bool):
            raise ValueError(f"Canonical NFL schedule contains invalid REG Week: {week!r}")
        try:
            week_number = int(week)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Canonical NFL schedule contains invalid REG Week: {week!r}"
            ) from exc
        if week_number < 1:
            raise ValueError(
                f"Canonical NFL schedule contains non-positive REG Week: {week_number}"
            )
        regular_weeks.add(week_number)

    if not regular_weeks:
        raise ValueError(f"Canonical NFL schedule contains no REG weeks: {path}")
    ceiling = max(regular_weeks)
    expected = set(range(1, ceiling + 1))
    if regular_weeks != expected:
        missing = sorted(expected - regular_weeks)
        raise ValueError(
            f"Canonical NFL schedule REG weeks are not contiguous for {season}; missing {missing}"
        )
    return ceiling
