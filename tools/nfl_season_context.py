#!/usr/bin/env python3
"""Resolve a provider-independent NFL season context from canonical schedules.

The context is deterministic for a repository state and an explicit as-of date.
It intentionally distinguishes only the boundaries that are currently backed by
canonical schedule evidence: before, during, and after the NFL regular season.
A richer postseason/offseason split can extend this contract later without
changing consumers that only need regular-season activity semantics.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

CONTEXT_ID = "nfl-regular-season-context"
SCHEMA_VERSION = 1
VALID_PHASES = {
    "pre_regular_season",
    "regular_season",
    "post_regular_season",
}


class NflSeasonContextError(RuntimeError):
    """Raised when canonical schedule data cannot resolve a trustworthy context."""


def _as_date(value: date | datetime | str | None) -> date:
    if value is None:
        return datetime.now(timezone.utc).date()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if "T" in text:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).date()
    return date.fromisoformat(text)


def _load_schedule(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise NflSeasonContextError(f"Canonical NFL schedule is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise NflSeasonContextError(f"Canonical NFL schedule is invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise NflSeasonContextError(f"Canonical NFL schedule is not an object: {path}")
    games = payload.get("Games")
    if not isinstance(games, list) or not games:
        raise NflSeasonContextError(f"Canonical NFL schedule has no Games array: {path}")
    return payload


def _schedule_bounds(payload: dict[str, Any]) -> dict[str, Any]:
    regular_games: list[tuple[date, int]] = []
    for game in payload.get("Games", []):
        if not isinstance(game, dict) or str(game.get("GameType") or "").upper() != "REG":
            continue
        try:
            game_day = date.fromisoformat(str(game["GameDay"]))
            week = int(game["Week"])
        except (KeyError, TypeError, ValueError) as exc:
            raise NflSeasonContextError("Canonical REG schedule row is missing valid GameDay/Week") from exc
        if week < 1:
            raise NflSeasonContextError(f"Canonical REG schedule has invalid week: {week}")
        regular_games.append((game_day, week))
    if not regular_games:
        raise NflSeasonContextError("Canonical NFL schedule has no REG games")
    return {
        "first_date": min(day for day, _ in regular_games),
        "last_date": max(day for day, _ in regular_games),
        "weeks": regular_games,
    }


def _schedule_files(root: Path) -> list[Path]:
    schedule_dir = root / "source-data" / "nfl" / "schedules"
    if not schedule_dir.exists():
        raise NflSeasonContextError(f"Canonical NFL schedule directory is missing: {schedule_dir}")
    files = sorted(
        path for path in schedule_dir.glob("*.json")
        if path.stem.isdigit()
    )
    if not files:
        raise NflSeasonContextError(f"No canonical NFL schedules found in {schedule_dir}")
    return files


def _select_schedule(root: Path, as_of: date, season: int | None) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    if season is not None:
        path = root / "source-data" / "nfl" / "schedules" / f"{season}.json"
        payload = _load_schedule(path)
        return path, payload, _schedule_bounds(payload)

    candidates: list[tuple[Path, dict[str, Any], dict[str, Any]]] = []
    for path in _schedule_files(root):
        payload = _load_schedule(path)
        candidates.append((path, payload, _schedule_bounds(payload)))

    containing = [
        item for item in candidates
        if item[2]["first_date"] <= as_of <= item[2]["last_date"]
    ]
    if containing:
        return max(containing, key=lambda item: int(item[0].stem))

    upcoming = [item for item in candidates if item[2]["first_date"] > as_of]
    if upcoming:
        return min(upcoming, key=lambda item: item[2]["first_date"])

    return max(candidates, key=lambda item: item[2]["last_date"])


def resolve_nfl_season_context(
    root: Path,
    *,
    as_of: date | datetime | str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    as_of_date = _as_date(as_of)
    path, payload, bounds = _select_schedule(root, as_of_date, season)

    schedule_season = payload.get("Season")
    try:
        schedule_season = int(schedule_season)
    except (TypeError, ValueError) as exc:
        raise NflSeasonContextError(f"Canonical NFL schedule has invalid Season: {schedule_season!r}") from exc
    if season is not None and schedule_season != season:
        raise NflSeasonContextError(
            f"Canonical NFL schedule season mismatch: requested {season}, found {schedule_season}"
        )

    first_date = bounds["first_date"]
    last_date = bounds["last_date"]
    if as_of_date < first_date:
        phase = "pre_regular_season"
        current_week = None
    elif as_of_date > last_date:
        phase = "post_regular_season"
        current_week = max(week for _, week in bounds["weeks"])
    else:
        phase = "regular_season"
        started_weeks = [
            week for game_day, week in bounds["weeks"]
            if game_day <= as_of_date
        ]
        current_week = max(started_weeks) if started_weeks else None

    return {
        "schema_version": SCHEMA_VERSION,
        "context_id": CONTEXT_ID,
        "season": schedule_season,
        "as_of_date": as_of_date.isoformat(),
        "phase": phase,
        "regular_season": {
            "first_game_date": first_date.isoformat(),
            "last_game_date": last_date.isoformat(),
            "current_week": current_week,
        },
        "source": {
            "kind": "canonical_nfl_schedule",
            "path": path.relative_to(root).as_posix(),
            "game_type_basis": "REG",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--as-of", help="ISO date or datetime; defaults to current UTC date")
    parser.add_argument("--season", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = resolve_nfl_season_context(
        args.root,
        as_of=args.as_of,
        season=args.season,
    )
    print(json.dumps(context, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
