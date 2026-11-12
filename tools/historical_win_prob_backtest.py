#!/usr/bin/env python3
"""Backtest of the pregame win probability (win-prob-v1, Issue #1443).

For every final fantasy matchup of the chosen seasons the pregame chance of the Weekly Recaps is compared with the actual result
(league-scored matchup totals). The chance is the raw result of the production functions (team-range-v1 projections of the
PlayerWeekFantasy partitions, win-prob-v1); there is no calibration. Reported: accuracy of the favorite, Brier score of the favorite's
chance against the base rate of 0.25, the calibration per chance band, and the upset rate.

The persisted PlayerWeekFantasy partitions are used as they are; they are produced without knowledge of the week they project, but a
later model change shows up here only after the partitions are rebuilt. Matchups with an unknown chance (missing projection) and ties
are counted separately and not scored.

Usage:
    python3 tools/historical_win_prob_backtest.py --seasons 2024 2025
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from data_roots import DATA_SOURCE_ROOT  # noqa: E402
from derived_data_lib.fantasy_game_context import canonical_matchup_facts  # noqa: E402
from derived_data_lib.weekly_recaps import resolve_weekly_recaps  # noqa: E402

LEAGUE_ID = "nfl-reise"
BANDS = ((50, 60), (60, 70), (70, 80), (80, 101))


def scored_matchups(repo_root: Path, league_id: str, season: int) -> list[dict[str, Any]]:
    """One row per final matchup with a known chance and a winner: the favorite's chance and whether the favorite won."""
    recap = resolve_weekly_recaps(repo_root, league_id, season)
    season_dir = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season)
    rows: list[dict[str, Any]] = []
    for week in recap["Weeks"]:
        number = week["Week"]
        raw = json.loads((season_dir / "matchups" / f"week-{number}.json").read_text(encoding="utf-8-sig"))
        facts = {item["FantasyMatchupID"]: item for item in canonical_matchup_facts(str(season), number, raw if isinstance(raw, list) else [raw])}
        for entry in week["WinProbabilities"]:
            fact = facts.get(entry["FantasyMatchupID"])
            chances = [team["PregameWinProbability"] for team in entry["Teams"]]
            if fact is None or None in chances:
                rows.append({"Season": season, "Week": number, "Status": "unknown-chance"})
                continue
            scores = [float(team["FinalScore"]) for team in fact["Teams"]]
            if scores[0] == scores[1] or chances[0] == chances[1]:
                rows.append({"Season": season, "Week": number, "Status": "tie-or-even"})
                continue
            favorite = 0 if chances[0] > chances[1] else 1
            rows.append(
                {
                    "Season": season,
                    "Week": number,
                    "Status": "scored",
                    "FavoriteChance": chances[favorite] / 100.0,
                    "FavoriteWon": scores[favorite] > scores[1 - favorite],
                    "Upset": entry["Upset"],
                }
            )
    return rows


def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    scored = [row for row in rows if row["Status"] == "scored"]
    if not scored:
        return {"Matchups": len(rows), "Scored": 0}
    brier = sum((row["FavoriteChance"] - (1.0 if row["FavoriteWon"] else 0.0)) ** 2 for row in scored) / len(scored)
    bands = {}
    for low, high in BANDS:
        members = [row for row in scored if low <= row["FavoriteChance"] * 100 < high]
        if members:
            bands[f"{low}-{min(high, 100)}"] = {
                "Count": len(members),
                "MeanChance": round(sum(row["FavoriteChance"] for row in members) / len(members), 4),
                "FavoriteWinRate": round(sum(1 for row in members if row["FavoriteWon"]) / len(members), 4),
            }
    return {
        "Matchups": len(rows),
        "Scored": len(scored),
        "UnknownChance": sum(1 for row in rows if row["Status"] == "unknown-chance"),
        "TieOrEven": sum(1 for row in rows if row["Status"] == "tie-or-even"),
        "FavoriteWinRate": round(sum(1 for row in scored if row["FavoriteWon"]) / len(scored), 4),
        "Brier": round(brier, 4),
        "BrierBaseline": 0.25,
        "UpsetRate": round(sum(1 for row in scored if row["Upset"]) / len(scored), 4),
        "Bands": bands,
    }


def build_report(repo_root: Path, league_id: str, seasons: Iterable[int]) -> dict[str, Any]:
    by_season = {season: scored_matchups(repo_root, league_id, season) for season in seasons}
    return {
        "Model": "win-prob-v1",
        "Calibration": "none",
        "Seasons": {str(season): summarize(rows) for season, rows in by_season.items()},
        "AllSeasons": summarize([row for rows in by_season.values() for row in rows]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=TOOLS.parent)
    parser.add_argument("--league", default=LEAGUE_ID)
    parser.add_argument("--seasons", type=int, nargs="+", default=[2024, 2025])
    args = parser.parse_args(argv)
    print(json.dumps(build_report(args.repo_root.resolve(), args.league, sorted(args.seasons)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
