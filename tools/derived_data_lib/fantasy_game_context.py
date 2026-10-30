"""FantasyGameContext of one matchup week as a pure function (ADR-075, Issue #1199 section 3).

Port of FantasyGameContextCore.ps1 with its overlays (FantasyRelevanceV2Utils, FantasyMatchupPreviewUtils,
FantasyWeeklyWatchUtils, FantasyGameContextUtils score and market context). The result is computed from the Decision Windows
facts, the paired fantasy matchup facts and the NFL schedule; nothing is persisted here. The only intended value change against
the PowerShell model is the counterfactual week-final rule: ``week_is_final`` comes from the shared LeagueScoredWeek milestone
(ADR-071) instead of Sleeper ``last_scored_leg`` (decision M2).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT

from .matchup_context import (
    MatchupContextError,
    _blank,
    _read,
    _text,
    current_matchup_rows,
    fantasy_matchup_id,
    matchup_load_week,
    parse_instant_text,
    to_int,
    value_of,
)

LOG = logging.getLogger(__name__)
FINAL_STATUS = re.compile(r"^Final", re.IGNORECASE)
_UNSET: Any = object()


def _s(value: Any) -> str:
    """Sort/compare text of an optional value (PowerShell ``[string]`` of null is empty)."""
    return "" if value is None else str(value)


def _sum(values: list[float]) -> float:
    """Sequential double sum (Measure-Object -Sum); ``sum`` would use compensated summation on newer Pythons."""
    total = 0.0
    for value in values:
        total += value
    return total


def _opt_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


# ---------------------------------------------------------------------------------------------------------------------
# Paired fantasy matchup facts


def point_map(value: Any) -> dict[str, float]:
    """Player points of a Sleeper ``players_points`` object; the positional ``starters_points`` array yields an empty map."""
    if not isinstance(value, dict):
        return {}
    return {str(key): float(points) for key, points in value.items() if points is not None}


def _player_fact(player_id: str, canonical_id: str | None, is_starter: bool, points: float | None, has_points: bool) -> dict[str, Any]:
    return {"PlayerID": player_id, "CanonicalPlayerID": canonical_id, "IsStarter": is_starter, "HasPoints": has_points, "Points": points}


def paired_matchup_facts(season: str, week: int, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Two-team fantasy matchups of one week sorted by FantasyMatchupID (ConvertTo-FgcPairedMatchupFacts)."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row["ProviderMatchupID"], []).append(row)
    owner: dict[str, str] = {}
    result: list[dict[str, Any]] = []
    for name in sorted(groups):
        participants = sorted(groups[name], key=lambda r: str(r["FantasyTeamID"]))
        if len(participants) != 2:
            LOG.warning("Excluding malformed fantasy matchup '%s' in Week %s because it has %s participants.", name, week, len(participants))
            continue
        team_ids = [str(p["FantasyTeamID"]) for p in participants]
        matchup_id = fantasy_matchup_id(season, week, team_ids)
        for participant in participants:
            for player in participant["Players"]:
                known = owner.get(player["PlayerID"])
                if known is not None and known != str(participant["FantasyTeamID"]):
                    raise MatchupContextError(f"Fantasy matchup evidence assigns PlayerID '{player['PlayerID']}' to multiple fantasy teams in Week {week}.")
                owner[player["PlayerID"]] = str(participant["FantasyTeamID"])
        result.append(
            {
                "FantasyMatchupID": matchup_id,
                "TeamIDs": team_ids,
                "Teams": [
                    {
                        "FantasyTeamID": str(p["FantasyTeamID"]),
                        "Players": sorted(p["Players"], key=lambda pl: pl["PlayerID"]),
                        "FinalScore": p["FinalScore"],
                        "HasCustomPoints": bool(p["HasCustomPoints"]),
                    }
                    for p in participants
                ],
            }
        )
    result.sort(key=lambda m: m["FantasyMatchupID"])
    return result


def current_matchup_facts(season: str, week: int, matchup_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Paired facts of the strict current-week rows in the legacy Sleeper shape (ConvertTo-FgcCurrentMatchupFacts)."""
    rows: list[dict[str, Any]] = []
    for row in matchup_rows:
        if row is None:
            continue
        provider_id = value_of(row, "matchup_id", "MatchupID")
        team_id = value_of(row, "roster_id", "FantasyTeamID", "TeamID")
        if provider_id is None or team_id is None:
            continue
        provider_id, team_id = str(provider_id).strip(), str(team_id).strip()
        if provider_id == "" or team_id == "":
            continue
        player_ids = sorted({str(p).strip() for p in (value_of(row, "players", "Players") or []) if not _blank(p)})
        starter_ids = sorted({str(p).strip() for p in (value_of(row, "starters", "Starters") or []) if not _blank(p)})
        for starter_id in starter_ids:
            if starter_id not in player_ids:
                raise MatchupContextError(f"Fantasy matchup Week {week} Team '{team_id}' has starter '{starter_id}' outside the rostered player set.")
        player_points = point_map(value_of(row, "players_points", "PlayerPoints"))
        starter_points = point_map(value_of(row, "starters_points", "StarterPoints"))
        if not starter_points:
            starter_points = {s: player_points[s] for s in starter_ids if s in player_points}
        players = []
        for player_id in player_ids:
            is_starter = player_id in starter_ids
            has_points = player_id in player_points
            points = player_points[player_id] if has_points else None
            if is_starter and player_id in starter_points:
                has_points, points = True, starter_points[player_id]
            players.append(_player_fact(player_id, None, is_starter, points, has_points))
        score = value_of(row, "points", "Points")
        rows.append(
            {
                "ProviderMatchupID": provider_id,
                "FantasyTeamID": team_id,
                "Players": players,
                "FinalScore": None if score is None else float(score),
                "HasCustomPoints": value_of(row, "custom_points", "CustomPoints") is not None,
            }
        )
    return paired_matchup_facts(season, week, rows)


def outcome_state(left: float, right: float) -> str:
    if left > right:
        return "left"
    if right > left:
        return "right"
    return "tie"


# ---------------------------------------------------------------------------------------------------------------------
# Base context (New-FantasyGameContextReadModel of FantasyGameContextCore.ps1)


