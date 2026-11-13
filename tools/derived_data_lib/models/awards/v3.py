"""awards-v3: league-adjusted Overperformer and richer Overperformer/Brick Wall display (Issue #1460).

Everything except the two changed awards is exactly awards-v2 (and so awards-v1): same awards, order, display and score
annotations. Both changed awards read the persisted ``season-statistics`` product (``season-stats-v1``) like awards-v2:

* Overperformer: the highest mean of the own points above the own pregame projection, minus the league mean of the same
  difference over every projected game of the season. Subtracting the league mean removes a projection bias that hits every
  team alike (in 2025 the whole league stayed below its projections), so the winner's value is never negative. The order of
  the teams is the same as in awards-v2. An exact tie goes to the first team in table order. A team without a projected
  game is not eligible.
* Brick Wall: unchanged ranking of awards-v2 (most wins against opponents that scored above their own season average in
  that game; tie: higher quota, then table order). The display adds the points those beaten opponents scored above their own
  average (the surplus the team withstood).

Display (English, three parts each):
``vs. Projection: +8.7 per Game (League-Adjusted) | Beat Projection: 8 of 13 | Record: 7-7``
``Beat Above-Average Opponents: 5 of 10 | Opponent Surplus Withstood: +31.4 Pts | Record: 9-5``

Missing evidence is not guessed: without the product, or without an eligible team, the award is not given. Immutable after its
first productive use; any other change is ``awards-v4``.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Any, Sequence

from . import v1, v2

MODEL_ID = "awards-v3"
KIND = "awards"
#: The pure assembly passes the season statistics of the season to ``compute`` for models with this marker.
NEEDS_SEASON_STATISTICS = True

PARAMS = MappingProxyType({**v1.PARAMS, "Overperformer": "mean-points-above-pregame-projection-minus-league-mean",
                           "BrickWall": "wins-against-above-average-opponents"})


def _record(row: dict[str, Any]) -> str:
    record = f"{row['Wins']}-{row['Losses']}"
    return f"{record}-{row['Ties']}" if row.get("Ties") else record


def _projected_games(team: dict[str, Any]) -> list[dict[str, Any]]:
    return [g for g in team.get("GameLog") or [] if g.get("ProjectionDelta") is not None]


def _league_mean_delta(teams: Sequence[dict[str, Any]]) -> float | None:
    deltas = [g["ProjectionDelta"] for team in teams for g in _projected_games(team)]
    return sum(deltas) / len(deltas) if deltas else None


def _overperformer(rows: Sequence[dict[str, Any]], stats: dict[int, dict[str, Any]]) -> dict[str, Any] | None:
    league_mean = _league_mean_delta(list(stats.values()))
    if league_mean is None:
        return None
    best: tuple[dict[str, Any], dict[str, Any], float] | None = None
    for row in rows:
        team = stats.get(row["TeamID"])
        if not team or not team.get("ProjectionGames") or team.get("ProjectionDelta") is None:
            continue
        adjusted = team["ProjectionDelta"] - league_mean
        if best is None or adjusted > best[2]:
            best = (row, team, adjusted)
    if best is None:
        return None
    row, team, adjusted = best
    games = _projected_games(team)
    beaten = sum(1 for g in games if g["ProjectionDelta"] > 0)
    return v1._award("Overperformer", "RegularSeason", "1F680",
                     f"vs. Projection: {adjusted + 0.0:+.1f} per Game (League-Adjusted) | "
                     f"Beat Projection: {beaten} of {len(games)} | Record: {_record(row)}", row)


def _brick_wall(rows: Sequence[dict[str, Any]], stats: dict[int, dict[str, Any]]) -> dict[str, Any] | None:
    chosen = v2._brick_wall(rows, stats)
    if chosen is None:
        return None
    row = next(r for r in rows if r["TeamID"] == chosen["TeamID"])
    team = stats[row["TeamID"]]
    surplus = sum(g["OpponentTiming"] for g in team.get("GameLog") or []
                  if g.get("Result") == "W" and g.get("OpponentTiming") is not None and g["OpponentTiming"] > 0)
    return v1._award("Brick Wall", "RegularSeason", "1F9F1",
                     f"Beat Above-Average Opponents: {team['AboveAverageOpponentWins']} of {team['AboveAverageOpponents']} | "
                     f"Opponent Surplus Withstood: {surplus + 0.0:+.1f} Pts | Record: {_record(row)}", row)


def compute(
    regular_season: Sequence[dict[str, Any]] | None,
    playoffs: Sequence[dict[str, Any]] | None,
    previous_season: dict[str, Any] | None,
    season_statistics: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    """Awards plus score annotations per TeamID; ``season_statistics`` is the season-statistics product document or None."""
    awards, annotations = v1.compute(regular_season, playoffs, previous_season)
    if not awards:
        return awards, annotations
    stats = {team["TeamID"]: team for team in (season_statistics or {}).get("Teams", [])}
    replacements = {"Overperformer": _overperformer(regular_season or [], stats), "Brick Wall": _brick_wall(regular_season or [], stats)}
    result: list[dict[str, Any]] = []
    for award in awards:
        if award["Name"] in replacements:
            replacement = replacements[award["Name"]]
            if replacement is not None:
                result.append(replacement)
        else:
            result.append(award)
    return result, annotations
