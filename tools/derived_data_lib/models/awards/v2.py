"""awards-v2: Overperformer and Brick Wall from the season-statistics product (Issue #506, ADR-082).

Everything except the two changed awards is exactly awards-v1 (same awards, order, display and score annotations). The two
changed awards read the figures of ``season-stats-v1`` (the persisted product ``data-derived/season-statistics``), so they
use the same formulas as the season statistics and no second copy exists:

* Overperformer: the highest mean of the own points above the own pregame projection (``ProjectionDelta``). A team without a
  projected game is not eligible. An exact tie goes to the first team in table order.
* Brick Wall: the most wins against opponents that scored above their own season average in that game
  (``AboveAverageOpponentWins``). An exact tie goes to the higher quota (wins over such opponents), then to the first team in
  table order. A team without such an opponent is not eligible.

Missing evidence is not guessed: without the product, or without an eligible team, the award is not given. Immutable after its
first productive use; any other change is ``awards-v3``.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Any, Sequence

from .._common import ps_text
from . import v1

MODEL_ID = "awards-v2"
KIND = "awards"
#: The pure assembly passes the season statistics of the season to ``compute`` for models with this marker.
NEEDS_SEASON_STATISTICS = True

PARAMS = MappingProxyType({**v1.PARAMS, "Overperformer": "mean-points-above-pregame-projection",
                           "BrickWall": "wins-against-above-average-opponents"})


def _overperformer(rows: Sequence[dict[str, Any]], stats: dict[int, dict[str, Any]]) -> dict[str, Any] | None:
    best: tuple[dict[str, Any], dict[str, Any]] | None = None
    for row in rows:
        team = stats.get(row["TeamID"])
        if not team or not team.get("ProjectionGames") or team.get("ProjectionDelta") is None:
            continue
        if best is None or team["ProjectionDelta"] > best[1]["ProjectionDelta"]:
            best = (row, team)
    if best is None:
        return None
    row, team = best
    delta = team["ProjectionDelta"]
    return v1._award("Overperformer", "RegularSeason", "1F680",
                     f"Points vs. Projection per Game: {delta:+.1f} | Wins: {ps_text(row['Wins'])}", row)


def _brick_wall(rows: Sequence[dict[str, Any]], stats: dict[int, dict[str, Any]]) -> dict[str, Any] | None:
    best: tuple[dict[str, Any], dict[str, Any]] | None = None
    for row in rows:
        team = stats.get(row["TeamID"])
        if not team or not team.get("AboveAverageOpponents"):
            continue
        quota = team["AboveAverageOpponentWins"] / team["AboveAverageOpponents"]
        if best is None:
            best = (row, team)
            continue
        other = best[1]
        other_quota = other["AboveAverageOpponentWins"] / other["AboveAverageOpponents"]
        if (team["AboveAverageOpponentWins"], quota) > (other["AboveAverageOpponentWins"], other_quota):
            best = (row, team)
    if best is None:
        return None
    row, team = best
    return v1._award("Brick Wall", "RegularSeason", "1F9F1",
                     f"Wins vs. Above-Average Opponents: {team['AboveAverageOpponentWins']} of {team['AboveAverageOpponents']} | "
                     f"Wins: {ps_text(row['Wins'])}", row)


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