def _base_context(
    league_id: Any,
    season: str,
    week: int,
    decision_facts: Any,
    matchups: list[dict[str, Any]],
    schedule: list[dict[str, Any]],
    week_is_final: bool,
    team_key: Callable[[Any], str | None],
) -> dict[str, Any]:
    matchup_by_team: dict[str, dict[str, Any]] = {}
    team_fact_by_id: dict[str, dict[str, Any]] = {}
    for matchup in matchups:
        for team in matchup["Teams"]:
            key = str(team["FantasyTeamID"])
            if key in matchup_by_team:
                raise MatchupContextError(f"Fantasy Team '{key}' appears in multiple fantasy matchups in Week {week}.")
            matchup_by_team[key] = matchup
            team_fact_by_id[key] = team

    status_by_game: dict[str, str] = {}
    for row in schedule:
        game_id = _s(value_of(row, "gameID", "GameID"))
        if game_id.strip() != "":
            status_by_game[game_id] = _s(value_of(row, "gameStatus", "Status"))

    game_meta: dict[str, dict[str, Any]] = {}
    windows = list(value_of(decision_facts, "DecisionWindows") or [])
    for window in windows:
        for game in value_of(window, "Games") or []:
            game_id = _s(game["GameID"])
            game_meta[game_id] = {
                "GameID": game_id,
                "DecisionWindowID": _s(window["DecisionWindowID"]),
                "StartsAtUtc": _s(window["StartsAtUtc"]),
                "AwayTeamID": _s(game.get("AwayTeamID")),
                "AwayTeamAbbr": game.get("AwayTeamAbbr"),
                "HomeTeamID": _s(game.get("HomeTeamID")),
                "HomeTeamAbbr": game.get("HomeTeamAbbr"),
                "Status": status_by_game.get(game_id),
            }

    associations_by_game: dict[str, list[dict[str, Any]]] = {}
    non_game: list[dict[str, Any]] = []
    for lock in value_of(decision_facts, "PlayerLockFacts") or []:
        team_id = _s(lock.get("FantasyTeamID"))
        matchup = matchup_by_team.get(team_id)
        team_fact = team_fact_by_id.get(team_id)
        player_fact = None
        if team_fact is not None:
            player_fact = next((p for p in team_fact["Players"] if p["PlayerID"] == _s(lock.get("PlayerID"))), None)
        base = {
            "FantasyTeamID": team_id,
            "FantasyMatchupID": matchup["FantasyMatchupID"] if matchup is not None else None,
            "PlayerID": _s(lock.get("PlayerID")),
            "NFLTeamID": lock.get("NFLTeamID"),
            "IsStarter": bool(lock.get("IsStarter")),
        }
        if _s(lock.get("Kind")) != "scheduled" or _s(lock.get("GameID")).strip() == "" or matchup is None or player_fact is None:
            if matchup is None:
                kind, reason = "unknown", "missing-fantasy-matchup"
            elif player_fact is None:
                kind, reason = _s(lock.get("Kind")), "missing-weekly-player-scoring-fact"
            else:
                kind, reason = _s(lock.get("Kind")), _s(lock.get("Kind"))
            non_game.append({**base, "Kind": kind, "Reason": reason})
            continue
        game_id = _s(lock["GameID"])
        if game_id not in game_meta:
            non_game.append({**base, "Kind": "unknown", "Reason": "missing-game-fact"})
            continue
        associations_by_game.setdefault(game_id, []).append(
            {**base, "HasPoints": bool(player_fact["HasPoints"]), "Points": player_fact["Points"]}
        )

    def assoc_key(a: dict[str, Any]) -> tuple[str, str, str]:
        return (_s(a["FantasyMatchupID"]), a["FantasyTeamID"], a["PlayerID"])

    matchup_game_rows: dict[str, list[dict[str, Any]]] = {}
    games: list[dict[str, Any]] = []
    for game_id in sorted(game_meta):
        meta = game_meta[game_id]
        associations = sorted(associations_by_game.get(game_id, []), key=assoc_key)
        team_groups: dict[str, list[dict[str, Any]]] = {}
        for association in associations:
            team_groups.setdefault(association["FantasyTeamID"], []).append(association)
        fantasy_teams: list[dict[str, Any]] = []
        for team_id, group in team_groups.items():
            players = sorted(group, key=lambda a: a["PlayerID"])
            matchup_id = _s(players[0]["FantasyMatchupID"])
            fantasy_team = {
                "FantasyTeamID": team_id,
                "FantasyMatchupID": matchup_id,
                "RosteredPlayerCount": len(players),
                "StarterCount": sum(1 for p in players if p["IsStarter"]),
                "RosteredPoints": round(_sum([p["Points"] for p in players if p["HasPoints"]]), 4),
                "StarterPoints": round(_sum([p["Points"] for p in players if p["HasPoints"] and p["IsStarter"]]), 4),
                "Players": [
                    {"PlayerID": p["PlayerID"], "IsStarter": p["IsStarter"], "Points": p["Points"] if p["HasPoints"] else None} for p in players
                ],
            }
            fantasy_teams.append(fantasy_team)
            matchup_game_rows.setdefault(f"{matchup_id}|{game_id}", []).append(fantasy_team)

        away_key, home_key = team_key(meta["AwayTeamID"]), team_key(meta["HomeTeamID"])
        unknown_for_game = sum(
            1
            for a in non_game
            if not _blank(a["NFLTeamID"]) and team_key(a["NFLTeamID"]) in (away_key, home_key)
        )
        has_points = any(a["HasPoints"] for a in associations)
        is_final_game = FINAL_STATUS.match(_s(meta["Status"])) is not None
        impact_state = "unavailable" if not has_points else ("final" if is_final_game else "partial")
        games.append(
            {
                "GameID": game_id,
                "DecisionWindowID": meta["DecisionWindowID"],
                "StartsAtUtc": meta["StartsAtUtc"],
                "AwayTeamID": meta["AwayTeamID"],
                "AwayTeamAbbr": meta["AwayTeamAbbr"],
                "HomeTeamID": meta["HomeTeamID"],
                "HomeTeamAbbr": meta["HomeTeamAbbr"],
                "Status": meta["Status"],
                "Relevance": {
                    "RosteredPlayerCount": len(associations),
                    "StarterCount": sum(1 for a in associations if a["IsStarter"]),
                    "FantasyTeamCount": len({a["FantasyTeamID"] for a in associations}),
                    "FantasyMatchupCount": len({a["FantasyMatchupID"] for a in associations}),
                    "UnknownAssociationCount": unknown_for_game,
                },
                "Impact": {
                    "State": impact_state,
                    "RosteredPoints": round(_sum([a["Points"] for a in associations if a["HasPoints"]]), 4) if has_points else None,
                    "StarterPoints": round(_sum([a["Points"] for a in associations if a["HasPoints"] and a["IsStarter"]]), 4) if has_points else None,
                    "OutcomeSwingMatchupCount": 0,
                },
                "FantasyTeams": sorted(fantasy_teams, key=lambda t: (t["FantasyMatchupID"], t["FantasyTeamID"])),
            }
        )

    games_sorted = sorted(games, key=lambda g: (g["StartsAtUtc"], g["GameID"]))
    views: list[dict[str, Any]] = []
    for matchup in sorted(matchups, key=lambda m: m["FantasyMatchupID"]):
        team_ids = list(matchup["TeamIDs"])
        left_id, right_id = str(team_ids[0]), str(team_ids[1])
        left_fact = next(t for t in matchup["Teams"] if str(t["FantasyTeamID"]) == left_id)
        right_fact = next(t for t in matchup["Teams"] if str(t["FantasyTeamID"]) == right_id)
        official = (
            week_is_final
            and left_fact["FinalScore"] is not None
            and right_fact["FinalScore"] is not None
            and not left_fact["HasCustomPoints"]
            and not right_fact["HasCustomPoints"]
        )
        actual = outcome_state(left_fact["FinalScore"], right_fact["FinalScore"]) if official else None
        game_rows: list[dict[str, Any]] = []
        for game in games_sorted:
            sides = matchup_game_rows.get(f"{matchup['FantasyMatchupID']}|{game['GameID']}")
            if sides is None:
                continue
            left_side = next((s for s in sides if str(s["FantasyTeamID"]) == left_id), None)
            right_side = next((s for s in sides if str(s["FantasyTeamID"]) == right_id), None)
            left_points = float(left_side["StarterPoints"]) if left_side is not None else 0.0
            right_points = float(right_side["StarterPoints"]) if right_side is not None else 0.0
            changed = None
            without_left = without_right = None
            if official:
                without_left = float(left_fact["FinalScore"]) - left_points
                without_right = float(right_fact["FinalScore"]) - right_points
                changed = outcome_state(without_left, without_right) != actual
                if changed:
                    game["Impact"]["OutcomeSwingMatchupCount"] += 1
            game_rows.append(
                {
                    "GameID": game["GameID"],
                    "DecisionWindowID": game["DecisionWindowID"],
                    "StartsAtUtc": game["StartsAtUtc"],
                    "LeftStarterCount": int(left_side["StarterCount"]) if left_side is not None else 0,
                    "RightStarterCount": int(right_side["StarterCount"]) if right_side is not None else 0,
                    "LeftRosteredPlayerCount": int(left_side["RosteredPlayerCount"]) if left_side is not None else 0,
                    "RightRosteredPlayerCount": int(right_side["RosteredPlayerCount"]) if right_side is not None else 0,
                    "LeftStarterPoints": left_points,
                    "RightStarterPoints": right_points,
                    "StarterPointDelta": round(left_points - right_points, 4),
                    "OutcomeChangedWithoutGame": changed,
                    "ScoreWithoutGame": {"Left": round(without_left, 4), "Right": round(without_right, 4)} if official else None,
                }
            )
        if official:
            counterfactual = "available"
        elif week_is_final and (left_fact["HasCustomPoints"] or right_fact["HasCustomPoints"]):
            counterfactual = "unavailable-custom-score"
        elif week_is_final:
            counterfactual = "unavailable-final-score"
        else:
            counterfactual = "unavailable-not-final"
        views.append(
            {
                "FantasyMatchupID": matchup["FantasyMatchupID"],
                "TeamIDs": team_ids,
                "FinalScores": {"Left": float(left_fact["FinalScore"]), "Right": float(right_fact["FinalScore"])} if official else None,
                "CounterfactualState": counterfactual,
                "Games": game_rows,
            }
        )

    decision_windows = [
        {
            "DecisionWindowID": _s(w["DecisionWindowID"]),
            "StartsAtUtc": _s(w["StartsAtUtc"]),
            "GameIDs": sorted(_s(g["GameID"]) for g in w.get("Games") or []),
        }
        for w in sorted(windows, key=lambda w: _s(w["StartsAtUtc"]))
    ]
    if week_is_final:
        scoring_state = "final"
    elif any(g["Impact"]["State"] != "unavailable" for g in games_sorted):
        scoring_state = "partial"
    else:
        scoring_state = "pending"
    return {
        "SchemaVersion": 1,
        "LeagueID": league_id,
        "Season": season,
        "Week": week,
        "ScoringState": scoring_state,
        "DecisionWindows": decision_windows,
        "Games": games_sorted,
        "FantasyMatchups": views,
        "NonGameAssociations": sorted(non_game, key=assoc_key),
    }


