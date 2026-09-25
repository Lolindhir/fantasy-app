#!/usr/bin/env python3
"""Re-score canonical historical NFL player weeks with an explicit League scoring profile."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# Sleeper scoring keys are intentionally mapped to canonical nflverse raw-stat fields.
# Provider fantasy-point columns are never consumed here.
#
# This module scores *individual player records*. Team-defense-only settings are
# classified separately and are intentionally not applied to player rows.
STAT_MAP: dict[str, tuple[str, ...]] = {
    # Passing
    "pass_att": ("attempts",),
    "pass_cmp": ("completions",),
    "pass_yd": ("passing_yards",),
    "pass_td": ("passing_tds",),
    "pass_int": ("passing_interceptions",),
    "pass_2pt": ("passing_2pt_conversions",),
    "pass_fd": ("passing_first_downs",),
    # Rushing
    "rush_att": ("carries",),
    "rush_yd": ("rushing_yards",),
    "rush_td": ("rushing_tds",),
    "rush_2pt": ("rushing_2pt_conversions",),
    "rush_fd": ("rushing_first_downs",),
    # Receiving
    "rec": ("receptions",),
    "rec_yd": ("receiving_yards",),
    "rec_td": ("receiving_tds",),
    "rec_2pt": ("receiving_2pt_conversions",),
    "rec_fd": ("receiving_first_downs",),
    # Misc player fumbles. Sleeper documents Fumble/Fumble Lost as applying to
    # any player/unit. fum_rec is deliberately *not* an offensive own-recovery
    # counter; for an individual player it is the defensive/IDP recovery stat.
    "fum": ("fumbles_total",),
    "fum_lost": ("fumbles_lost_total",),
    "fum_rec": ("def_fumbles",),
    "fum_rec_td": ("fumble_recovery_tds",),
    "fum_ret_yd": ("fumble_recovery_yards_opp",),
    # Individual defense / IDP. These keys can coexist with team-defense scoring
    # in Sleeper; when scoring one player row we use only that player's facts.
    "ff": ("def_fumbles_forced",),
    "int": ("def_interceptions",),
    "int_ret_yd": ("def_interception_yards",),
    "sack": ("def_sacks",),
    "sack_yd": ("def_sack_yards",),
    "safe": ("def_safeties",),
    "tkl_solo": ("def_tackles_solo",),
    "tkl_ast": ("def_tackle_assists",),
    "tkl_loss": ("def_tackles_for_loss",),
    "qb_hit": ("def_qb_hits",),
    "blk_kick": ("def_punt_blocks", "def_pat_blocks", "def_fg_blocks"),
    "def_td": ("def_tds",),
    # Individual special teams / returns.
    "st_td": ("special_teams_tds",),
    "pr_yd": ("punt_return_yards",),
    "kr_yd": ("kickoff_return_yards",),
    # Kicking
    "xpm": ("pat_made",),
    # Sleeper counts blocked kicks as misses. Attempts minus made therefore intentionally
    # includes both explicit misses and blocked attempts.
    "xpmiss": ("pat_att", "__subtract__:pat_made"),
    "fgm": ("fg_made",),
    "fgmiss": ("fg_att", "__subtract__:fg_made"),
    "fgm_0_19": ("fg_made_0_19",),
    "fgm_20_29": ("fg_made_20_29",),
    "fgm_30_39": ("fg_made_30_39",),
    "fgm_40_49": ("fg_made_40_49",),
    "fgm_50_59": ("fg_made_50_59",),
    "fgm_50p": ("fg_made_50_59", "fg_made_60_"),
    "fgm_60p": ("fg_made_60_",),
    "fgm_yds": ("fg_made_distance",),
}

# These settings describe the fantasy team-defense unit, not an individual player
# record. They must not be mistaken for unsupported player settings and must never
# be applied to an offensive/kicker/IDP player row.
TEAM_DEFENSE_ONLY_KEYS = {
    "bonus_def_fum_td_50p",
    "bonus_def_int_td_50p",
    "blk_kick_ret_yd",
    "def_2pt",
    "def_3_and_out",
    "def_4_and_stop",
    "def_forced_punts",
    "def_kr_yd",
    "def_pass_def",
    "def_pr_yd",
    "def_st_ff",
    "def_st_fum_rec",
    "def_st_td",
    "def_st_tkl_solo",
    "fg_ret_yd",
    "pts_allow",
    "pts_allow_0",
    "pts_allow_1_6",
    "pts_allow_7_13",
    "pts_allow_14_20",
    "pts_allow_21_27",
    "pts_allow_28_34",
    "pts_allow_35p",
    "yds_allow",
    "yds_allow_0_100",
    "yds_allow_100_199",
    "yds_allow_200_299",
    "yds_allow_300_349",
    "yds_allow_350_399",
    "yds_allow_400_449",
    "yds_allow_450_499",
    "yds_allow_500_549",
    "yds_allow_550p",
}

# Position-specific Sleeper settings are the exception to event-first scoring.
# They only apply when the player's canonical primary position matches the key.
POSITIONAL_RECEPTION_BONUS_KEYS = {"bonus_rec_rb", "bonus_rec_wr", "bonus_rec_te"}
POSITIONAL_FIRST_DOWN_BONUS_KEYS = {
    "bonus_fd_qb",
    "bonus_fd_rb",
    "bonus_fd_wr",
    "bonus_fd_te",
}
POSITIONAL_KEYS = POSITIONAL_RECEPTION_BONUS_KEYS | POSITIONAL_FIRST_DOWN_BONUS_KEYS


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


def positional_key_applies(position: str, key: str) -> bool:
    return key.endswith(f"_{position.lower()}")


def applicable_scoring_keys(position: str | None, scoring: dict[str, Any]) -> set[str]:
    """Return individual-player scoring keys that apply to this record.

    Player scoring is event-first: kickers may produce passing/rushing/receiving
    stats, skill players may produce return/defensive stats, and fumble deductions
    apply regardless of unit. Position only gates explicitly positional bonuses.

    Any non-team-defense, non-positional key is considered player-applicable so an
    activated but unmapped setting fails closed instead of being silently ignored.
    """

    pos = (position or "").upper()
    applicable: set[str] = set()
    for key in scoring:
        if key in TEAM_DEFENSE_ONLY_KEYS:
            continue
        if key in POSITIONAL_KEYS:
            if positional_key_applies(pos, key):
                applicable.add(key)
            continue
        applicable.add(key)
    return applicable


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
            "Selected scoring profile contains player-applicable non-zero settings without an explicit canonical mapping: "
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
