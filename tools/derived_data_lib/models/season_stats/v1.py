"""season-stats-v1: season statistics of one league season from the weekly regular-season games (Issue #506).

Pure function of explicit inputs (no file, clock or league configuration). ``compute`` takes the regular-season games of the scored
weeks in an uninterrupted run and returns, per team, every figure of the product plus the weekly progression:

* All-Play and ExpectedWins: per week ``(teams with fewer points + 0.5 * equal points) / (N - 1)``; the sum is ExpectedWins.
* Luck (RecordDelta) = (Wins + 0.5 * Ties) - ExpectedWins.
* RelativeScoringStrength = team points per game / league points per team-game at the same cut-off.
* StrengthOfSchedule = mean RelativeScoringStrength of the opponents per game (repeated opponents count repeatedly). Stored, but the
  App does not display it (six teams, self-exclusion makes the spread tiny).
* PointsAgainstBurden = own points against per game / league points per team-game.
* OpponentTiming per game = opponent points - opponent season average at the cut-off; the season value is the mean.
* ProjectionDelta per game = points - pregame projection (team-range-v1, PlayerWeekFantasy); a game without projection is ``None``.
* Brick-Wall basis: games against an opponent above its own season average in that game, and the wins among them.
* Upsets: wins with a pregame win chance below ``UNDERDOG_THRESHOLD`` (underdog wins), of them below ``UPSET_THRESHOLD`` (upsets); losses as
  favorite (chance above the underdog boundary) and the losses against an upset. A game without a chance counts nowhere (unknown).
* BiggestUpset: the win with the lowest pregame chance when it is below ``UPSET_THRESHOLD``, else ``None``.

Missing evidence is ``None``, never a guess. Immutable after its first productive use; any change is ``season-stats-v2``.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Any, Sequence

MODEL_ID = "season-stats-v1"
KIND = "season-stats"

UNDERDOG_THRESHOLD = 0.5
UPSET_THRESHOLD = 0.35
DIGITS = 4

PARAMS = MappingProxyType({
    "AllPlay": "less-plus-half-equal-over-others",
    "UnderdogThreshold": UNDERDOG_THRESHOLD,
    "UpsetThreshold": UPSET_THRESHOLD,
    "Digits": DIGITS,
})


def _r(value: float | None) -> float | None:
    return None if value is None else round(value, DIGITS) + 0.0  # + 0.0 turns -0.0 into 0.0


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _result(own: float, other: float) -> str:
    return "W" if own > other else ("L" if own < other else "T")


def _flat(weeks: Sequence[dict[str, Any]], upto: int) -> list[dict[str, Any]]:
    """One row per team and game up to week ``upto``: Week, TeamID, Opponent, Points, OpponentPoints, projection and chance."""
    rows: list[dict[str, Any]] = []
    for week in weeks:
        if week["Week"] > upto:
            continue
        for game in week["Games"]:
            a, b = game["Teams"]
            chance = game.get("WinProbability")  # unrounded chance of Teams[0] or None
            for own, other, own_chance in ((a, b, chance), (b, a, None if chance is None else 1.0 - chance)):
                rows.append({
                    "Week": week["Week"], "TeamID": own["TeamID"], "OpponentID": other["TeamID"],
                    "Points": own["Points"], "OpponentPoints": other["Points"],
                    "Projection": own.get("PregameProjection"), "Chance": own_chance,
                    "BestBall": own.get("ProjectedBestBallPoints"), "EfficiencyActual": own.get("LineupEfficiencyActual"),
                    "BestBallExcluded": own.get("BestBallExcludedPlayers"),
                })
    return rows


def _efficiency_projected(game: dict[str, Any]) -> float | None:
    """Pregame starter projection as a percentage of the pregame best-ball projection (None when either is unknown)."""
    projection, best_ball = game.get("Projection"), game.get("BestBall")
    if projection is None or best_ball is None or best_ball <= 0:
        return None
    return projection * 100.0 / best_ball


def _stand(team_ids: Sequence[Any], weeks: Sequence[dict[str, Any]], upto: int) -> dict[Any, dict[str, Any]]:
    rows = _flat(weeks, upto)
    by_team: dict[Any, list[dict[str, Any]]] = {team: [] for team in team_ids}
    for row in rows:
        by_team[row["TeamID"]].append(row)
    total_games = len(rows)
    league_ppg = sum(r["Points"] for r in rows) / total_games if total_games else None
    average = {t: (sum(r["Points"] for r in g) / len(g) if g else None) for t, g in by_team.items()}
    strength = {t: (average[t] / league_ppg if average[t] is not None and league_ppg else None) for t in team_ids}

    expected = {t: 0.0 for t in team_ids}
    all_play = {t: [0, 0, 0] for t in team_ids}
    shares: dict[tuple[int, Any], float | None] = {}
    for week in weeks:
        if week["Week"] > upto:
            continue
        scores = {team["TeamID"]: team["Points"] for game in week["Games"] for team in game["Teams"]}
        others = len(scores) - 1
        for team, points in scores.items():
            less = sum(1 for o, p in scores.items() if o != team and p < points)
            equal = sum(1 for o, p in scores.items() if o != team and p == points)
            share = (less + 0.5 * equal) / others if others > 0 else None
            shares[(week["Week"], team)] = share
            if share is not None:
                expected[team] += share
            all_play[team][0] += less
            all_play[team][1] += others - less - equal
            all_play[team][2] += equal
    result: dict[Any, dict[str, Any]] = {}
    for team in team_ids:
        games = by_team[team]
        wins = sum(1 for g in games if g["Points"] > g["OpponentPoints"])
        ties = sum(1 for g in games if g["Points"] == g["OpponentPoints"])
        count = len(games)
        pa = sum(g["OpponentPoints"] for g in games)
        timing: list[dict[str, Any]] = []
        for g in games:
            opp_avg = average[g["OpponentID"]]
            timing.append({**g, "Timing": None if opp_avg is None else g["OpponentPoints"] - opp_avg, "OpponentAverage": opp_avg})
        opp_strength = [strength[g["OpponentID"]] for g in games if strength[g["OpponentID"]] is not None]
        deltas = [g["Points"] - g["Projection"] for g in games if g["Projection"] is not None]
        above = [g for g in timing if g["Timing"] is not None and g["Timing"] > 0]
        known = [g for g in games if g["Chance"] is not None]
        best_balls = [g["BestBall"] for g in games if g["BestBall"] is not None]
        eff_projected = [e for e in (_efficiency_projected(g) for g in games) if e is not None]
        eff_actual = [g["EfficiencyActual"] for g in games if g["EfficiencyActual"] is not None]
        mean_best_ball, mean_eff_projected = _mean(best_balls), _mean(eff_projected)
        result[team] = {
            "BestBallGames": len(best_balls),
            "ProjectedBestBallPoints": mean_best_ball,
            "LineupEfficiencyProjected": mean_eff_projected,
            "LineupEfficiencyActual": _mean(eff_actual),
            "ProjectedBestBallStrength": None if mean_best_ball is None or mean_eff_projected is None else mean_best_ball * mean_eff_projected / 100.0,
            "Games": games, "Timing": timing, "Wins": wins, "Ties": ties, "Losses": count - wins - ties,
            "Points": sum(g["Points"] for g in games), "PointsAgainst": pa,
            "ExpectedWins": expected[team] if count else None,
            "AllPlay": all_play[team], "Shares": shares,
            "RelativeScoringStrength": strength[team],
            "StrengthOfSchedule": _mean(opp_strength),
            "PointsAgainstBurden": (pa / count) / league_ppg if count and league_ppg else None,
            "OpponentTiming": _mean([g["Timing"] for g in timing if g["Timing"] is not None]),
            "ProjectionDelta": _mean(deltas), "ProjectionGames": len(deltas),
            "AboveAverageOpponents": len(above), "AboveAverageOpponentWins": sum(1 for g in above if g["Points"] > g["OpponentPoints"]),
            "KnownChanceGames": len(known),
            "UnderdogWins": sum(1 for g in known if g["Points"] > g["OpponentPoints"] and g["Chance"] < UNDERDOG_THRESHOLD),
            "UpsetWins": sum(1 for g in known if g["Points"] > g["OpponentPoints"] and g["Chance"] < UPSET_THRESHOLD),
            "FavoriteLosses": sum(1 for g in known if g["Points"] < g["OpponentPoints"] and g["Chance"] > UNDERDOG_THRESHOLD),
            "UpsetLosses": sum(1 for g in known if g["Points"] < g["OpponentPoints"] and 1.0 - g["Chance"] < UPSET_THRESHOLD),
        }
    return result


def compute(team_ids: Sequence[Any], weeks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Per-team statistics, weekly progression and the biggest upset.

    ``weeks``: ``[{"Week": int, "Games": [{"Teams": [{"TeamID", "Points", "PregameProjection"}, {...}], "WinProbability"}]}]`` in
    ascending week order; ``WinProbability`` is the unrounded pregame chance of the first team or ``None``.
    """
    weeks = sorted(weeks, key=lambda w: w["Week"])
    final_week = weeks[-1]["Week"] if weeks else 0
    progression = []
    for week in weeks:
        stand = _stand(team_ids, weeks, week["Week"])
        progression.append({"Week": week["Week"], "Teams": [
            {
                "TeamID": team,
                "ExpectedWins": _r(stand[team]["ExpectedWins"]),
                "Luck": _r(stand[team]["Wins"] + 0.5 * stand[team]["Ties"] - stand[team]["ExpectedWins"]) if stand[team]["ExpectedWins"] is not None else None,
                "RelativeScoringStrength": _r(stand[team]["RelativeScoringStrength"]),
                "StrengthOfSchedule": _r(stand[team]["StrengthOfSchedule"]),
                "ProjectedBestBallStrength": _r(stand[team]["ProjectedBestBallStrength"]),
            }
            for team in team_ids
        ]})
    final = _stand(team_ids, weeks, final_week)
    teams = []
    for team in team_ids:
        s = final[team]
        games = []
        for g in s["Timing"]:
            chance = g["Chance"]
            games.append({
                "Week": g["Week"], "OpponentID": g["OpponentID"], "Points": _r(g["Points"]), "OpponentPoints": _r(g["OpponentPoints"]),
                "Result": _result(g["Points"], g["OpponentPoints"]),
                "AllPlayShare": _r(s["Shares"].get((g["Week"], team))),
                "OpponentTiming": _r(g["Timing"]),
                "PregameProjection": _r(g["Projection"]),
                "ProjectionDelta": None if g["Projection"] is None else _r(g["Points"] - g["Projection"]),
                "PregameWinProbability": _r(chance),
                "ProjectedStarterPoints": _r(g["Projection"]),
                "ProjectedBestBallPoints": _r(g["BestBall"]),
                "LineupEfficiencyProjected": _r(_efficiency_projected(g)),
                "LineupEfficiencyActual": _r(g["EfficiencyActual"]),
                "BestBallExcludedPlayers": g["BestBallExcluded"] if g["BestBall"] is not None else None,
            })
        wins_ties = s["Wins"] + 0.5 * s["Ties"]
        teams.append({
            "TeamID": team,
            "Games": len(s["Games"]), "Wins": s["Wins"], "Losses": s["Losses"], "Ties": s["Ties"],
            "Points": _r(s["Points"]), "PointsAgainst": _r(s["PointsAgainst"]),
            "ExpectedWins": _r(s["ExpectedWins"]),
            "AllPlay": {"Wins": s["AllPlay"][0], "Losses": s["AllPlay"][1], "Ties": s["AllPlay"][2]},
            "Luck": None if s["ExpectedWins"] is None else _r(wins_ties - s["ExpectedWins"]),
            "RelativeScoringStrength": _r(s["RelativeScoringStrength"]),
            "StrengthOfSchedule": _r(s["StrengthOfSchedule"]),
            "PointsAgainstBurden": _r(s["PointsAgainstBurden"]),
            "OpponentTiming": _r(s["OpponentTiming"]),
            "ProjectionDelta": _r(s["ProjectionDelta"]), "ProjectionGames": s["ProjectionGames"],
            "AboveAverageOpponents": s["AboveAverageOpponents"], "AboveAverageOpponentWins": s["AboveAverageOpponentWins"],
            "KnownChanceGames": s["KnownChanceGames"],
            "BestBallGames": s["BestBallGames"],
            "ProjectedBestBallPoints": _r(s["ProjectedBestBallPoints"]),
            "LineupEfficiencyProjected": _r(s["LineupEfficiencyProjected"]),
            "LineupEfficiencyActual": _r(s["LineupEfficiencyActual"]),
            "ProjectedBestBallStrength": _r(s["ProjectedBestBallStrength"]),
            "UnderdogWins": s["UnderdogWins"], "UpsetWins": s["UpsetWins"],
            "FavoriteLosses": s["FavoriteLosses"], "UpsetLosses": s["UpsetLosses"],
            "GameLog": games,
        })
    return {"Teams": teams, "Weeks": progression, "BiggestUpset": biggest_upset(weeks)}


def biggest_upset(weeks: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    """Win with the lowest pregame chance below UPSET_THRESHOLD; ties by earlier week, then lower winner TeamID text."""
    best: tuple[Any, dict[str, Any]] | None = None
    for week in sorted(weeks, key=lambda w: w["Week"]):
        for game in week["Games"]:
            chance = game.get("WinProbability")
            a, b = game["Teams"]
            if chance is None or a["Points"] == b["Points"]:
                continue
            winner, loser, winner_chance = (a, b, chance) if a["Points"] > b["Points"] else (b, a, 1.0 - chance)
            if winner_chance >= UPSET_THRESHOLD:
                continue
            key = (winner_chance, week["Week"], str(winner["TeamID"]))
            if best is None or key < best[0]:
                best = (key, {
                    "Week": week["Week"], "WinnerTeamID": winner["TeamID"], "LoserTeamID": loser["TeamID"],
                    "WinnerPoints": _r(winner["Points"]), "LoserPoints": _r(loser["Points"]),
                    "WinnerPregameWinProbability": _r(winner_chance),
                })
    return None if best is None else best[1]
