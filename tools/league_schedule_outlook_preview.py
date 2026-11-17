#!/usr/bin/env python3
"""Read-only historical Regular-Season Outlook preview (Issue #1519, checkpoint I2).

Not a publisher or a completed league-schedule-outlook product. It derives one
historical after-week snapshot from accepted canonical pairing facts and the
persisted, rebuildable season-statistics weekly progression. The future Source
matchup payload is projected to pairing identity before it reaches the pure
schedule-outlook-v1 model: points, starters and current/final roster data are
never historical forecast inputs. Playoff paths are a separate checkpoint.

Usage:
  python tools/league_schedule_outlook_preview.py --league nfl-reise --season 2025 --after-week 6
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import data_derived_dir, data_source_dir
from derived_data_lib.models.registry import get_model
from derived_data_lib.week_finality import resolve_week_finality
from league_standings_sources import build_teams

MODEL_ID = "schedule-outlook-v1"


class ScheduleOutlookSourceError(ValueError):
    """Canonical source or as-of statistic input is missing or contradictory."""


def _document(path: Path) -> Any:
    if not path.is_file():
        raise ScheduleOutlookSourceError(f"Missing required source: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ScheduleOutlookSourceError(f"Invalid JSON source: {path}") from exc


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip() == value


def normalize_week_pairings(rows: Any, *, week: int, canonical_rosters: set[str]) -> list[dict[str, str]]:
    """Convert canonical one-row-per-roster matchup facts to one identity-only row per game.

    The input is allowed to contain scores, lineup players and other later
    observations: none are returned or used for the historical outlook.
    """
    if not isinstance(rows, list):
        raise ScheduleOutlookSourceError(f"Week {week}: matchups must be an array")
    matches: dict[str, list[str]] = {}
    roster_seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ScheduleOutlookSourceError(f"Week {week}: matchup entry must be an object")
        match, rid = row.get("CanonicalLeagueMatchupID"), row.get("CanonicalLeagueRosterID")
        if not _nonempty(match) or not _nonempty(rid) or rid not in canonical_rosters:
            raise ScheduleOutlookSourceError(f"Week {week}: missing or unknown canonical matchup/roster identity")
        if rid in roster_seen:
            raise ScheduleOutlookSourceError(f"Week {week}: repeated participant {rid}")
        roster_seen.add(rid)
        matches.setdefault(match, []).append(rid)
    if roster_seen != canonical_rosters:
        raise ScheduleOutlookSourceError(f"Week {week}: roster coverage incomplete")
    normalized = []
    for match, rosters in sorted(matches.items()):
        if len(rosters) != 2 or rosters[0] == rosters[1]:
            raise ScheduleOutlookSourceError(f"Week {week}: game {match} must have exactly two distinct rosters")
        a, b = sorted(rosters)
        normalized.append({
            "CanonicalLeagueMatchupID": match,
            "Team1CanonicalLeagueRosterID": a,
            "Team2CanonicalLeagueRosterID": b,
        })
    return normalized


def ratings_for_week(stats: dict[str, Any], teams: list[dict[str, Any]], *, rating_week: int) -> dict[str, dict[str, Any]]:
    """Map season-statistics weekly history to canonical roster IDs with strict as-of evidence."""
    if rating_week == 0:
        return {}
    if not isinstance(stats, dict) or not isinstance(stats.get("AsOf"), dict):
        raise ScheduleOutlookSourceError("Missing season-statistics AsOf evidence")
    completed = stats["AsOf"].get("CompletedWeeks")
    if type(completed) is not int or rating_week > completed:
        raise ScheduleOutlookSourceError(f"Season statistics not final through Week {rating_week}")
    weeks = stats.get("Weeks")
    if not isinstance(weeks, list):
        raise ScheduleOutlookSourceError("Missing season-statistics weekly history")
    matching = [w for w in weeks if isinstance(w, dict) and w.get("Week") == rating_week]
    if len(matching) != 1 or not isinstance(matching[0].get("Teams"), list):
        raise ScheduleOutlookSourceError(f"Missing/duplicate team ratings for Week {rating_week}")
    by_id: dict[int, dict[str, Any]] = {}
    for rating in matching[0]["Teams"]:
        if not isinstance(rating, dict) or type(rating.get("TeamID")) is not int:
            raise ScheduleOutlookSourceError(f"Malformed team rating for Week {rating_week}")
        tid = rating["TeamID"]
        if tid in by_id:
            raise ScheduleOutlookSourceError(f"Duplicate team rating {tid} at Week {rating_week}")
        by_id[tid] = {
            "RelativeScoringStrength": rating.get("RelativeScoringStrength"),
            "ProjectedBestBallStrength": rating.get("ProjectedBestBallStrength"),
        }
    if set(by_id) != {t["TeamID"] for t in teams}:
        raise ScheduleOutlookSourceError(f"Team-rating coverage mismatch at Week {rating_week}")
    return {t["CanonicalLeagueRosterID"]: by_id[t["TeamID"]] for t in teams}


def preview(repo_root: Path, league_id: str, season: int, after_week: int) -> dict[str, Any]:
    """Derive a single as-of RS preview; no output file and no future result inputs."""
    if not _nonempty(league_id) or type(season) is not int or type(after_week) is not int or after_week < 0:
        raise ScheduleOutlookSourceError("Invalid league/season/as-of selector")
    season_dir = data_source_dir(repo_root) / "leagues" / league_id / "seasons" / str(season)
    league = _document(season_dir / "league.json")
    if not isinstance(league, dict) or league.get("CanonicalLeagueID") != league_id or league.get("Season") != season:
        raise ScheduleOutlookSourceError("Canonical league ID/season mismatch")
    season_id = league.get("CanonicalLeagueSeasonID")
    if not _nonempty(season_id):
        raise ScheduleOutlookSourceError("Missing CanonicalLeagueSeasonID")
    week_structure = league.get("WeekStructure") or {}
    start = week_structure.get("PlayoffStartWeek")
    if type(start) is not int or start <= 1:
        raise ScheduleOutlookSourceError("Invalid canonical PlayoffStartWeek")
    regular_end = start - 1

    members = _document(season_dir / "members.json")
    rosters = _document(season_dir / "rosters.json")
    if not isinstance(members, list) or not isinstance(rosters, list):
        raise ScheduleOutlookSourceError("Invalid members/rosters source")
    teams = build_teams(members, rosters)
    roster_ids = {team["CanonicalLeagueRosterID"] for team in teams}
    if len(roster_ids) != len(teams) or len(teams) < 2:
        raise ScheduleOutlookSourceError("Missing or duplicate canonical teams")

    finality = resolve_week_finality(repo_root, league_id, season)
    scored = finality.get("LeagueScoredWeek")
    if type(scored) is not int or after_week > scored:
        raise ScheduleOutlookSourceError(f"As-of Week {after_week} is not LeagueScored final ({scored})")
    rating_week = min(after_week, regular_end)
    stats = _document(data_derived_dir(repo_root) / "season-statistics" / league_id / f"{season}.json") if rating_week else {}
    if rating_week and (stats.get("Product") != "season-statistics" or stats.get("CanonicalLeagueID") != league_id or stats.get("Season") != season):
        raise ScheduleOutlookSourceError("Season-statistics product identity mismatch")
    ratings = ratings_for_week(stats, teams, rating_week=rating_week)
    by_week: dict[int, list[dict[str, str]]] = {}
    for week in range(max(1, after_week + 1), regular_end + 1):
        raw = _document(season_dir / "matchups" / f"week-{week}.json")
        by_week[week] = normalize_week_pairings(raw, week=week, canonical_rosters=roster_ids)

    model = get_model(MODEL_ID, kind="schedule-outlook")
    value = model.compute_regular_season(
        teams=teams, pairings_by_week=by_week, strengths_by_roster=ratings,
        after_week=after_week, regular_season_last_week=regular_end,
    )
    # Preview-only shape: deliberately NOT a complete or publishable V1 product.
    return {
        "PreviewOnly": True,
        "CanonicalLeagueID": league_id,
        "CanonicalLeagueSeasonID": season_id,
        "Season": season,
        "Models": {"ScheduleOutlook": MODEL_ID, "SeasonStats": stats.get("Models", {}).get("SeasonStats") if stats else None},
        "AsOf": {"AfterWeek": after_week, "RatingWeek": rating_week if rating_week else None},
        "RegularSeason": value,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", required=True)
    parser.add_argument("--season", required=True, type=int)
    parser.add_argument("--after-week", required=True, type=int)
    args = parser.parse_args()
    try:
        result = preview(args.repo_root, args.league, args.season, args.after_week)
    except (ScheduleOutlookSourceError, ValueError, OSError, KeyError) as exc:
        print(f"schedule outlook preview failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
