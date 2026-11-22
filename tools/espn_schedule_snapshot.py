#!/usr/bin/env python3
"""ESPN kickoff observations as Source Evidence for the canonical NFL schedule (Issue #1627, ADR-097).

Writes data-source/providers/espn/schedule/<season>.json: per ESPN game ID the kickoff instant ESPN reports. It is
an observation only; the canonical schedule (nflverse) stays the single schedule truth and applies the observation
through tools/nfl_source_data_lib/schedule_kickoff_overlay.py during its own materialization.

  espn_schedule_snapshot.py sync [--season S] [--lookahead-days N]

Rules: one scoreboard request per distinct GameDay of the upcoming, not yet scored games; the result is MERGED into
the previous snapshot (an ESPN outage or a missing day keeps earlier observations); entries of scored or unknown
games are pruned; the file is written only on a semantic difference (no timestamps inside, history is in git).
An ESPN outage never fails the run (exit 0, reported as a warning).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import DATA_SOURCE_ROOT  # noqa: E402
from nfl_schedule_parity import (  # noqa: E402
    SCOREBOARD_URL,
    Fetcher,
    fetch_scoreboard,
    parse_espn_instant,
    upcoming_games,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "espn.schedule"
SCHEMA_VERSION = 1
# Flex moves are announced about two weeks ahead, so the snapshot looks further ahead than the parity check.
DEFAULT_LOOKAHEAD_DAYS = 14


def snapshot_path(repo_root: Path, season: int) -> Path:
    return repo_root / DATA_SOURCE_ROOT / "providers" / "espn" / "schedule" / f"{season}.json"


def load_observations(path: Path) -> dict[str, str]:
    """Previous observations {EspnGameID: KickoffUtc}; an unreadable snapshot counts as empty (fail closed)."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return {str(o["EspnGameID"]): str(o["KickoffUtc"]) for o in payload["Observations"]}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def build_snapshot(
    games: list[dict[str, Any]],
    previous: dict[str, str],
    today: date,
    lookahead_days: int,
    fetcher: Fetcher,
    season: int,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """(snapshot payload, errors). Merge of the previous observations with a fresh scoreboard read."""
    observations = dict(previous)
    errors: list[dict[str, str]] = []
    by_day: dict[str, dict[str, dict[str, Any]]] = {}
    for game in upcoming_games(games, today, lookahead_days):
        espn_id = (game.get("ProviderGameIDs") or {}).get("ESPN")
        if espn_id:
            by_day.setdefault(str(game["GameDay"]), {})[str(espn_id)] = game
    for day in sorted(by_day):
        try:
            events = {str(e["id"]): e for e in fetcher(day.replace("-", ""))["events"]}
        except Exception as exc:  # noqa: BLE001 - provider outage must never fail the pipeline
            errors.append({"GameDay": day, "Error": f"{type(exc).__name__}: {exc}"})
            continue
        for espn_id in by_day[day]:
            event = events.get(espn_id)
            instant = parse_espn_instant(event.get("date")) if event else None
            if instant is not None:
                observations[espn_id] = instant
    # Prune: keep only games of this schedule that are not scored yet (a scored game is never overlaid).
    open_ids = {
        str((g.get("ProviderGameIDs") or {}).get("ESPN"))
        for g in games
        if (g.get("ProviderGameIDs") or {}).get("ESPN") and g.get("AwayScore") is None and g.get("HomeScore") is None
    }
    payload = {
        "SchemaVersion": SCHEMA_VERSION,
        "SourceDataset": DATASET_ID,
        "Season": season,
        "SourceUrl": SCOREBOARD_URL.split("?")[0] + "?dates=<yyyymmdd>",
        "Observations": [
            {"EspnGameID": key, "KickoffUtc": observations[key]} for key in sorted(observations) if key in open_ids
        ],
    }
    return payload, errors


def sync(repo_root: Path, season: int, today: date, lookahead_days: int, fetcher: Fetcher) -> dict[str, Any]:
    from nfl_source_data_lib.common import write_json_if_changed

    schedule = json.loads(
        (repo_root / DATA_SOURCE_ROOT / "nfl" / "schedules" / f"{season}.json").read_text(encoding="utf-8")
    )
    games = schedule.get("Games")
    if not isinstance(games, list) or not games:
        raise ValueError(f"Canonical NFL schedule {season} contains no games.")
    path = snapshot_path(repo_root, season)
    payload, errors = build_snapshot(games, load_observations(path), today, lookahead_days, fetcher, season)
    changed = write_json_if_changed(path, payload)
    return {"Season": season, "Observations": len(payload["Observations"]), "Changed": changed, "Errors": errors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("sync")
    cmd.add_argument("--season", type=int)
    cmd.add_argument("--lookahead-days", type=int, default=DEFAULT_LOOKAHEAD_DAYS)
    args = parser.parse_args(argv)
    if args.season is not None:
        season = args.season
    else:
        from nfl_source_data_lib.common import current_source_season

        season = int(current_source_season(args.repo_root))
    today = datetime.now(timezone.utc).date()
    result = sync(args.repo_root, season, today, args.lookahead_days, fetch_scoreboard)
    line = (
        f"ESPN schedule snapshot {season}: {result['Observations']} observations, "
        f"{'written' if result['Changed'] else 'unchanged'}, {len(result['Errors'])} ESPN errors"
    )
    print(line)
    for error in result["Errors"]:
        print(f"::warning title=ESPN schedule unavailable::{error['GameDay']}: {error['Error']}")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write(f"- {line}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
