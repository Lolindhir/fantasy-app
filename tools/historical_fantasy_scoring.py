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

SPECIAL_TEAMS_EVENT_DATASET_ID = "nflverse.special-teams-fumble-events"
SPECIAL_TEAMS_EVENT_SCORING_KEYS = {"st_ff", "st_fum_rec"}

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

# Sleeper's generic individual-defense keys are IDP stats. nflverse may expose
# defensive counters on an offensive-position player after a turnover or other
# unusual play, but Sleeper does not apply these IDP settings to QB/RB/WR/TE/K.
# Unit-specific Special Teams player keys are intentionally separate and remain
# position-independent.
IDP_ONLY_KEYS = {
    "ff",
    "fum_rec",
    "int",
    "int_ret_yd",
    "sack",
    "sack_yd",
    "safe",
    "tkl_solo",
    "tkl_ast",
    "tkl_loss",
    "qb_hit",
    "def_td",
}
DEFENSIVE_POSITION_GROUPS = {"DB", "DL", "LB"}
DEFENSIVE_POSITIONS = {
    "CB", "DB", "DE", "DL", "DT", "EDGE", "FS", "ILB", "LB", "NT",
    "OLB", "S", "SAF", "SS",
}


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


def is_defensive_player(position: str | None, position_group: str | None = None) -> bool:
    pos = (position or "").upper()
    group = (position_group or "").upper()
    return group in DEFENSIVE_POSITION_GROUPS or pos in DEFENSIVE_POSITIONS


def applicable_scoring_keys(
    position: str | None,
    scoring: dict[str, Any],
    *,
    position_group: str | None = None,
) -> set[str]:
    """Return individual-player scoring keys that apply to this record.

    Player scoring is event-first for ordinary offense, kicking, returns and
    unit-specific Special Teams player events. Position gates only settings whose
    Sleeper semantics are position-specific: explicit positional bonuses and
    generic IDP/individual-defense keys.

    Any other non-team-defense key remains player-applicable so an activated but
    unmapped setting fails closed instead of being silently ignored.
    """

    pos = (position or "").upper()
    defensive_player = is_defensive_player(position, position_group)
    applicable: set[str] = set()
    for key in scoring:
        if key in TEAM_DEFENSE_ONLY_KEYS:
            continue
        if key in POSITIONAL_KEYS:
            if positional_key_applies(pos, key):
                applicable.add(key)
            continue
        if key in IDP_ONLY_KEYS and not defensive_player:
            continue
        applicable.add(key)
    return applicable


def score_record(
    record: dict[str, Any],
    scoring: dict[str, Any],
    *,
    special_teams_event_values: dict[str, float] | None = None,
) -> dict[str, Any]:
    stats = record.get("Stats") or {}
    if not isinstance(stats, dict):
        raise ValueError("Canonical player stat record has no Stats object")
    applicable = applicable_scoring_keys(
        record.get("Position"),
        scoring,
        position_group=record.get("PositionGroup"),
    )
    contributions = []
    unsupported_nonzero = []
    total = 0.0
    for key in sorted(applicable):
        weight = number(scoring.get(key))
        if weight == 0:
            continue
        if key in SPECIAL_TEAMS_EVENT_SCORING_KEYS:
            if special_teams_event_values is None:
                unsupported_nonzero.append(key)
                continue
            raw = number(special_teams_event_values.get(key))
        else:
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


def special_teams_event_path(repo_root: Path, season: int, week: int) -> Path:
    return (
        repo_root
        / "source-data/nfl/special-teams-fumble-events"
        / str(season)
        / f"{week:02d}.json"
    )


def _recovery_scores_st_fum_rec(record: dict[str, Any]) -> bool:
    recovery_team = record.get("RecoveryTeam")
    fumbled_teams = record.get("FumbledTeams")
    if not isinstance(recovery_team, str) or not recovery_team.strip():
        raise ValueError(
            "Canonical Special Teams fumble-recovery event has no RecoveryTeam"
        )
    if not isinstance(fumbled_teams, list):
        raise ValueError(
            "Canonical Special Teams fumble-recovery event has no FumbledTeams list"
        )
    normalized = {
        str(team).strip()
        for team in fumbled_teams
        if isinstance(team, str) and str(team).strip()
    }
    if len(normalized) != 1:
        raise ValueError(
            "Canonical Special Teams fumble-recovery relation is ambiguous; "
            f"expected exactly one fumble team, found {sorted(normalized)}"
        )
    return recovery_team.strip() not in normalized


