"""Pure, deterministic global NFL Game derivation (Issue #1077).

No source reads, clocks, league rules, app formats, or writes. The caller supplies
canonical season partitions from the dedicated Source owner. SpreadLine is the
AWAY-team spread; positive spread favors home.
"""
from __future__ import annotations

import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

SCHEMA_VERSION = 1
ODDS_SOURCE = "nflverse.schedule-odds"
SCHEDULE_SOURCE = "nflverse.schedules"
FINALITY_SOURCE = "nflverse.game-finality"


def _index(payload: Mapping[str, Any], *, season: int, dataset: str) -> dict[str, Mapping[str, Any]]:
    if payload.get("Season") != season or payload.get("SourceDataset") != dataset:
        raise ValueError(f"{dataset}: incompatible season or source")
    games = payload.get("Games")
    if not isinstance(games, list) or not games:
        raise ValueError(f"{dataset}: missing games")
    result: dict[str, Mapping[str, Any]] = {}
    for row in games:
        if not isinstance(row, dict):
            raise ValueError(f"{dataset}: invalid game")
        key = row.get("GameID")
        if not isinstance(key, str) or not key.startswith(f"{season}_"):
            raise ValueError(f"{dataset}: invalid GameID {key!r}")
        if key in result:
            raise ValueError(f"{dataset}: duplicate GameID {key}")
        result[key] = row
    return result


def _line(value: Any, key: str, game_id: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{game_id}: nonnumeric {key}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{game_id}: nonfinite {key}")
    return Decimal(str(value))


def _rounded(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def build_nfl_games(
    schedule: Mapping[str, Any], finality: Mapping[str, Any], odds: Mapping[str, Any]
) -> dict[str, Any]:
    """Build season-wide, consumer-neutral NFL games; fail closed on bad joins.

    Missing *lines* are valid nulls; a missing entire odds source partition is
    unavailable evidence, not a reason to silently create an incomplete product.
    """
    season = schedule.get("Season")
    if type(season) is not int or season < 1999:
        raise ValueError("Invalid season")
    scheduled = _index(schedule, season=season, dataset=SCHEDULE_SOURCE)
    completed = _index(finality, season=season, dataset=FINALITY_SOURCE)
    market = _index(odds, season=season, dataset=ODDS_SOURCE)
    if set(scheduled) != set(completed) or set(scheduled) != set(market):
        missing_final = set(scheduled) - set(completed)
        missing_market = set(scheduled) - set(market)
        extra = (set(completed) | set(market)) - set(scheduled)
        raise ValueError(
            f"GameID mismatch: missing finality={len(missing_final)} "
            f"missing odds={len(missing_market)} extra={len(extra)}"
        )
    if odds.get("SpreadConvention") != "away spread; positive favors home":
        raise ValueError("Unsupported odds spread convention")

    games = []
    for game_id, source in sorted(
        scheduled.items(), key=lambda item: (item[1]["Week"], item[1]["GameType"], item[0])
    ):
        state, quote = completed[game_id], market[game_id]
        for candidate, name in ((state, "finality"), (quote, "odds")):
            if (candidate.get("Week"), candidate.get("GameType")) != (
                source.get("Week"), source.get("GameType")
            ):
                raise ValueError(f"{game_id}: {name} week/type mismatch")
        if type(state.get("Final")) is not bool:
            raise ValueError(f"{game_id}: invalid Final")
        total = _line(quote.get("TotalLine"), "TotalLine", game_id)
        spread = _line(quote.get("SpreadLine"), "SpreadLine", game_id)
        if total is not None and total <= 0:
            raise ValueError(f"{game_id}: nonpositive TotalLine")
        if spread is not None and total is not None and abs(spread) > total:
            raise ValueError(f"{game_id}: spread exceeds total")

        away = source.get("AwayScore")
        home = source.get("HomeScore")
        for score in (away, home):
            if score is not None and (type(score) not in (int, float) or
                                      not math.isfinite(score) or score < 0):
                raise ValueError(f"{game_id}: invalid score")
        if bool(state["Final"]) and (away is None or home is None):
            raise ValueError(f"{game_id}: Final without both scores")
        if any(not isinstance(source.get(k), str) or not source.get(k)
               for k in ("AwayTeam", "HomeTeam", "GameDay")):
            raise ValueError(f"{game_id}: missing schedule identity/date")
        # Historical nflverse schedules (notably 1999) legitimately lack
        # GameTime. Preserve null; never fabricate a kickoff clock value.
        game_time = source.get("GameTime")
        if game_time is not None and (not isinstance(game_time, str) or not game_time):
            raise ValueError(f"{game_id}: invalid GameTime")

        games.append({
            "GameID": game_id,
            "GameType": source["GameType"],
            "Week": source["Week"],
            "GameDay": source["GameDay"],
            "GameTime": source["GameTime"],
            "AwayTeam": source["AwayTeam"],
            "HomeTeam": source["HomeTeam"],
            "AwayScore": away,
            "HomeScore": home,
            "Final": state["Final"],
            "Market": {
                "SourceDataset": ODDS_SOURCE,
                "SpreadLine": float(spread) if spread is not None else None,
                "TotalLine": float(total) if total is not None else None,
                "ImpliedAwayPoints": _rounded((total - spread) / 2)
                if spread is not None and total is not None else None,
                "ImpliedHomePoints": _rounded((total + spread) / 2)
                if spread is not None and total is not None else None,
            },
        })
    return {
        "SchemaVersion": SCHEMA_VERSION,
        "Season": season,
        "SourceDatasets": [SCHEDULE_SOURCE, FINALITY_SOURCE, ODDS_SOURCE],
        "Games": games,
    }