# ---------------------------------------------------------------------------------------------------------------------
# Fantasy Relevance context (Add-FantasyRelevanceContext)


def _unique(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _group_by(items: list[dict[str, Any]], key: str) -> list[tuple[str, list[dict[str, Any]]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(item[key], []).append(item)
    return list(groups.items())


def _ordered_windows(items: list[dict[str, Any]], parse: Callable[[str], Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    return sorted(_group_by(items, "DecisionWindowID"), key=lambda g: parse(g[1][0]["StartsAtUtc"]))


def _scalar_if_single(values: list[str]) -> Any:
    """PowerShell unrolls a one-element array and an empty array assigned from an ``if`` expression."""
    if not values:
        return None
    return values[0] if len(values) == 1 else values


def add_relevance_context(context: dict[str, Any], decision_facts: Any, parse: Callable[[str], Any]) -> dict[str, Any]:
    relevance = value_of(decision_facts, "FantasyRelevance")
    if relevance is None:
        return context
    team_state = {_s(t["FantasyTeamID"]): t for t in relevance.get("Teams") or []}
    matchup_by_team = {str(team_id): m for m in context["FantasyMatchups"] for team_id in m["TeamIDs"]}

    paths: list[dict[str, Any]] = []
    for team_id in sorted(team_state):
        matchup = matchup_by_team.get(team_id)
        if matchup is None:
            continue
        for player in team_state[team_id].get("Players") or []:
            direct = player.get("HasDirectScoringPath")
            if direct is None:
                has_direct = player.get("Placement") == "starter" and _s(player.get("GameState")) in ("unlocked", "locked-active")
            else:
                has_direct = bool(direct)
            path_type = None
            if player.get("Placement") == "starter" and has_direct and player.get("GameState") == "locked-active":
                path_type = "locked-starter"
            elif player.get("Placement") == "starter" and has_direct and player.get("GameState") == "unlocked":
                path_type = "unlocked-starter"
            elif player.get("IsBenchCandidate"):
                path_type = "bench-candidate"
            if path_type is None or _s(player.get("GameID")).strip() == "":
                continue
            paths.append(
                {
                    "FantasyMatchupID": matchup["FantasyMatchupID"],
                    "FantasyTeamID": team_id,
                    "PlayerID": _s(player.get("PlayerID")),
                    "GameID": _s(player["GameID"]),
                    "DecisionWindowID": _s(player.get("DecisionWindowID")),
                    "StartsAtUtc": _s(player.get("StartsAtUtc")),
                    "PathType": path_type,
                }
            )

    relevance_by_matchup: dict[str, dict[str, Any]] = {}
    for matchup in context["FantasyMatchups"]:
        matchup_id = matchup["FantasyMatchupID"]
        team_ids = [str(t) for t in matchup["TeamIDs"]]
        left_id = team_ids[0] if len(team_ids) > 0 else None
        right_id = team_ids[1] if len(team_ids) > 1 else None
        matchup_paths = [p for p in paths if p["FantasyMatchupID"] == matchup_id]
        left_paths = [p for p in matchup_paths if p["FantasyTeamID"] == left_id]
        right_paths = [p for p in matchup_paths if p["FantasyTeamID"] == right_id]
        ordered = _ordered_windows([p for p in matchup_paths if p["DecisionWindowID"].strip() != ""], parse)
        active = [g for g in ordered if any(p["PathType"] == "locked-starter" for p in g[1])]
        next_group = active[0] if active else (ordered[0] if ordered else None)
        final_group = ordered[-1] if ordered else None
        final_committed = bool(final_group) and all(p["PathType"] == "locked-starter" for p in final_group[1])
        if left_paths and right_paths:
            state = "both-sides"
        elif left_paths:
            state = "left-only"
        elif right_paths:
            state = "right-only"
        else:
            state = "none"
        remaining = {
            "State": state,
            "HasRemainingScoringPaths": len(matchup_paths) > 0,
            "LeftRemainingPathCount": len(left_paths),
            "RightRemainingPathCount": len(right_paths),
            "LockedActiveStarterCount": sum(1 for p in matchup_paths if p["PathType"] == "locked-starter"),
            "UnlockedStarterCount": sum(1 for p in matchup_paths if p["PathType"] == "unlocked-starter"),
            "EligibleBenchCandidateCount": sum(1 for p in matchup_paths if p["PathType"] == "bench-candidate"),
            "NextScoringWindowID": next_group[0] if next_group else None,
            "NextScoringGameIDs": _scalar_if_single(sorted(set(p["GameID"] for p in next_group[1]))) if next_group else None,
            "FinalScoringWindowID": final_group[0] if final_group else None,
            "FinalScoringGameIDs": _scalar_if_single(sorted(set(p["GameID"] for p in final_group[1]))) if final_group else None,
            "IsFinalScoringWindowCommitted": final_committed,
        }
        matchup["RemainingRelevance"] = remaining
        relevance_by_matchup[matchup_id] = remaining

    for game in context["Games"]:
        game_paths = [p for p in paths if p["GameID"] == game["GameID"]]
        matchup_ids = _unique([p["FantasyMatchupID"] for p in game_paths])
        direct_paths = [p for p in game_paths if p["PathType"] in ("locked-starter", "unlocked-starter")]
        direct_team_ids = sorted(set(p["FantasyTeamID"] for p in direct_paths))
        two_sided = final_window = committed_final = 0
        for matchup_id in matchup_ids:
            teams = {p["FantasyTeamID"] for p in game_paths if p["FantasyMatchupID"] == matchup_id}
            if len(teams) >= 2:
                two_sided += 1
            matchup_relevance = relevance_by_matchup.get(matchup_id)
            if matchup_relevance is not None and _s(matchup_relevance["FinalScoringWindowID"]) == _s(game["DecisionWindowID"]):
                final_window += 1
                if matchup_relevance["IsFinalScoringWindowCommitted"]:
                    committed_final += 1
        game["RemainingRelevance"] = {
            "HasRemainingRelevance": len(game_paths) > 0,
            "LockedActiveStarterCount": sum(1 for p in game_paths if p["PathType"] == "locked-starter"),
            "UnlockedStarterCount": sum(1 for p in game_paths if p["PathType"] == "unlocked-starter"),
            "EligibleBenchCandidateCount": sum(1 for p in game_paths if p["PathType"] == "bench-candidate"),
            "DirectStarterFantasyTeamCount": len(direct_team_ids),
            "DirectStarterFantasyTeamIDs": direct_team_ids,
            "FantasyMatchupCount": len(matchup_ids),
            "TwoSidedFantasyMatchupCount": two_sided,
            "FinalWindowFantasyMatchupCount": final_window,
            "CommittedFinalWindowMatchupCount": committed_final,
        }
    # MustWatchGames and MustWatchRank are owned by the weekly watch context, which replaces the first ranking of the
    # relevance context in the PowerShell chain.
    context["SchemaVersion"] = max(2, int(context["SchemaVersion"]))
    return context


# ---------------------------------------------------------------------------------------------------------------------
# Matchup preview context (Add-FantasyMatchupPreviewContext)


def _preview_path_type(player: dict[str, Any]) -> str | None:
    placement, state = _s(player.get("Placement")), _s(player.get("GameState"))
    if placement == "starter" and state == "locked-active":
        return "locked-starter"
    if placement == "starter" and state == "unlocked":
        return "unlocked-starter"
    if player.get("IsBenchCandidate"):
        return "bench-candidate"
    return None


def _primary_game_selection(window_paths: list[dict[str, Any]], eligible: tuple[str, ...]) -> dict[str, Any] | None:
    groups = [g for g in _group_by(window_paths, "GameID") if any(p["PathType"] in eligible for p in g[1])]

    def key(group: tuple[str, list[dict[str, Any]]]) -> tuple[int, int, int, str]:
        paths = group[1]
        return (
            -sum(1 for p in paths if p["PathType"] in ("locked-starter", "unlocked-starter")),
            -sum(1 for p in paths if p["PathType"] == "locked-starter"),
            -sum(1 for p in paths if p["PathType"] == "bench-candidate"),
            group[0],
        )

    groups.sort(key=key)
    if not groups:
        return None
    return {"PrimaryGameID": groups[0][0], "GameIDs": [g[0] for g in groups], "PrimaryPaths": groups[0][1]}


def _set(remaining: dict[str, Any], name: str, value: Any) -> None:
    """Add-Member -Force: the property moves to the end of the object."""
    remaining.pop(name, None)
    remaining[name] = value


def add_preview_context(context: dict[str, Any], decision_facts: Any, parse: Callable[[str], Any]) -> dict[str, Any]:
    relevance = value_of(decision_facts, "FantasyRelevance")
    if relevance is None:
        return context
    context["SchemaVersion"] = max(5, int(context["SchemaVersion"]))
    team_state = {_s(t.get("FantasyTeamID")): t for t in relevance.get("Teams") or [] if _s(t.get("FantasyTeamID")).strip() != ""}
    for matchup in context["FantasyMatchups"]:
        remaining = matchup.get("RemainingRelevance")
        if remaining is None:
            continue
        paths: list[dict[str, Any]] = []
        for team_id_value in matchup["TeamIDs"]:
            team_id = str(team_id_value)
            if team_id not in team_state:
                continue
            for player in team_state[team_id].get("Players") or []:
                path_type = _preview_path_type(player)
                if path_type is None:
                    continue
                game_id, window_id, starts_at = _s(player.get("GameID")), _s(player.get("DecisionWindowID")), _s(player.get("StartsAtUtc"))
                if game_id.strip() == "" or window_id.strip() == "" or starts_at.strip() == "":
                    continue
                paths.append(
                    {
                        "FantasyTeamID": team_id,
                        "PlayerID": _s(player.get("PlayerID")),
                        "GameID": game_id,
                        "DecisionWindowID": window_id,
                        "StartsAtUtc": starts_at,
                        "PathType": path_type,
                    }
                )
        window_groups = _ordered_windows(paths, parse)
        decision_groups = [g for g in window_groups if any(p["PathType"] in ("unlocked-starter", "bench-candidate") for p in g[1])]
        decision_group = decision_groups[0] if decision_groups else None
        selection = None
        if decision_group is not None:
            decision_paths = [p for p in decision_group[1] if p["PathType"] in ("unlocked-starter", "bench-candidate")]
            selection = _primary_game_selection(decision_paths, ("unlocked-starter", "bench-candidate"))
        if selection is None:
            for name, value in (
                ("NextLineupDecisionWindowID", None), ("NextLineupDecisionGameIDs", []), ("NextLineupDecisionPrimaryGameID", None),
                ("NextLineupDecisionWindowGameCount", 0), ("NextLineupDecisionStarterCount", 0), ("NextLineupDecisionOptionCount", 0),
            ):
                _set(remaining, name, value)
        else:
            primary = selection["PrimaryPaths"]
            _set(remaining, "NextLineupDecisionWindowID", decision_group[0])
            _set(remaining, "NextLineupDecisionGameIDs", list(selection["GameIDs"]))
            _set(remaining, "NextLineupDecisionPrimaryGameID", selection["PrimaryGameID"])
            _set(remaining, "NextLineupDecisionWindowGameCount", len(selection["GameIDs"]))
            _set(remaining, "NextLineupDecisionStarterCount", sum(1 for p in primary if p["PathType"] == "unlocked-starter"))
            _set(remaining, "NextLineupDecisionOptionCount", sum(1 for p in primary if p["PathType"] == "bench-candidate"))

        locked_groups = [g for g in window_groups if any(p["PathType"] == "locked-starter" for p in g[1])]
        unlocked_groups = [g for g in window_groups if any(p["PathType"] == "unlocked-starter" for p in g[1])]
        active_group = locked_groups[0] if locked_groups else None
        next_group = unlocked_groups[0] if unlocked_groups else None

        active_selection = _primary_game_selection(list(active_group[1]), ("locked-starter",)) if active_group is not None else None
        if active_selection is None:
            _set(remaining, "ActiveScoringWindowID", None)
            _set(remaining, "ActiveScoringGameIDs", [])
        else:
            _set(remaining, "ActiveScoringWindowID", active_group[0])
            _set(remaining, "ActiveScoringGameIDs", list(active_selection["GameIDs"]))

        scoring = _primary_game_selection(list(next_group[1]), ("unlocked-starter",)) if next_group is not None else None
        if scoring is None:
            for name, value in (
                ("NextScoringWindowID", None), ("NextScoringGameIDs", []), ("NextScoringPrimaryGameID", None), ("NextScoringWindowGameCount", 0),
                ("NextScoringLockedActiveStarterCount", 0), ("NextScoringUnlockedStarterCount", 0), ("NextScoringOptionCount", 0),
            ):
                _set(remaining, name, value)
            continue
        _set(remaining, "NextScoringWindowID", next_group[0])
        _set(remaining, "NextScoringGameIDs", list(scoring["GameIDs"]))
        _set(remaining, "NextScoringPrimaryGameID", scoring["PrimaryGameID"])
        _set(remaining, "NextScoringWindowGameCount", len(scoring["GameIDs"]))
        _set(remaining, "NextScoringLockedActiveStarterCount", 0)
        _set(remaining, "NextScoringUnlockedStarterCount", sum(1 for p in scoring["PrimaryPaths"] if p["PathType"] == "unlocked-starter"))
        _set(
            remaining,
            "NextScoringOptionCount",
            sum(1 for p in next_group[1] if p["GameID"] == scoring["PrimaryGameID"] and p["PathType"] == "bench-candidate"),
        )
    return context


# ---------------------------------------------------------------------------------------------------------------------
# Score, weekly watch and market context


def add_score_context(context: dict[str, Any], schedule: list[dict[str, Any]]) -> dict[str, Any]:
    by_game: dict[str, dict[str, Any]] = {}
    for row in schedule:
        if row is None:
            continue
        game_id = _s(value_of(row, "gameID", "GameID"))
        if game_id.strip() == "":
            continue
        if game_id in by_game:
            raise MatchupContextError(f"Duplicate Schedule score identity for FantasyGameContext GameID '{game_id}'.")
        by_game[game_id] = row
    for game in context["Games"]:
        away = home = None
        if FINAL_STATUS.match(_s(game["Status"])) and game["GameID"] in by_game:
            row = by_game[game["GameID"]]
            candidate_away = _opt_float(value_of(row, "awayPts", "AwayScore"))
            candidate_home = _opt_float(value_of(row, "homePts", "HomeScore"))
            if candidate_away is not None and candidate_home is not None:
                away, home = candidate_away, candidate_home
        game["AwayScore"] = away
        game["HomeScore"] = home
    context["SchemaVersion"] = max(3, int(context["SchemaVersion"]))
    return context


def _starter_team_ids(game: dict[str, Any]) -> list[str]:
    return sorted({str(t["FantasyTeamID"]) for t in game["FantasyTeams"] if int(t["StarterCount"]) > 0})


def _starter_matchup_ids(game: dict[str, Any]) -> list[str]:
    return sorted({str(t["FantasyMatchupID"]) for t in game["FantasyTeams"] if int(t["StarterCount"]) > 0 and _s(t["FantasyMatchupID"]).strip() != ""})


def add_weekly_watch_context(context: dict[str, Any]) -> dict[str, Any]:
    candidates = [g for g in context["Games"] if int(g["Relevance"]["StarterCount"]) > 0]
    for game in context["Games"]:
        if game.get("RemainingRelevance") is not None:
            game["RemainingRelevance"]["MustWatchRank"] = None
    ranked = sorted(
        candidates,
        key=lambda g: (-len(_starter_team_ids(g)), -int(g["Relevance"]["StarterCount"]), -len(_starter_matchup_ids(g)), _s(g["StartsAtUtc"]), _s(g["GameID"])),
    )

    def remaining_value(remaining: Any, name: str) -> int:
        return 0 if remaining is None or name not in remaining else int(remaining[name])

    must_watch = []
    for index, game in enumerate(ranked):
        remaining = game.get("RemainingRelevance")
        team_ids = _starter_team_ids(game)
        if remaining is not None:
            remaining["MustWatchRank"] = index + 1
        must_watch.append(
            {
                "Rank": index + 1,
                "GameID": _s(game["GameID"]),
                "DecisionWindowID": _s(game["DecisionWindowID"]),
                "StartsAtUtc": _s(game["StartsAtUtc"]),
                "CommittedFinalWindowMatchupCount": remaining_value(remaining, "CommittedFinalWindowMatchupCount"),
                "LockedActiveStarterCount": remaining_value(remaining, "LockedActiveStarterCount"),
                "DirectStarterFantasyTeamCount": len(team_ids),
                "DirectStarterFantasyTeamIDs": team_ids,
                "UnlockedStarterCount": remaining_value(remaining, "UnlockedStarterCount"),
                "TwoSidedFantasyMatchupCount": remaining_value(remaining, "TwoSidedFantasyMatchupCount"),
                "FantasyMatchupCount": len(_starter_matchup_ids(game)),
                "FinalWindowFantasyMatchupCount": remaining_value(remaining, "FinalWindowFantasyMatchupCount"),
                "EligibleBenchCandidateCount": remaining_value(remaining, "EligibleBenchCandidateCount"),
            }
        )
    context["MustWatchGames"] = must_watch
    context["SchemaVersion"] = max(4, int(context["SchemaVersion"]))
    return context


def add_market_context(
    context: dict[str, Any], schedule: list[dict[str, Any]], season: str, week: int, nfl_game_derived: Any
) -> dict[str, Any]:
    """Markets are optional display data from the NFL Game product; the App GameID bridges through CanonicalGameID."""
    by_game: dict[str, dict[str, Any]] = {}
    for row in schedule:
        if row is None:
            continue
        app_id = _s(value_of(row, "gameID", "GameID"))
        if app_id.strip() == "":
            continue
        if app_id in by_game:
            raise MatchupContextError(f"Duplicate App schedule GameID '{app_id}' in NFL market projection.")
        by_game[app_id] = row
    derived_by_game: dict[str, Any] = {}
    if nfl_game_derived is not None:
        if int(nfl_game_derived.get("SchemaVersion", 0)) != 1 or _s(nfl_game_derived.get("Season")) != season or nfl_game_derived.get("Games") is None:
            raise MatchupContextError(f"NFL Game Derived schema/season mismatch for FantasyGameContext {season} Week {week}.")
        for row in nfl_game_derived["Games"]:
            canonical_id = _s(row.get("GameID"))
            if canonical_id.strip() == "" or canonical_id in derived_by_game:
                raise MatchupContextError(f"Missing or duplicate canonical GameID '{canonical_id}' in NFL Game Derived.")
            derived_by_game[canonical_id] = row
    for game in context["Games"]:
        market = None
        row = by_game.get(game["GameID"])
        if row is not None:
            canonical_id = _s(value_of(row, "CanonicalGameID"))
            derived = derived_by_game.get(canonical_id) if canonical_id.strip() != "" else None
            if derived is not None:
                if int(derived.get("Week", 0)) != week or _s(derived.get("AwayTeam")) != _s(game["AwayTeamID"]) or _s(derived.get("HomeTeam")) != _s(game["HomeTeamID"]):
                    raise MatchupContextError(f"NFL market identity mismatch for '{game['GameID']}' -> '{canonical_id}'.")
                raw = derived.get("Market")
                if raw is not None:
                    values: dict[str, float | None] = {}
                    for field in ("SpreadLine", "TotalLine", "ImpliedAwayPoints", "ImpliedHomePoints"):
                        value = raw.get(field)
                        if value is None:
                            values[field] = None
                            continue
                        number = _opt_float(value)
                        if number is None or number != number or number in (float("inf"), float("-inf")):
                            raise MatchupContextError(f"Invalid NFL market {field} for '{canonical_id}'.")
                        values[field] = number
                    market = values
        game["Market"] = market
    context["SchemaVersion"] = max(6, int(context["SchemaVersion"]))
    return context


# ---------------------------------------------------------------------------------------------------------------------
# Public builder and resolver


def build_fantasy_game_context(
    league_id: Any,
    season: str,
    week: int,
    decision_facts: Any,
    matchups: list[dict[str, Any]],
    schedule: list[dict[str, Any]],
    week_is_final: bool,
    team_key: Callable[[Any], str | None],
    parse_instant: Callable[[str], Any],
    nfl_game_derived: Any = _UNSET,
) -> dict[str, Any]:
    """The FantasyGameContext of one week; ``nfl_game_derived`` omitted keeps the historical schema without market values."""
    context = _base_context(league_id, season, week, decision_facts, matchups, schedule, week_is_final, team_key)
    context = add_relevance_context(context, decision_facts, parse_instant)
    context = add_preview_context(context, decision_facts, parse_instant)
    context = add_score_context(context, schedule)
    context = add_weekly_watch_context(context)
    if nfl_game_derived is not _UNSET:
        context = add_market_context(context, schedule, season, week, nfl_game_derived)
    return context


# ---------------------------------------------------------------------------------------------------------------------
# History of completed seasons (New-HistoricalFantasyGameContextSeason of FantasyGameContextCore.ps1)

HISTORY_GAME_TYPES = {"REG", "WC", "DIV", "CON", "SB"}


def canonical_matchup_facts(season: str, week: int, rows: list[Any]) -> list[dict[str, Any]]:
    """Paired facts of canonical league matchup rows (ConvertTo-FgcCanonicalMatchupFacts)."""
    normalized: list[dict[str, Any]] = []
    for row in rows:
        provider_id = _mapping_text(row, "ProviderMatchupID", "MatchupID")
        team_id = _mapping_text(row, "ProviderRosterID", "RosterID")
        if provider_id is None or team_id is None:
            continue
        player_points = _canonical_points(value_of(row, "PlayerPoints"))
        starter_points = _canonical_points(value_of(row, "StarterPoints"))
        starter_ids = sorted({pid for pid in (_canonical_player_id(p) for p in (value_of(row, "Starters") or [])) if pid})
        players: dict[str, dict[str, Any]] = {}
        for ref in value_of(row, "Players") or []:
            player_id = _canonical_player_id(ref)
            if not player_id:
                continue
            is_starter = player_id in starter_ids
            has_points = player_id in player_points
            points = player_points[player_id] if has_points else None
            if is_starter and player_id in starter_points:
                has_points, points = True, starter_points[player_id]
            canonical = value_of(ref, "CanonicalPlayerID") if isinstance(ref, dict) else None
            canonical = None if _blank(canonical) else str(canonical).strip()
            players.setdefault(player_id, _player_fact(player_id, canonical, is_starter, points, has_points))
        for starter_id in starter_ids:
            if starter_id not in players:
                raise MatchupContextError(f"Historical fantasy matchup Week {week} Team '{team_id}' has starter '{starter_id}' outside the rostered player set.")
        score = value_of(row, "Points")
        normalized.append(
            {
                "ProviderMatchupID": provider_id,
                "FantasyTeamID": team_id,
                "Players": [players[key] for key in sorted(players)],
                "FinalScore": 0.0 if score is None else float(score),
                "HasCustomPoints": value_of(row, "CustomPoints") is not None,
            }
        )
    return paired_matchup_facts(season, week, normalized)


def _mapping_text(row: Any, *names: str) -> str | None:
    for mapping in value_of(row, "ProviderMappings") or []:
        if _s(value_of(mapping, "Provider")) != "Sleeper":
            continue
        value = value_of(mapping, *names)
        if value is not None and not _blank(value):
            return str(value).strip()
    return None


def _canonical_player_id(ref: Any) -> str | None:
    if ref is None:
        return None
    if not isinstance(ref, dict):
        return str(ref).strip() or None
    direct = value_of(ref, "PlayerID", "ID", "SleeperID")
    if direct is not None and not _blank(direct):
        return str(direct).strip()
    return _mapping_text(ref, "ProviderPlayerID", "PlayerID")


def _canonical_points(entries: Any) -> dict[str, float]:
    result: dict[str, float] = {}
    for entry in entries or []:
        if entry is None:
            continue
        player_id = _canonical_player_id(value_of(entry, "Player"))
        points = value_of(entry, "Points")
        if player_id and points is not None:
            result[player_id] = float(points)
    return result


def _kickoff_from_epoch(game: Any) -> str | None:
    from datetime import datetime, timezone

    epoch = value_of(game, "gameTime_epoch", "GameTimeEpoch")
    if epoch is not None and str(epoch).strip() != "":
        try:
            return datetime.fromtimestamp(int(float(epoch)), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, OverflowError, OSError):
            pass
    return None


def historical_decision_facts(
    week: int,
    schedule: list[dict[str, Any]],
    matchups: list[dict[str, Any]],
    assignments: dict[str, list[str]] | None,
    team_key: Callable[[Any], str | None],
) -> dict[str, Any]:
    """Decision Windows and player lock facts of a completed week from canonical weekly membership (New-FgcHistoricalDecisionFacts)."""
    label = f"Week {week}"
    games: list[dict[str, Any]] = []
    for game in schedule:
        week_text = _s(value_of(game, "gameWeek", "Week"))
        if week_text != label and week_text != str(week):
            continue
        game_id = _s(value_of(game, "gameID", "GameID"))
        starts = _kickoff_from_epoch(game)
        if game_id.strip() == "" or not starts:
            continue
        games.append(
            {
                "GameID": game_id,
                "StartsAtUtc": starts,
                "AwayTeamID": _s(value_of(game, "teamIDAway", "AwayTeamID")),
                "AwayTeamAbbr": value_of(game, "teamAbvAway", "AwayTeamAbbr"),
                "HomeTeamID": _s(value_of(game, "teamIDHome", "HomeTeamID")),
                "HomeTeamAbbr": value_of(game, "teamAbvHome", "HomeTeamAbbr"),
            }
        )
    assignments = assignments or {}
    locks: list[dict[str, Any]] = []
    for matchup in matchups:
        for team in matchup["Teams"]:
            for player in team["Players"]:
                candidates: list[tuple[dict[str, Any], str]] = []
                canonical = _s(player.get("CanonicalPlayerID"))
                if canonical.strip() != "" and canonical in assignments:
                    for abbr in assignments[canonical]:
                        for game in games:
                            keys = {team_key(game["AwayTeamID"]), team_key(game["HomeTeamID"])}
                            if team_key(abbr) in keys or abbr in (_s(game["AwayTeamAbbr"]), _s(game["HomeTeamAbbr"])):
                                candidates.append((game, abbr))
                game_ids = sorted({g["GameID"] for g, _ in candidates})
                if len(game_ids) == 1:
                    game = candidates[0][0]
                    team_ids = sorted({abbr for _, abbr in candidates})
                    locks.append(
                        {
                            "FantasyTeamID": team["FantasyTeamID"], "PlayerID": player["PlayerID"],
                            "NFLTeamID": team_ids[0] if len(team_ids) == 1 else None, "Kind": "scheduled", "GameID": game["GameID"],
                            "DecisionWindowID": game["StartsAtUtc"], "StartsAtUtc": game["StartsAtUtc"], "IsStarter": player["IsStarter"],
                        }
                    )
                else:
                    locks.append(
                        {
                            "FantasyTeamID": team["FantasyTeamID"], "PlayerID": player["PlayerID"], "NFLTeamID": None, "Kind": "unknown",
                            "GameID": None, "DecisionWindowID": None, "StartsAtUtc": None, "IsStarter": player["IsStarter"],
                        }
                    )
    windows: list[dict[str, Any]] = []
    for starts in sorted({g["StartsAtUtc"] for g in games}):
        windows.append(
            {
                "DecisionWindowID": starts,
                "StartsAtUtc": starts,
                "Games": sorted((g for g in games if g["StartsAtUtc"] == starts), key=lambda g: g["GameID"]),
            }
        )
    return {"DecisionWindows": windows, "PlayerLockFacts": locks}


def resolve_historical_season(repo_root: Path, league_id: str, season: int) -> dict[str, Any]:
    """The FantasyGameContext history document of a completed season (SchemaVersion 1, ScoringState final).

    Raises MatchupContextError when the canonical evidence (league source, matchups, schedule, weekly rosters) is incomplete.
    """
    from nfl_source_data_lib.teams import NflTeamRegistry
    from schedule_archive import ScheduleArchiveError, build_schedule

    from .decision_windows import make_team_key

    season_dir = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season)
    league_file = season_dir / "league.json"
    matchup_dir = season_dir / "matchups"
    roster_dir = repo_root / DATA_SOURCE_ROOT / "nfl" / "weekly-rosters" / str(season)
    if not league_file.is_file() or not matchup_dir.is_dir() or not roster_dir.is_dir():
        raise MatchupContextError(f"Historical FantasyGameContext {season} requires canonical league matchups, the canonical NFL schedule and canonical weekly NFL roster evidence.")
    league = _read(league_file, "Canonical league source")
    last_week = to_int(value_of(value_of(league, "WeekStructure"), "FinalLeagueWeek"))
    if last_week <= 0:
        last_week = to_int(value_of(value_of(league, "Settings"), "last_scored_leg"))
    if last_week <= 0:
        raise MatchupContextError(f"Historical FantasyGameContext {season} cannot resolve the final fantasy week.")
    try:
        schedule = build_schedule(repo_root, season, HISTORY_GAME_TYPES)
    except ScheduleArchiveError as exc:
        raise MatchupContextError(str(exc)) from exc
    team_key = make_team_key(NflTeamRegistry.load(repo_root))
    weeks: list[dict[str, Any]] = []
    for week in range(1, last_week + 1):
        matchup_file = matchup_dir / f"week-{week}.json"
        if not matchup_file.is_file():
            continue
        payload = _read(matchup_file, f"Canonical matchups week {week}")
        facts = canonical_matchup_facts(str(season), week, payload if isinstance(payload, list) else [payload])
        if not facts:
            continue
        from .matchup_context import weekly_assignment_map

        decision = historical_decision_facts(week, schedule, facts, weekly_assignment_map(repo_root, season, week), team_key)
        weeks.append(build_fantasy_game_context(league_id, str(season), week, decision, facts, schedule, True, team_key, parse_instant_text))
    return {"SchemaVersion": 1, "LeagueID": league_id, "Season": str(season), "ScoringState": "final", "Weeks": weeks}


def resolve_current_context(repo_root: Path, league_id: str, season: int, at_utc: Any) -> dict[str, Any] | None:
    """The FantasyGameContext of the current lineup week at ``at_utc`` or None when no current matchup week is loadable.

    None keeps the previously published file (PowerShell kept it on a failed matchup load or a lineup/matchup week mismatch).
    """
    from nfl_source_data_lib.teams import NflTeamRegistry
    from schedule_archive import build_schedule

    from .decision_windows import DecisionWindowsError, make_team_key, resolve as resolve_decision_windows
    from .league_lifecycle import LifecycleError, resolve_lifecycle

    if at_utc.tzinfo is None:
        raise MatchupContextError("AtUtc must be timezone-aware")
    try:
        decision_facts = resolve_decision_windows(repo_root, league_id, season, at_utc)
        lifecycle = resolve_lifecycle(repo_root, league_id, season, at_utc)
    except (DecisionWindowsError, LifecycleError) as exc:
        raise MatchupContextError(str(exc)) from exc
    league = _read(repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season) / "league.json", "Canonical league source")
    week = matchup_load_week(decision_facts, int(lifecycle["LastLeagueWeek"]), _text(value_of(league, "Status")) == "complete")
    if week <= 0 or to_int(value_of(decision_facts, "LineupWeek")) != week:
        return None
    try:
        rows = current_matchup_rows(repo_root, league_id, season, week)
    except MatchupContextError as exc:
        LOG.warning("Canonical current matchup load for Week %s failed: %s", week, exc)
        return None
    facts = current_matchup_facts(str(season), week, rows)
    derived_path = repo_root / DATA_DERIVED_ROOT / "nfl-games" / f"{season}.json"
    derived = _read(derived_path, "NFL Game Derived") if derived_path.is_file() else None
    schedule = build_schedule(repo_root, season, {"REG"})
    return build_fantasy_game_context(
        value_of(decision_facts, "LeagueID"),
        str(season),
        week,
        decision_facts,
        facts,
        schedule,
        int(lifecycle["FinalScoredWeek"]) >= week,
        make_team_key(NflTeamRegistry.load(repo_root)),
        parse_instant_text,
        derived,
    )


__all__ = [
    "add_market_context", "add_preview_context", "add_relevance_context", "add_score_context", "add_weekly_watch_context",
    "build_fantasy_game_context", "current_matchup_facts", "outcome_state", "paired_matchup_facts", "point_map",
    "resolve_current_context", "resolve_historical_season", "canonical_matchup_facts", "historical_decision_facts",
]
