#!/usr/bin/env python3
"""Walk-forward backtest of the team projection range (MatchupProjections method).

For every historical team-week the production PlayerWeekFantasy model is rebuilt as
if the week were about to start (only earlier weeks and seasons enter the model).
The team value and range use the same functions as tools/matchup_projection.py, so
the backtest validates the production formula, not a copy of it. The realized
team score is the league-scored matchup total of the actual starters.

Weeks after the league's final fantasy week are excluded: Sleeper still lists a
matchup for NFL week 18, but it never counted as a fantasy week.

Usage (about five minutes for two seasons):
    python3 tools/historical_team_range_backtest.py --seasons 2024 2025
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping, Sequence

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from matchup_projection import player_sigma, team_ranges, z_for_level  # noqa: E402
from player_week_fantasy import PRIMARY_INTERVAL_LEVEL, PUBLISHED_INTERVAL_LEVELS  # noqa: E402

LEAGUE_ID = "nfl-reise"


def last_fantasy_week(repo_root: Path, league_id: str, season: int) -> int:
    path = repo_root / "source-data" / "leagues" / league_id / "seasons" / str(season) / "league.json"
    structure = json.loads(path.read_text(encoding="utf-8")).get("WeekStructure") or {}
    week = structure.get("FinalLeagueWeek") or structure.get("ExpectedLastLeagueWeek")
    if isinstance(week, bool) or not isinstance(week, int) or week < 1:
        raise ValueError(f"League season {season} has no final fantasy week: {path}")
    return week


def build_team_week_row(
    starters: Sequence[str],
    projections: Mapping[str, Mapping[str, Any]],
    *,
    actual: float,
) -> tuple[dict[str, Any] | None, str | None]:
    """One pregame team-week, or (None, reason) when a starter cannot be projected."""

    total = 0.0
    variance = 0.0
    byes = 0
    for player_id in starters:
        projection = projections.get(player_id)
        if projection is None:
            return None, "missing-record"
        if projection["Status"] == "no-game":
            byes += 1
            continue
        ranges = projection.get("PredictionRanges") or []
        basis = next((item for item in ranges if item["Level"] == PRIMARY_INTERVAL_LEVEL), None)
        if projection["Status"] != "available" or projection["Points"] is None or basis is None:
            return None, str(projection["Status"])
        total += projection["Points"]
        sigma = player_sigma(basis["Lower"], basis["Upper"])
        variance += sigma * sigma
    return {"Mean": total, "Variance": variance, "ByeStarters": byes, "Actual": actual}, None


def collect(
    repo_root: Path,
    league_id: str,
    seasons: Iterable[int],
) -> dict[str, Any]:
    from player_week_fantasy_materialize import build_player_week_fantasy_dataset

    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed_weeks: list[dict[str, Any]] = []
    for season in seasons:
        for week in range(1, last_fantasy_week(repo_root, league_id, season) + 1):
            try:
                dataset = build_player_week_fantasy_dataset(
                    repo_root, league_id=league_id, season=season, week=week
                )
            except ValueError as exc:
                failed_weeks.append({"Season": season, "Week": week, "Error": str(exc)[:160]})
                continue
            by_player = {record["CanonicalPlayerID"]: record["Projection"] for record in dataset["Records"]}
            partition = repo_root / "source-data" / "leagues" / league_id / "seasons" / str(season) / "matchups" / f"week-{week}.json"
            for entry in json.loads(partition.read_text(encoding="utf-8")):
                starters = [item["CanonicalPlayerID"] for item in entry["Starters"] if item.get("CanonicalPlayerID")]
                key = {"Season": season, "Week": week, "Roster": entry["CanonicalLeagueRosterID"]}
                if not starters:
                    skipped.append({**key, "Reason": "no-starters"})
                    continue
                row, reason = build_team_week_row(starters, by_player, actual=float(entry["Points"]))
                if row is None:
                    skipped.append({**key, "Reason": reason})
                else:
                    rows.append({**key, **row})
    return {"Rows": rows, "Skipped": skipped, "FailedWeeks": failed_weeks}


def coverage(
    rows: Sequence[Mapping[str, Any]],
    *,
    levels: Sequence[float] = PUBLISHED_INTERVAL_LEVELS,
    scale: float = 1.0,
) -> dict[str, Any]:
    """Share of realized team scores inside the team range; scale widens sigma."""

    if not rows:
        return {"Count": 0}
    hits = {level: 0 for level in levels}
    low_miss = {level: 0 for level in levels}
    high_miss = {level: 0 for level in levels}
    for row in rows:
        for item in team_ranges(row["Mean"], row["Variance"] * scale * scale, tuple(levels)):
            level = item["Level"]
            if row["Actual"] < item["Lower"]:
                low_miss[level] += 1
            elif row["Actual"] > item["Upper"]:
                high_miss[level] += 1
            else:
                hits[level] += 1
    errors = [row["Actual"] - row["Mean"] for row in rows]
    return {
        "Count": len(rows),
        "Coverage": {str(level): round(hits[level] / len(rows), 4) for level in levels},
        "LowMisses": {str(level): low_miss[level] for level in levels},
        "HighMisses": {str(level): high_miss[level] for level in levels},
        "Bias": round(mean(errors), 3),
        "ResidualStd": round(pstdev(errors), 3),
        "MeanPredictedStd": round(mean(math.sqrt(row["Variance"]) for row in rows), 3),
    }


def calibration_scale(rows: Sequence[Mapping[str, Any]], level: float = PRIMARY_INTERVAL_LEVEL) -> float:
    """Factor on sigma that gives the target level exact coverage on these rows."""

    z_scores = sorted(
        abs(row["Actual"] - row["Mean"]) / math.sqrt(row["Variance"])
        for row in rows
        if row["Variance"] > 0
    )
    if not z_scores:
        raise ValueError("No rows with a positive variance to calibrate on")
    index = min(len(z_scores) - 1, math.ceil(level * len(z_scores)) - 1)
    return z_scores[index] / z_for_level(level)


def build_report(
    collected: Mapping[str, Any],
    *,
    calibration_season: int,
) -> dict[str, Any]:
    rows = collected["Rows"]
    seasons = sorted({row["Season"] for row in rows})
    report: dict[str, Any] = {
        "Method": "normal-independent-v1",
        "Levels": list(PUBLISHED_INTERVAL_LEVELS),
        "Seasons": {str(season): coverage([row for row in rows if row["Season"] == season]) for season in seasons},
        "AllSeasons": coverage(rows),
        "Skipped": collected["Skipped"],
        "FailedWeeks": collected["FailedWeeks"],
    }
    calibration_rows = [row for row in rows if row["Season"] == calibration_season]
    holdout_rows = [row for row in rows if row["Season"] != calibration_season]
    if calibration_rows and holdout_rows:
        scale = calibration_scale(calibration_rows)
        report["Calibration"] = {
            "CalibrationSeason": calibration_season,
            "Scale": round(scale, 4),
            "HoldoutRaw": coverage(holdout_rows),
            "HoldoutScaled": coverage(holdout_rows, scale=scale),
        }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=TOOLS.parent)
    parser.add_argument("--league", default=LEAGUE_ID)
    parser.add_argument("--seasons", type=int, nargs="+", default=[2024, 2025])
    parser.add_argument("--calibration-season", type=int, default=None)
    args = parser.parse_args(argv)
    seasons = sorted(args.seasons)
    collected = collect(args.repo_root.resolve(), args.league, seasons)
    report = build_report(collected, calibration_season=args.calibration_season or seasons[0])
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