def special_teams_event_index_from_payload(
    payload: dict[str, Any],
    *,
    season: int | None = None,
    week: int | None = None,
) -> dict[str, dict[str, float]]:
    if not isinstance(payload, dict):
        raise ValueError("Canonical Special Teams fumble-event partition is not an object")
    if season is not None and payload.get("Season") != season:
        raise ValueError(
            f"Canonical Special Teams fumble-event Season mismatch: expected {season}, "
            f"found {payload.get('Season')!r}"
        )
    if week is not None and payload.get("Week") != week:
        raise ValueError(
            f"Canonical Special Teams fumble-event Week mismatch: expected {week}, "
            f"found {payload.get('Week')!r}"
        )
    if payload.get("SourceDataset") != SPECIAL_TEAMS_EVENT_DATASET_ID:
        raise ValueError(
            "Canonical Special Teams fumble-event SourceDataset mismatch: "
            f"{payload.get('SourceDataset')!r}"
        )
    if payload.get("Finalized") is not True:
        raise ValueError(
            "Canonical Special Teams fumble-event partition is not finalized; "
            "zero-by-absence is unknown"
        )
    records = payload.get("Records")
    if not isinstance(records, list):
        raise ValueError("Canonical Special Teams fumble-event partition has no Records list")

    index: dict[str, dict[str, float]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Canonical Special Teams fumble-event Records contains a non-object")
        player_id = record.get("CanonicalPlayerID")
        if not isinstance(player_id, str) or not player_id.strip():
            raise ValueError("Canonical Special Teams fumble-event record has no CanonicalPlayerID")
        if record.get("SpecialTeams") is not True:
            raise ValueError("Canonical Special Teams fumble-event record is not marked SpecialTeams=true")
        values = index.setdefault(player_id, {"st_ff": 0.0, "st_fum_rec": 0.0})
        event_type = record.get("EventType")
        if event_type == "forced-fumble":
            values["st_ff"] += 1.0
        elif event_type == "fumble-recovery":
            if _recovery_scores_st_fum_rec(record):
                values["st_fum_rec"] += 1.0
        else:
            raise ValueError(
                f"Unsupported canonical Special Teams fumble EventType: {event_type!r}"
            )
    return index


def load_special_teams_event_index(
    repo_root: Path,
    season: int,
    week: int,
) -> dict[str, dict[str, float]]:
    path = special_teams_event_path(repo_root, season, week)
    if not path.exists():
        raise FileNotFoundError(
            f"Missing canonical Special Teams fumble-event evidence: {path}"
        )
    payload = read_json(path)
    return special_teams_event_index_from_payload(payload, season=season, week=week)


def active_special_teams_event_keys(
    position: str | None,
    scoring: dict[str, Any],
) -> set[str]:
    applicable = applicable_scoring_keys(position, scoring)
    return {
        key
        for key in SPECIAL_TEAMS_EVENT_SCORING_KEYS
        if key in applicable and number(scoring.get(key)) != 0
    }


def league_season_path(repo_root: Path, league_id: str, season: int) -> Path:
    return repo_root / "source-data/leagues" / league_id / "seasons" / str(season) / "league.json"


def player_stats_path(repo_root: Path, season: int, week: int) -> Path:
    return repo_root / "source-data/nfl/player-stats" / str(season) / f"{week:02d}.json"


def player_stats_index(repo_root: Path, season: int, week: int) -> dict[str, dict[str, Any]]:
    path = player_stats_path(repo_root, season, week)
    payload = read_json(path)
    records = payload.get("Records")
    if not isinstance(records, list):
        raise ValueError(f"Canonical player-stat partition has no Records list: {path}")
    index: dict[str, dict[str, Any]] = {}
    for row in records:
        if not isinstance(row, dict):
            raise ValueError(f"Canonical player-stat partition contains a non-object row: {path}")
        player_id = row.get("CanonicalPlayerID")
        if not isinstance(player_id, str) or not player_id.strip():
            raise ValueError(f"Canonical player-stat record has no CanonicalPlayerID: {path}")
        if player_id in index:
            raise ValueError(
                f"Duplicate canonical player-stat record for {player_id} in {season}/W{week}"
            )
        index[player_id] = row
    return index


def find_player_record(repo_root: Path, season: int, week: int, player_id: str) -> dict[str, Any]:
    index = player_stats_index(repo_root, season, week)
    if player_id not in index:
        raise ValueError(f"Expected one player-stat record for {player_id} in {season}/W{week}, found 0")
    return index[player_id]


def score_player_week(
    repo_root: Path,
    season: int,
    week: int,
    player_id: str,
    scoring: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    record = find_player_record(repo_root, season, week, player_id)
    event_values: dict[str, float] | None = None
    if active_special_teams_event_keys(record.get("Position"), scoring):
        event_index = load_special_teams_event_index(repo_root, season, week)
        event_values = event_index.get(player_id, {"st_ff": 0.0, "st_fum_rec": 0.0})
    return record, score_record(
        record,
        scoring,
        special_teams_event_values=event_values,
    )


def league_matchup_path(repo_root: Path, league_id: str, season: int, week: int) -> Path:
    return (
        repo_root
        / "source-data/leagues"
        / league_id
        / "seasons"
        / str(season)
        / "matchups"
        / f"week-{week}.json"
    )


def league_player_points(
    repo_root: Path,
    league_id: str,
    season: int,
    week: int,
) -> dict[str, float]:
    path = league_matchup_path(repo_root, league_id, season, week)
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Canonical League matchup partition is not a list: {path}")
    points: dict[str, float] = {}
    for matchup in payload:
        if not isinstance(matchup, dict):
            raise ValueError(f"Canonical League matchup partition contains a non-object: {path}")
        entries = matchup.get("PlayerPoints")
        if not isinstance(entries, list):
            raise ValueError(f"Canonical League matchup has no PlayerPoints list: {path}")
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("Player"), dict):
                raise ValueError(f"Canonical League PlayerPoints entry is malformed: {path}")
            player_id = entry["Player"].get("CanonicalPlayerID")
            if not isinstance(player_id, str) or not player_id.strip():
                raise ValueError(f"Canonical League PlayerPoints entry has no CanonicalPlayerID: {path}")
            if player_id in points:
                raise ValueError(
                    f"Duplicate CanonicalPlayerID {player_id} in League PlayerPoints for {season}/W{week}"
                )
            points[player_id] = number(entry.get("Points"))
    return points


def historical_parity_summary(
    repo_root: Path,
    *,
    nfl_season: int,
    weeks: range,
    league_id: str,
    scoring_season: int,
    tolerance: float = 0.01,
) -> dict[str, Any]:
    profile = read_json(league_season_path(repo_root, league_id, scoring_season))
    scoring = profile.get("ScoringSettings")
    if not isinstance(scoring, dict):
        raise ValueError("Selected league-season has no ScoringSettings")

    total_league_player_weeks = 0
    compared_player_weeks = 0
    exact_matches = 0
    missing_zero_points: list[dict[str, Any]] = []
    missing_nonzero_points: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    provider_divergences: list[dict[str, Any]] = []
    scoring_mismatches: list[dict[str, Any]] = []

    for week in weeks:
        stats_by_player = player_stats_index(repo_root, nfl_season, week)
        league_points = league_player_points(repo_root, league_id, nfl_season, week)
        total_league_player_weeks += len(league_points)

        event_index: dict[str, dict[str, float]] | None = None
        if any(number(scoring.get(key)) != 0 for key in SPECIAL_TEAMS_EVENT_SCORING_KEYS):
            event_index = load_special_teams_event_index(repo_root, nfl_season, week)

        for player_id, league_value in league_points.items():
            record = stats_by_player.get(player_id)
            if record is None:
                detail = {
                    "Week": week,
                    "CanonicalPlayerID": player_id,
                    "LeaguePoints": league_value,
                }
                if abs(league_value) <= tolerance:
                    missing_zero_points.append(detail)
                else:
                    missing_nonzero_points.append(detail)
                continue

            compared_player_weeks += 1
            event_values = None
            if active_special_teams_event_keys(record.get("Position"), scoring):
                if event_index is None:
                    raise ValueError(
                        f"Special Teams event evidence was not loaded for {nfl_season}/W{week}"
                    )
                event_values = event_index.get(
                    player_id,
                    {"st_ff": 0.0, "st_fum_rec": 0.0},
                )
            result = score_record(
                record,
                scoring,
                special_teams_event_values=event_values,
            )
            if result["UnsupportedNonZeroSettings"]:
                unsupported.append(
                    {
                        "Week": week,
                        "CanonicalPlayerID": player_id,
                        "PlayerName": record.get("PlayerName"),
                        "Settings": result["UnsupportedNonZeroSettings"],
                    }
                )
                continue

            derived = number(result["FantasyPoints"])
            delta = derived - league_value
            if abs(delta) <= tolerance + 1e-9:
                exact_matches += 1
                continue

            stats = record.get("Stats") or {}
            provider_ppr_raw = stats.get("fantasy_points_ppr") if isinstance(stats, dict) else None
            provider_ppr = number(provider_ppr_raw) if provider_ppr_raw not in (None, "") else None
            detail = {
                "Week": week,
                "CanonicalPlayerID": player_id,
                "PlayerName": record.get("PlayerName"),
                "Position": record.get("Position"),
                "DerivedPoints": derived,
                "LeaguePoints": league_value,
                "Delta": delta,
                "ProviderFantasyPointsPPR": provider_ppr,
                "Contributions": result["Contributions"],
            }
            if provider_ppr is not None and abs(derived - provider_ppr) <= tolerance + 1e-9:
                provider_divergences.append(detail)
            else:
                scoring_mismatches.append(detail)

    return {
        "NFLSeason": nfl_season,
        "LeagueScoringProfile": {
            "CanonicalLeagueID": league_id,
            "Season": scoring_season,
        },
        "Tolerance": tolerance,
        "TotalLeaguePlayerWeeks": total_league_player_weeks,
        "ComparedPlayerWeeks": compared_player_weeks,
        "ExactMatches": exact_matches,
        "MissingCanonicalStatZeroPointPlayerWeeks": missing_zero_points,
        "MissingCanonicalStatNonZeroPointPlayerWeeks": missing_nonzero_points,
        "UnsupportedPlayerWeeks": unsupported,
        "ProviderStatDivergences": provider_divergences,
        "ScoringMismatches": scoring_mismatches,
    }


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
    record, result = score_player_week(
        root,
        args.season,
        args.week,
        args.player,
        scoring,
    )
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
