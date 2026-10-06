#!/usr/bin/env python3
"""Shadow of the Players.json scoring-derived fields on league scoring (#347 D3).

Read-only. Re-derives the Tank01-PPR based Players.json fields from canonical
source data scored with the league ScoringSettings and reports the field-level
difference. It never writes public/data. D4 is the cutover.

Subcommands:
  shadow  build the shadow, validate the salary/ranking port against the committed
          Players.json and write the diff report
  gate    permanent Sleeper gate: league PlayerPoints of final weeks versus our scorer
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from historical_fantasy_scoring import (  # noqa: E402
    applicable_scoring_keys,
    number,
    read_json,
    score_record,
)
from players_league_scoring import (  # noqa: E402,F401
    SleeperIdentityResolver,
    build_weekly_scores,
    final_regular_weeks,
    game_final_regular_weeks,
    league_owned_sleeper_ids,
    league_scoring_settings,
    net_round,
    resolve_league_week_bounds,
    played_weeks,
    season_view,
)

LEAGUE_ID = "nfl-reise"
HISTORY_SEASONS = ("SeasonMinus1", "SeasonMinus2", "SeasonMinus3")
CURRENT_BLEND = {1: 0.25, 2: 0.35, 3: 0.5, 4: 0.75}
GATE_MIN_EXACT_RATE = 0.995
GATE_MAX_ABS_DIFF = 2.0

# Scalar Players.json fields the shadow recomputes.
SCALAR_FIELDS = (
    "Salary",
    "SalaryProjected",
    "GamesPlayed",
    "SnapsTotal",
    "AttemptsTotal",
    "FantasyPointsTotal",
    "FantasyPointsAvgGame",
    "FantasyPointsAvgPotentialGame",
    "FantasyPointsAvgSnap",
    "FantasyPointsAvgAttempt",
    "TouchdownsTotal",
    "TouchdownsPassing",
    "TouchdownsReceiving",
    "TouchdownsRushing",
)
POINT_HISTORY_FIELDS = ("Total", "AvgGame", "AvgPotentialGame", "GamesPlayed", "PotentialGames")


# --------------------------------------------------------------------------- #
# Salary and ranking: port of RequestPlayers.ps1 / PlayerUtils.psm1 (unchanged)
# --------------------------------------------------------------------------- #
def ps_round(value: float) -> float:
    """[math]::Round default (banker's rounding)."""
    return float(round(value))


def map_salary_nonlinear(points: float, source_max: float = 20.0, target_max: float = 50_000_000.0) -> float:
    normalized = points / source_max
    scaled = math.pow(max(normalized, 0), 2)
    if normalized > 1:
        scaled = 1 + (normalized - 1) * 2
    return scaled * target_max


def salary_with_floor(p1: float, p2: float, p3: float, w1: float = 0.5, w2: float = 0.33, w3: float = 0.17) -> float:
    if p1 == 0 and p2 == 0:
        return 0.0
    if p1 >= p2 and p1 >= p3:
        ratio, maximum = w1, p1
    elif p2 >= p1 and p2 >= p3:
        ratio, maximum = w2, p2
    else:
        ratio, maximum = w3, p3
    floor = maximum * ratio
    p1, p2, p3 = max(p1, floor), max(p2, floor), max(p3, floor)
    return ps_round(map_salary_nonlinear((p1 + p2 + p3) / 3))


def salaries(
    current_avg_potential: float,
    current_avg_game: float,
    point_history: dict[str, dict[str, Any]],
    *,
    final_week: int,
    weight_total: float,
    weight_game: float,
) -> tuple[float, float]:
    points_current = current_avg_potential * weight_total + current_avg_game * weight_game
    history = [
        point_history[key]["AvgPotentialGame"] * weight_total + point_history[key]["AvgGame"] * weight_game
        for key in HISTORY_SEASONS
    ]
    salary = salary_with_floor(*history)
    if final_week == 0:
        points_current = history[0]
    blend = CURRENT_BLEND.get(final_week)
    if blend is not None:
        points_current = points_current * blend + history[0] * (1 - blend)
    projected = salary_with_floor(points_current, history[0], history[1])
    return ps_round(salary), ps_round(projected)


def _rank_values(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    """Rank with gaps and ties (descending value), as Set-Rankings does."""
    ranks: dict[str, int] = {}
    previous = None
    rank = 0
    for index, item in enumerate(sorted(items, key=lambda x: x[key], reverse=True), start=1):
        value = item[key]
        if value == 0:
            continue
        if value != previous:
            rank = index
        previous = value
        ranks[item["ID"]] = rank
    return ranks


def _combined_ranks(items: list[dict[str, Any]], rank_total: dict[str, int], rank_avg: dict[str, int],
                    total_key: str, avg_key: str, weight_total: float, weight_avg: float) -> dict[str, int]:
    combined = {
        item["ID"]: rank_total[item["ID"]] * weight_total + rank_avg[item["ID"]] * weight_avg
        for item in items
        if item["ID"] in rank_total and item["ID"] in rank_avg
    }
    ordered = sorted(
        (item for item in items if combined.get(item["ID"], 0) > 0),
        key=lambda x: (combined[x["ID"]], -x[total_key], -x[avg_key]),
    )
    result: dict[str, int] = {}
    previous = None
    rank = 0
    for index, item in enumerate(ordered, start=1):
        value = combined[item["ID"]]
        if value != previous:
            rank = index
        previous = value
        result[item["ID"]] = rank
    return result


def compute_rankings(players: list[dict[str, Any]], weight_total: float, weight_game: float) -> dict[str, list[dict[str, Any]]]:
    """Ranking arrays per player ID: Add-Rankings plus Add-PreviousSeasonCombinedRanking."""
    total_key, avg_key = "FantasyPointsAvgPotentialGame", "FantasyPointsAvgGame"
    active = [p for p in players if p[total_key] > 0 and p[avg_key] > 0]
    out: dict[str, dict[str, int]] = defaultdict(dict)

    rank_total = _rank_values(active, total_key)
    rank_avg = _rank_values(active, avg_key)
    for pid, rank in rank_total.items():
        out[pid]["Total"] = rank
    for pid, rank in rank_avg.items():
        out[pid]["PerGame"] = rank
    for pid, rank in _combined_ranks(active, rank_total, rank_avg, total_key, avg_key, weight_total, weight_game).items():
        out[pid]["Combined"] = rank

    for position in sorted({p["Position"] for p in active}):
        group = [p for p in active if p["Position"] == position]
        pos_total = _rank_values(group, total_key)
        pos_avg = _rank_values(group, avg_key)
        for pid, rank in pos_total.items():
            out[pid]["Total_Pos"] = rank
        for pid, rank in pos_avg.items():
            out[pid]["PerGame_Pos"] = rank
        for pid, rank in _combined_ranks(group, pos_total, pos_avg, total_key, avg_key, weight_total, weight_game).items():
            out[pid]["Combined_Pos"] = rank

    with_history = [
        {
            "ID": p["ID"],
            "Total": p["PointHistory"]["SeasonMinus1"]["AvgPotentialGame"],
            "Game": p["PointHistory"]["SeasonMinus1"]["AvgGame"],
        }
        for p in players
        if p["PointHistory"]["SeasonMinus1"]["AvgPotentialGame"] > 0 and p["PointHistory"]["SeasonMinus1"]["AvgGame"] > 0
    ]
    prev_total = _rank_values(with_history, "Total")
    prev_game = _rank_values(with_history, "Game")
    for pid, rank in _combined_ranks(with_history, prev_total, prev_game, "Total", "Game", weight_total, weight_game).items():
        out[pid]["Combined_Previous"] = rank

    order = ("Total", "PerGame", "Combined", "Total_Pos", "PerGame_Pos", "Combined_Pos", "Combined_Previous")
    return {
        p["ID"]: [{"Type": t, "Value": out[p["ID"]][t]} for t in order if t in out.get(p["ID"], {})]
        for p in players
    }


def letter_grade(rank: int | None, position: str) -> str:
    """Get-LetterGrade of RequestPlayers.ps1 (a missing rank counts as 0)."""
    multiplier = 1.0 if position == "K" else 2.0 if position in ("RB", "WR") else 1.5
    value = rank or 0
    for limit, grade in ((6, "A"), (12, "B"), (18, "C"), (24, "D"), (30, "E")):
        if value <= limit * multiplier:
            return grade
    return "F"


def rank_grading(player: dict[str, Any]) -> dict[str, Any]:
    rank = next((r["Value"] for r in player["Ranking"] if r["Type"] == "Combined_Pos"), None)
    return {"Type": "Rank", "Value": rank, "Rank": rank, "Grade": letter_grade(rank, player["Position"])}


def compute_salary_cap(salaries_by_player: list[float], team_size: int, team_count: int) -> float:
    top = sorted(salaries_by_player, reverse=True)[: team_size * team_count]
    return ps_round(sum(top) / len(top) * team_size * 0.9)


# --------------------------------------------------------------------------- #
# Canonical inputs
# --------------------------------------------------------------------------- #
def read_ps_config_weights(repo_root: Path) -> tuple[float, float]:
    text = (repo_root / "public/requests/config.ps1").read_text(encoding="utf-8-sig")
    weights = []
    for name in ("WeightTotal", "WeightGame"):
        match = re.search(rf"\$Global:{name}\s*=\s*([0-9.]+)", text)
        if not match:
            raise ValueError(f"config.ps1 has no {name}")
        weights.append(float(match.group(1)))
    return weights[0], weights[1]


# --------------------------------------------------------------------------- #
# Shadow
# --------------------------------------------------------------------------- #
def derive_player(
    legacy: dict[str, Any],
    weeks_by_season: dict[int, dict[int, dict[str, float]]],
    *,
    season: int,
    last_week: int,
    final_week: int,
    final_weeks_current: set[int],
    weight_total: float,
    weight_game: float,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Return the shadow player and per-row counters (non-final games kept legacy)."""
    position = legacy["Position"]
    new = copy.deepcopy(legacy)
    counters: Counter = Counter()

    point_history = {
        key: season_view(weeks_by_season.get(season - offset, {}), position, last_week, last_week - 1)
        for offset, key in enumerate(HISTORY_SEASONS, start=1)
    }
    current_games = played_weeks(weeks_by_season.get(season, {}), position, last_week)
    count = len(current_games)
    total = net_round(sum(g["points"] for g in current_games.values()), 2)
    exact_total = sum(g["points"] for g in current_games.values())
    potential = int(legacy["GamesPotential"])
    avg_game = net_round(exact_total / count, 2) if count else 0
    avg_potential = net_round(exact_total / potential, 2) if potential > 0 else 0
    snaps = int(sum(g["kick_attempts"] if position == "K" else g["snaps"] for g in current_games.values()))
    attempts = int(sum(g["attempts"] for g in current_games.values()))

    new["GamesPlayed"] = count
    new["SnapsTotal"] = snaps
    new["AttemptsTotal"] = attempts
    new["FantasyPointsTotal"] = total
    new["FantasyPointsAvgGame"] = avg_game
    new["FantasyPointsAvgPotentialGame"] = avg_potential
    new["FantasyPointsAvgSnap"] = net_round(exact_total / snaps, 5) if snaps > 0 else 0
    new["FantasyPointsAvgAttempt"] = net_round(exact_total / attempts, 5) if attempts > 0 else 0
    td_pass = int(sum(g["td_pass"] for g in current_games.values()))
    td_rec = int(sum(g["td_rec"] for g in current_games.values()))
    td_rush = int(sum(g["td_rush"] for g in current_games.values()))
    new["TouchdownsPassing"], new["TouchdownsReceiving"], new["TouchdownsRushing"] = td_pass, td_rec, td_rush
    new["TouchdownsTotal"] = td_pass + td_rec + td_rush
    new["PointHistory"] = point_history
    new["Salary"], new["SalaryProjected"] = salaries(
        avg_potential, avg_game, point_history,
        final_week=final_week, weight_total=weight_total, weight_game=weight_game,
    )

    # GameHistory[].FantasyPoints: final REG weeks get canonical points, others keep legacy.
    current_weeks = weeks_by_season.get(season, {})
    for entry in new.get("GameHistory") or []:
        week = int(entry["GameDetails"]["Week"])
        if entry["GameDetails"].get("WeekPlayoff") or week not in final_weeks_current:
            counters["game_history_kept_legacy"] += 1
            continue
        row = current_weeks.get(week)
        entry["FantasyPoints"] = net_round(row["points"], 2) if row else 0.0
        counters["game_history_rescored"] += 1
    # Grading.Form repeats the last four final and scored games of GameHistory.
    final_scored = [e for e in new.get("GameHistory") or []
                    if e["GameDetails"].get("WeekFinal") and e["GameDetails"].get("WeekScored")][:4]
    for grading in new.get("Grading") or []:
        if grading.get("Type") == "Form":
            grading["Value"] = copy.deepcopy(final_scored)
    return new, dict(counters)


def apply_identity_hold(new: dict[str, Any], legacy: dict[str, Any]) -> dict[str, Any]:
    """identity_hold rows keep every legacy value."""
    held = copy.deepcopy(legacy)
    held["Ranking"] = []  # re-ranked with everyone else
    return held


def build_shadow(repo_root: Path, league_id: str = LEAGUE_ID) -> dict[str, Any]:
    players: list[dict[str, Any]] = read_json_bom(repo_root / "public/data/Players.json")
    league = read_json_bom(repo_root / "public/data/League.json")
    season = int(league["Season"])
    bounds = resolve_league_week_bounds(repo_root, league_id, season)
    last_week = bounds["LastLeagueWeek"]
    final_week = bounds["FinalScoredWeek"]
    team_size = int(league["SalaryRelevantTeamSize"])
    team_count = len(league.get("Teams") or [])
    weight_total, weight_game = read_ps_config_weights(repo_root)
    scoring = league_scoring_settings(repo_root, league_id, season)
    final_weeks_current = final_regular_weeks(repo_root, season)

    resolver = SleeperIdentityResolver.from_repo(repo_root)
    owned = league_owned_sleeper_ids(repo_root, league_id, season)
    seasons = tuple(season - offset for offset in (3, 2, 1, 0))
    identity_of: dict[str, dict[int, str | None]] = {}
    identity_hold: list[dict[str, Any]] = []
    for player in players:
        # Season-aware, as the D4 export: the Sleeper ID may belong to another person in an earlier season.
        current, status = resolver.resolve(str(player["ID"]), season)
        if current is None:
            identity_hold.append({
                "SleeperID": player["ID"], "Name": player["Name"], "Position": player["Position"],
                "Reason": status, "LeagueOwned": str(player["ID"]) in owned,
            })
            continue
        identity_of[player["ID"]] = {s: resolver.resolve(str(player["ID"]), s)[0] for s in seasons}
    wanted = {cid for per_season in identity_of.values() for cid in per_season.values() if cid}

    weekly, unsupported, scan_counts = build_weekly_scores(
        repo_root, seasons, season, final_weeks_current, wanted, scoring,
    )

    port = validate_legacy_port(players, league, weight_total, weight_game, final_week)

    shadow_players: list[dict[str, Any]] = []
    counters: Counter = Counter()
    history_loss: list[dict[str, Any]] = []
    held_ids = {row["SleeperID"] for row in identity_hold}
    for legacy in players:
        if legacy["ID"] in held_ids:
            shadow_players.append(apply_identity_hold(legacy, legacy))
            continue
        per_season = identity_of[legacy["ID"]]
        cid = per_season[season]
        weeks_by_season = {s: weekly[s].get(per_season[s], {}) if per_season[s] else {} for s in seasons}
        new, row_counts = derive_player(
            legacy, weeks_by_season, season=season, last_week=last_week, final_week=final_week,
            final_weeks_current=final_weeks_current, weight_total=weight_total, weight_game=weight_game,
        )
        counters.update(row_counts)
        shadow_players.append(new)
        lost = [
            key for key in HISTORY_SEASONS
            if legacy["PointHistory"][key]["GamesPlayed"] > 0 and new["PointHistory"][key]["GamesPlayed"] == 0
        ]
        if legacy["GamesPlayed"] > 0 and new["GamesPlayed"] == 0:
            lost.append("Current")
        if lost:
            history_loss.append({
                "SleeperID": legacy["ID"], "Name": legacy["Name"], "Position": legacy["Position"],
                "CanonicalPlayerID": cid, "LostSeasons": lost, "LeagueOwned": legacy["ID"] in owned,
                "LegacyPointsLost": round(
                    sum(legacy["PointHistory"][k]["Total"] for k in HISTORY_SEASONS if k in lost)
                    + (legacy["FantasyPointsTotal"] if "Current" in lost else 0), 2),
            })

    rankings = compute_rankings(shadow_players, weight_total, weight_game)
    for player in shadow_players:
        player["Ranking"] = rankings[player["ID"]]
        player["Grading"] = [g for g in player.get("Grading") or [] if g.get("Type") != "Rank"] + [rank_grading(player)]

    cap_new = compute_salary_cap([p["Salary"] for p in shadow_players], team_size, team_count)
    cap_projected_new = compute_salary_cap([p["SalaryProjected"] for p in shadow_players], team_size, team_count)
    return {
        "season": season,
        "lastWeek": last_week,
        "finalWeek": final_week,
        "finalWeeksCurrent": sorted(final_weeks_current),
        "weights": {"total": weight_total, "game": weight_game},
        "legacy": players,
        "shadow": shadow_players,
        "leagueOwnedIds": sorted(owned),
        "identityHold": identity_hold,
        "historyLoss": history_loss,
        "unsupportedNonZeroSettings": {f"{s}:{k}": v for (s, k), v in sorted(unsupported.items())},
        "counters": {**dict(counters), **dict(scan_counts)},
        "portValidation": port,
        "cap": {
            "published": [league["SalaryCap"], league["SalaryCapProjected"]],
            "recomputedLegacy": port["cap"],
            "shadow": [cap_new, cap_projected_new],
        },
    }


def read_json_bom(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _salary_mismatches(players: list[dict[str, Any]], weight_total: float, weight_game: float, final_week: int) -> Counter:
    mismatches: Counter = Counter()
    for p in players:
        sal, proj = salaries(
            p["FantasyPointsAvgPotentialGame"], p["FantasyPointsAvgGame"], p["PointHistory"],
            final_week=final_week, weight_total=weight_total, weight_game=weight_game,
        )
        if sal != p["Salary"]:
            mismatches["Salary"] += 1
        if proj != p["SalaryProjected"]:
            mismatches["SalaryProjected"] += 1
    return mismatches


def validate_legacy_port(players: list[dict[str, Any]], league: dict[str, Any], weight_total: float, weight_game: float, final_week: int) -> dict[str, Any]:
    """Re-derive Salary/SalaryProjected/Ranking/Avg* from the committed legacy inputs.

    The committed Players.json is rebuilt only a few times a day, so it can legitimately have been
    produced at an earlier final week than the canonical bounds report now. The salary blend is
    validated against the newest final week up to the canonical one that reproduces the file.
    """
    candidates = [(_salary_mismatches(players, weight_total, weight_game, week), week) for week in range(final_week, -1, -1)]
    salary_mismatches, produced_at = min(candidates, key=lambda c: (sum(c[0].values()), -c[1]))
    mismatches: Counter = Counter(salary_mismatches)
    recomputed: list[dict[str, Any]] = []
    for p in players:
        if p["GamesPlayed"] > 0 and net_round(p["FantasyPointsTotal"] / p["GamesPlayed"], 2) != p["FantasyPointsAvgGame"]:
            mismatches["FantasyPointsAvgGame"] += 1
        if p["SnapsTotal"] > 0 and net_round(p["FantasyPointsTotal"] / p["SnapsTotal"], 5) != p["FantasyPointsAvgSnap"]:
            mismatches["FantasyPointsAvgSnap"] += 1
        if p["AttemptsTotal"] > 0 and net_round(p["FantasyPointsTotal"] / p["AttemptsTotal"], 5) != p["FantasyPointsAvgAttempt"]:
            mismatches["FantasyPointsAvgAttempt"] += 1
        recomputed.append(p)
    rankings = compute_rankings(recomputed, weight_total, weight_game)
    for p in players:
        if rankings[p["ID"]] != p["Ranking"]:
            mismatches["Ranking"] += 1
        graded = next((g for g in p["Grading"] if g.get("Type") == "Rank"), None)
        if graded != rank_grading({**p, "Ranking": rankings[p["ID"]]}):
            mismatches["Grading.Rank"] += 1
    team_size = int(league["SalaryRelevantTeamSize"])
    team_count = len(league.get("Teams") or [])
    cap = [compute_salary_cap([p["Salary"] for p in players], team_size, team_count),
           compute_salary_cap([p["SalaryProjected"] for p in players], team_size, team_count)]
    return {
        "players": len(players),
        "mismatches": dict(mismatches),
        "cap": cap,
        "capMatchesPublished": cap == [league["SalaryCap"], league["SalaryCapProjected"]],
        "producedAtFinalWeek": produced_at,
    }


# --------------------------------------------------------------------------- #
# Diff
# --------------------------------------------------------------------------- #
def _values_differ(old: Any, new: Any) -> bool:
    if isinstance(old, (int, float)) and isinstance(new, (int, float)):
        return abs(float(old) - float(new)) > 1e-9
    return old != new


def field_diff_rows(legacy: list[dict[str, Any]], shadow: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for old, new in zip(legacy, shadow):
        assert old["ID"] == new["ID"]
        base = {"SleeperID": old["ID"], "Name": old["Name"], "Position": old["Position"], "Team": old["TeamAbbr"]}
        for field in SCALAR_FIELDS:
            if _values_differ(old[field], new[field]):
                rows.append({**base, "Field": field, "Old": old[field], "New": new[field]})
        for key in HISTORY_SEASONS:
            for field in POINT_HISTORY_FIELDS:
                if _values_differ(old["PointHistory"][key][field], new["PointHistory"][key][field]):
                    rows.append({**base, "Field": f"PointHistory.{key}.{field}",
                                 "Old": old["PointHistory"][key][field], "New": new["PointHistory"][key][field]})
        old_rank = {r["Type"]: r["Value"] for r in old["Ranking"]}
        new_rank = {r["Type"]: r["Value"] for r in new["Ranking"]}
        for rank_type in sorted(set(old_rank) | set(new_rank)):
            if old_rank.get(rank_type) != new_rank.get(rank_type):
                rows.append({**base, "Field": f"Ranking.{rank_type}",
                             "Old": old_rank.get(rank_type), "New": new_rank.get(rank_type)})
        old_grade = next((g for g in old["Grading"] if g.get("Type") == "Rank"), {})
        new_grade = next((g for g in new["Grading"] if g.get("Type") == "Rank"), {})
        for grade_field in ("Rank", "Grade"):
            if old_grade.get(grade_field) != new_grade.get(grade_field):
                rows.append({**base, "Field": f"Grading.Rank.{grade_field}",
                             "Old": old_grade.get(grade_field), "New": new_grade.get(grade_field)})
        for index, (old_game, new_game) in enumerate(zip(old.get("GameHistory") or [], new.get("GameHistory") or [])):
            if _values_differ(old_game["FantasyPoints"], new_game["FantasyPoints"]):
                rows.append({**base, "Field": f"GameHistory[{old_game['GameID']}].FantasyPoints",
                             "Old": old_game["FantasyPoints"], "New": new_game["FantasyPoints"]})
    return rows


def summarize(result: dict[str, Any], diff_rows: list[dict[str, Any]]) -> dict[str, Any]:
    legacy, shadow = result["legacy"], result["shadow"]

    def group(field: str) -> str:
        if field.startswith("PointHistory."):
            return "PointHistory"
        if field.startswith("Ranking."):
            return "Ranking"
        if field.startswith("Grading."):
            return "Grading.Rank"
        if field.startswith("GameHistory["):
            return "GameHistory.FantasyPoints"
        return field

    changed_rows: dict[str, set[str]] = defaultdict(set)
    for row in diff_rows:
        changed_rows[group(row["Field"])].add(row["SleeperID"])

    def sum_by_position(key: str) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for position in sorted({p["Position"] for p in legacy}):
            old = sum(p[key] for p in legacy if p["Position"] == position)
            new = sum(p[key] for p in shadow if p["Position"] == position)
            out[position] = {"old": round(old, 2), "new": round(new, 2),
                             "pct": round((new / old - 1) * 100, 1) if old else None}
        return out

    owned = set(result["leagueOwnedIds"])
    by_position_owned: dict[str, dict[str, Any]] = {}
    for position in sorted({p["Position"] for p in legacy}):
        pairs = [(o, n) for o, n in zip(legacy, shadow) if o["Position"] == position and o["ID"] in owned]
        old_sum = sum(o["Salary"] for o, _ in pairs)
        new_sum = sum(n["Salary"] for _, n in pairs)
        by_position_owned[position] = {
            "players": len(pairs),
            "salaryChanged": sum(1 for o, n in pairs if o["Salary"] != n["Salary"]),
            "salaryOld": old_sum, "salaryNew": new_sum,
            "pct": round((new_sum / old_sum - 1) * 100, 1) if old_sum else None,
        }
    held = {row["SleeperID"] for row in result["identityHold"]}
    held_changed = sorted({r["SleeperID"] for r in diff_rows if r["SleeperID"] in held})
    return {
        "season": result["season"],
        "lastWeek": result["lastWeek"],
        "finalWeek": result["finalWeek"],
        "finalWeeksCurrent": result["finalWeeksCurrent"],
        "players": len(legacy),
        "rowsChangedPerField": {k: len(v) for k, v in sorted(changed_rows.items())},
        "diffRowCount": len(diff_rows),
        "identityHold": result["identityHold"],
        "identityHoldRowsWithChangedFields": held_changed,
        "historyLoss": result["historyLoss"],
        "unsupportedNonZeroSettings": result["unsupportedNonZeroSettings"],
        "counters": result["counters"],
        "portValidation": result["portValidation"],
        "cap": result["cap"],
        "leagueOwnedSalaryByPosition": by_position_owned,
        "leagueOwnedHistoryLoss": [r["Name"] for r in result["historyLoss"] if r["LeagueOwned"]],
        "salaryByPosition": sum_by_position("Salary"),
        "salaryProjectedByPosition": sum_by_position("SalaryProjected"),
        "fantasyPointsTotalByPosition": sum_by_position("FantasyPointsTotal"),
        "pointsSeasonMinus1ByPosition": {
            pos: {
                "old": round(sum(p["PointHistory"]["SeasonMinus1"]["Total"] for p in legacy if p["Position"] == pos), 1),
                "new": round(sum(p["PointHistory"]["SeasonMinus1"]["Total"] for p in shadow if p["Position"] == pos), 1),
            }
            for pos in sorted({p["Position"] for p in legacy})
        },
    }


# --------------------------------------------------------------------------- #
# Permanent Sleeper gate
# --------------------------------------------------------------------------- #
def classify_residual(diff: float, applicable_weights: list[float]) -> str | None:
    """Known class `yardage-correction`: a provider stat correction on a yardage-type stat.

    The residual must be smaller than the smallest discrete scoring event (weight >= 1,
    i.e. no reception, touchdown, fumble or kick event can explain it) and an exact
    multiple of a fractional yardage weight. Anything else is unclassified.
    """
    magnitude = abs(diff)
    discrete = [abs(w) for w in applicable_weights if abs(w) >= 1]
    yardage = [abs(w) for w in applicable_weights if 0 < abs(w) < 1]
    if not yardage or (discrete and magnitude >= min(discrete)):
        return None
    for weight in yardage:
        units = magnitude / weight
        if abs(units - round(units)) < 1e-6 and round(units) >= 1:
            return "yardage-correction"
    return None


def sleeper_gate(repo_root: Path, league_id: str = LEAGUE_ID) -> dict[str, Any]:
    seasons_dir = repo_root / "source-data/leagues" / league_id / "seasons"
    exact = 0
    compared = 0
    residuals: list[dict[str, Any]] = []
    skipped: Counter = Counter()
    unsupported: Counter = Counter()
    for season_dir in sorted(p for p in seasons_dir.iterdir() if p.is_dir()):
        season = int(season_dir.name)
        scoring = league_scoring_settings(repo_root, league_id, season)
        final_weeks = final_regular_weeks(repo_root, season)
        game_final_weeks = game_final_regular_weeks(repo_root, season)
        for matchup_file in sorted((season_dir / "matchups").glob("week-*.json")):
            week = int(matchup_file.stem.split("-")[1])
            if week not in final_weeks:
                # Games final but stats not completely published yet is a legitimate pending state
                # for the newest week only; an older week with a hole stays a hard failure.
                if week in game_final_weeks and week > max(final_weeks, default=0):
                    skipped[f"{season}:week-stats-pending"] += 1
                elif week in game_final_weeks:
                    raise FileNotFoundError(
                        f"Final week {season}:{week} lacks a complete canonical player-stats partition")
                else:
                    skipped[f"{season}:week-not-final"] += 1
                continue
            stats_path = repo_root / "source-data/nfl/player-stats" / str(season) / f"{week:02d}.json"
            if not stats_path.exists():
                raise FileNotFoundError(f"Final week without canonical player-stats partition: {stats_path}")
            records = {r["CanonicalPlayerID"]: r for r in read_json(stats_path)["Records"]
                       if r.get("SeasonType", "REG") == "REG" and r.get("CanonicalPlayerID")}
            events: dict[str, list[dict[str, Any]]] = defaultdict(list)
            events_path = repo_root / "source-data/nfl/special-teams-fumble-events" / str(season) / f"{week:02d}.json"
            if events_path.exists():
                for event in read_json(events_path)["Records"]:
                    events[event.get("CanonicalPlayerID")].append(event)
            for matchup in read_json(matchup_file):
                for entry in matchup.get("PlayerPoints") or []:
                    cid = (entry.get("Player") or {}).get("CanonicalPlayerID")
                    sleeper_points = entry.get("Points")
                    if not cid or sleeper_points is None:
                        skipped[f"{season}:no-canonical-id-or-points"] += 1
                        continue
                    record = records.get(cid)
                    position = record.get("Position") if record else None
                    if record:
                        result = score_record(record, scoring, special_teams_fumble_events=events[cid])
                        ours = result["FantasyPoints"]
                        for key in result["UnsupportedNonZeroSettings"]:
                            unsupported[(season, key)] += 1
                    else:
                        ours = 0.0
                    compared += 1
                    diff = round(ours - float(sleeper_points), 4)
                    if abs(diff) < 0.005:
                        exact += 1
                        continue
                    weights = [number(scoring.get(k)) for k in sorted(applicable_scoring_keys(position, scoring))
                               if number(scoring.get(k)) != 0]
                    residuals.append({
                        "Season": season, "Week": week, "CanonicalPlayerID": cid,
                        "Name": record["PlayerName"] if record else "", "Position": position or "?",
                        "Sleeper": float(sleeper_points), "Ours": round(ours, 2), "Diff": diff,
                        "Class": classify_residual(diff, weights) or "unclassified",
                    })
    return evaluate_gate(compared, exact, residuals, skipped, unsupported)


def evaluate_gate(
    compared: int,
    exact: int,
    residuals: list[dict[str, Any]],
    skipped: Counter | dict[str, int],
    unsupported: Counter | dict[Any, int],
) -> dict[str, Any]:
    exact_rate = exact / compared if compared else 0.0
    failures = []
    if compared == 0:
        failures.append("no player-weeks compared")
    if compared and exact_rate < GATE_MIN_EXACT_RATE:
        failures.append(f"exact rate {exact_rate:.4f} < {GATE_MIN_EXACT_RATE}")
    too_large = [r for r in residuals if abs(r["Diff"]) > GATE_MAX_ABS_DIFF]
    if too_large:
        failures.append(f"{len(too_large)} residual(s) with |diff| > {GATE_MAX_ABS_DIFF}")
    unclassified = [r for r in residuals if r["Class"] == "unclassified"]
    if unclassified:
        failures.append(f"{len(unclassified)} unclassified residual(s)")
    if unsupported:
        failures.append("unsupported non-zero scoring settings: "
                        + ", ".join(f"{s}:{k}" for (s, k) in sorted(unsupported)))
    return {
        "compared": compared,
        "exact": exact,
        "exactRate": round(exact_rate, 6),
        "residuals": residuals,
        "skipped": dict(skipped),
        "passed": not failures,
        "failures": failures,
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", default=LEAGUE_ID)
    sub = parser.add_subparsers(dest="command", required=True)
    shadow = sub.add_parser("shadow", help="build the shadow and write the diff report")
    shadow.add_argument("--out-dir", type=Path, required=True)
    gate = sub.add_parser("gate", help="Sleeper gate; exit 1 on failure")
    gate.add_argument("--out-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    if args.command == "gate":
        report = sleeper_gate(root, args.league)
        print(json.dumps({k: v for k, v in report.items() if k != "residuals"}, indent=2))
        for row in report["residuals"]:
            print(row)
        if args.out_dir:
            args.out_dir.mkdir(parents=True, exist_ok=True)
            write_csv(args.out_dir / "sleeper-gate-residuals.csv", report["residuals"],
                      ["Season", "Week", "CanonicalPlayerID", "Name", "Position", "Sleeper", "Ours", "Diff", "Class"])
        return 0 if report["passed"] else 1

    result = build_shadow(root, args.league)
    diff_rows = field_diff_rows(result["legacy"], result["shadow"])
    summary = summarize(result, diff_rows)
    gate_report = sleeper_gate(root, args.league)
    summary["sleeperGate"] = {k: v for k, v in gate_report.items() if k != "residuals"}
    summary["sleeperGate"]["residualCount"] = len(gate_report["residuals"])
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "players-scoring-shadow-diff.csv", diff_rows, ["SleeperID", "Name", "Position", "Team", "Field", "Old", "New"])
    write_csv(out / "players-scoring-shadow-history-loss.csv",
              [{**r, "LostSeasons": ";".join(r["LostSeasons"])} for r in result["historyLoss"]],
              ["SleeperID", "Name", "Position", "CanonicalPlayerID", "LostSeasons", "LegacyPointsLost", "LeagueOwned"])
    write_csv(out / "players-scoring-shadow-sleeper-residuals.csv", gate_report["residuals"],
              ["Season", "Week", "CanonicalPlayerID", "Name", "Position", "Sleeper", "Ours", "Diff", "Class"])
    (out / "players-scoring-shadow-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("players", "rowsChangedPerField", "portValidation", "cap", "sleeperGate")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
