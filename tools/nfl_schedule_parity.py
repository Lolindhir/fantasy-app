#!/usr/bin/env python3
"""Read-only kickoff freshness check of the canonical NFL schedule against ESPN (Issue: kickoff freshness).

The canonical schedule (data-source/nfl/schedules/<season>.json, nflverse) is the only schedule truth. nflverse can
lag behind NFL flex scheduling, so a green sync does not prove current kickoff times. This tool compares the
kickoff instant of every upcoming, not yet scored game with the ESPN scoreboard (an independent observation, joined
by the ESPN game ID already stored in ProviderGameIDs) and REPORTS differences. It never writes data and never
overrides the canonical schedule.

  nfl_schedule_parity.py check [--season S] [--lookahead-days N] [--fail-on-mismatch] [--json-out PATH]

Exit codes: 0 = no mismatch (or ESPN unavailable, reported as such), 3 = mismatch with --fail-on-mismatch.
Unknown or unavailable evidence is never reported as a match.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import DATA_SOURCE_ROOT  # noqa: E402
from derived_data_lib.nfl_games import kickoff_utc  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={day}"
DEFAULT_LOOKAHEAD_DAYS = 7
RETRY_STATUS = {429, 500, 502, 503, 504}

Fetcher = Callable[[str], Any]


def fetch_scoreboard(day: str, timeout: int = 30) -> Any:
    """ESPN scoreboard JSON of one Eastern calendar day (yyyymmdd); transient errors retried three times."""
    request = urllib.request.Request(
        SCOREBOARD_URL.format(day=day),
        headers={"Accept": "application/json", "User-Agent": "fantasy-app-schedule-parity/1.0"},
    )
    delays = (2, 5, 10)
    for attempt in range(len(delays) + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRY_STATUS or attempt == len(delays):
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == len(delays):
                raise
        time.sleep(delays[attempt])
    raise AssertionError("unreachable")


def parse_espn_instant(value: Any) -> str | None:
    """ESPN date ('2026-11-22T18:00Z') -> canonical instant text; None when absent or malformed."""
    if not isinstance(value, str):
        return None
    for fmt in ("%Y-%m-%dT%H:%MZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    return None


def upcoming_games(games: list[dict[str, Any]], today: date, lookahead_days: int) -> list[dict[str, Any]]:
    """Games that are not scored yet and whose GameDay lies in [today - 1, today + lookahead]."""
    first, last = today - timedelta(days=1), today + timedelta(days=lookahead_days)
    selected = []
    for game in games:
        if game.get("AwayScore") is not None or game.get("HomeScore") is not None:
            continue
        try:
            day = date.fromisoformat(str(game["GameDay"]))
        except (KeyError, ValueError):
            continue
        if first <= day <= last:
            selected.append(game)
    return selected


def compare(games: list[dict[str, Any]], fetcher: Fetcher) -> dict[str, Any]:
    """Compare canonical kickoffs with ESPN per game; one scoreboard request per distinct GameDay."""
    by_day: dict[str, list[dict[str, Any]]] = {}
    for game in games:
        by_day.setdefault(str(game["GameDay"]), []).append(game)
    mismatches, matches, unverifiable, errors = [], 0, [], []
    for day in sorted(by_day):
        try:
            payload = fetcher(day.replace("-", ""))
            events = {str(event["id"]): event for event in payload["events"]}
        except Exception as exc:  # noqa: BLE001 - provider outage must never fail the pipeline
            errors.append({"GameDay": day, "Error": f"{type(exc).__name__}: {exc}"})
            unverifiable.extend({"GameID": g["GameID"], "Reason": "espn-unavailable"} for g in by_day[day])
            continue
        for game in by_day[day]:
            espn_id = (game.get("ProviderGameIDs") or {}).get("ESPN")
            event = events.get(str(espn_id)) if espn_id else None
            if event is None:
                unverifiable.append({"GameID": game["GameID"], "Reason": "no-espn-event" if espn_id else "no-espn-id"})
                continue
            observed = parse_espn_instant(event.get("date"))
            canonical = kickoff_utc(game["GameID"], game["GameDay"], game.get("GameTime") or None)
            if observed is None or canonical is None:
                unverifiable.append({"GameID": game["GameID"], "Reason": "kickoff-unknown"})
            elif observed == canonical:
                matches += 1
            else:
                mismatches.append(
                    {
                        "GameID": game["GameID"],
                        "Week": game.get("Week"),
                        "CanonicalKickoffUtc": canonical,
                        "EspnKickoffUtc": observed,
                        "EspnGameID": str(espn_id),
                    }
                )
    return {
        "Checked": len(games),
        "Matches": matches,
        "Mismatches": mismatches,
        "Unverifiable": unverifiable,
        "Errors": errors,
    }


def render_summary(result: dict[str, Any]) -> str:
    lines = ["### NFL schedule kickoff parity (canonical vs ESPN)", ""]
    lines.append(
        f"Checked {result['Checked']} upcoming games: {result['Matches']} match, "
        f"{len(result['Mismatches'])} differ, {len(result['Unverifiable'])} unverifiable."
    )
    if result["Mismatches"]:
        lines += ["", "| Game | Canonical (UTC) | ESPN (UTC) |", "|---|---|---|"]
        lines += [f"| {m['GameID']} | {m['CanonicalKickoffUtc']} | {m['EspnKickoffUtc']} |" for m in result["Mismatches"]]
    for error in result["Errors"]:
        lines.append(f"- ESPN unavailable for {error['GameDay']}: {error['Error']}")
    return "\n".join(lines) + "\n"


def run(repo_root: Path, season: int, today: date, lookahead_days: int, fetcher: Fetcher) -> dict[str, Any]:
    path = repo_root / DATA_SOURCE_ROOT / "nfl" / "schedules" / f"{season}.json"
    games = json.loads(path.read_text(encoding="utf-8")).get("Games")
    if not isinstance(games, list) or not games:
        raise ValueError(f"Canonical NFL schedule {season} contains no games.")
    result = compare(upcoming_games(games, today, lookahead_days), fetcher)
    result.update({"Season": season, "AsOfDate": today.isoformat(), "LookaheadDays": lookahead_days})
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--season", type=int)
    check.add_argument("--lookahead-days", type=int, default=DEFAULT_LOOKAHEAD_DAYS)
    check.add_argument("--fail-on-mismatch", action="store_true")
    check.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    today = datetime.now(timezone.utc).date()
    if args.season is not None:
        season = args.season
    else:
        from nfl_source_data_lib.common import current_source_season

        season = int(current_source_season(args.repo_root))
    result = run(args.repo_root, season, today, args.lookahead_days, fetch_scoreboard)
    summary = render_summary(result)
    print(summary)
    if args.json_out:
        args.json_out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write(summary)
    for mismatch in result["Mismatches"]:
        print(
            f"::warning title=Kickoff differs from ESPN::{mismatch['GameID']} canonical "
            f"{mismatch['CanonicalKickoffUtc']} vs ESPN {mismatch['EspnKickoffUtc']}"
        )
    return 3 if (result["Mismatches"] and args.fail_on_mismatch) else 0


if __name__ == "__main__":
    raise SystemExit(main())
