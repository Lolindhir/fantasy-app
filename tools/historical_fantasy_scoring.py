#!/usr/bin/env python3
"""Re-score canonical historical NFL player weeks with an explicit League scoring profile."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# Sleeper scoring keys are intentionally mapped to canonical nflverse raw-stat fields.
# Provider fantasy-point columns are never consumed here.
STAT_MAP: dict[str, tuple[str, ...]] = {
    "pass_att": ("attempts",),
    "pass_cmp": ("completions",),
    "pass_yd": ("passing_yards",),
    "pass_td": ("passing_tds",),
    "pass_int": ("interceptions",),
    "pass_2pt": ("passing_2pt_conversions",),
    "rush_att": ("carries",),
    "rush_yd": ("rushing_yards",),
    "rush_td": ("rushing_tds",),
    "rush_2pt": ("rushing_2pt_conversions",),
    "rec": ("receptions",),
    "rec_yd": ("receiving_yards",),
    "rec_td": ("receiving_tds",),
    "rec_2pt": ("receiving_2pt_conversions",),
    "fum": ("rushing_fumbles", "receiving_fumbles", "sack_fumbles"),
    "fum_lost": ("rushing_fumbles_lost", "receiving_fumbles_lost", "sack_fumbles_lost"),
    "xpm": ("extra_points_made",),
    "xpmiss": ("extra_point_attempts", "__subtract__:extra_points_made"),
    "fgm": ("field_goals_made",),
    "fgmiss": ("field_goal_attempts", "__subtract__:field_goals_made"),
}

OFFENSE_PREFIXES = ("pass_", "rush_", "rec_", "fum")
KICKER_KEYS = {"xpm", "xpmiss", "fgm", "fgmiss", "fgm_0_19", "fgm_20_29", "fgm_30_39", "fgm_40_49", "fgm_50_59", "fgm_60p"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def number(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)


def stat_value(stats: dict[str, Any], fields: tuple[str, ...]) -> float:
    total = 0.0
    for field in fields:
        if field.startswith("__subtract__:"):
            total -= number(stats.get(field.split(":", 1)[1]))
        else:
            total += number(stats.get(field))
    return total


def applicable_scoring_keys(position: str | None, scoring: dict[str, Any]) -> set[str]:
    pos = (position or "").upper()
    if pos == "K":
        return {key for key in scoring if key in KICKER_KEYS}
    if pos in {"QB", "RB", "WR", "TE", "FB"}:
        return {key for key in scoring if key.startswith(OFFENSE_PREFIXES)}
    return set()


def score_record(record: dict[str, Any], scoring: dict[str, Any]) -> dict[str, Any]:
    stats = record.get("Stats") or {}
    if not isinstance(stats, dict):
        raise ValueError("Canonical player stat record has no Stats object")
    applicable = applicable_scoring_keys(record.get("Position"), scoring)
    contributions = []
    unsupported_nonzero = []
    total = 0.0
    for key in sorted(applicable):
        weight = number(scoring.get(key))
        if weight == 0:
            continue
        fields = STAT_MAP.get(key)
        if fields is None:
            unsupported_nonzero.append(key)
            continue
        raw = stat_value(stats, fields)
        points = raw * weight
        total += points
        contributions.append(
            {"ScoringKey": key, "RawValue": raw, "Weight": weight, "Points": points}
        )
    return {
        "FantasyPoints": total,
        "Contributions": contributions,
        "UnsupportedNonZeroSettings": unsupported_nonzero,
    }


def league_season_path(repo_root: Path, league_id: str, season: int) -> Path:
    return repo_root / "source-data/leagues" / league_id / "seasons" / str(season) / "league.json"


def find_player_record(repo_root: Path, season: int, week: int, player_id: str) -> dict[str, Any]:
    path = repo_root / "source-data/nfl/player-stats" / str(season) / f"{week:02d}.json"
    payload = read_json(path)
    matches = [row for row in payload.get("Records", []) if row.get("CanonicalPlayerID") == player_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one player-stat record for {player_id} in {season}/W{week}, found {len(matches)}")
    return matches[0]


def snap_context(repo_root: Path, season: int, week: int, player_id: str) -> dict[str, Any] | None:
    path = repo_root / "source-data/nfl/snap-counts" / str(season) / f"{week:02d}.json"
    if not path.exists():
        return None
    rows = [row for row in read_json(path).get("Records", []) if row.get("CanonicalPlayerID") == player_id]
    if not rows:
        return None
    return {
        "GameCount": len(rows),
        "OffenseSnaps": sum(number(row.get("OffenseSnaps")) for row in rows),
        "DefenseSnaps": sum(number(row.get("DefenseSnaps")) for row in rows),
        "SpecialTeamsSnaps": sum(number(row.get("SpecialTeamsSnaps")) for row in rows),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--player", required=True, help="CanonicalPlayerID")
    parser.add_argument("--season", type=int, required=True, help="Historical NFL season to score")
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--league", default="nfl-reise", help="CanonicalLeagueID of the scoring profile")
    parser.add_argument("--scoring-season", type=int, required=True, help="League season whose ScoringSettings are applied")
    parser.add_argument("--allow-unsupported", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    profile = read_json(league_season_path(root, args.league, args.scoring_season))
    scoring = profile.get("ScoringSettings")
    if not isinstance(scoring, dict):
        raise ValueError("Selected league-season has no ScoringSettings")
    record = find_player_record(root, args.season, args.week, args.player)
    result = score_record(record, scoring)
    if result["UnsupportedNonZeroSettings"] and not args.allow_unsupported:
        raise ValueError(
            "Selected scoring profile contains applicable non-zero settings without an explicit raw-stat mapping: "
            + ", ".join(result["UnsupportedNonZeroSettings"])
        )
    output = {
        "CanonicalPlayerID": args.player,
        "NFLSeason": args.season,
        "Week": args.week,
        "LeagueScoringProfile": {"CanonicalLeagueID": args.league, "Season": args.scoring_season},
        "Player": {key: record.get(key) for key in ("PlayerName", "Position", "Team", "OpponentTeam", "SeasonType")},
        "Scoring": result,
        "SnapContext": snap_context(root, args.season, args.week, args.player),
        "Semantics": {
            "FantasyPointsAreDerived": True,
            "ProviderFantasyPointsUsed": False,
            "MissingSnapContextIsZero": False,
        },
    }
    print(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
