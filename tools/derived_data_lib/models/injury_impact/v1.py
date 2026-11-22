"""injury-impact-v1: projected starter potential lost to injuries per fantasy team and league week (Issue #1584).

Pure function of explicit inputs (no file, clock or league configuration). For one team and one week it compares two
position-conformant best lineups built from the SAME historical roster (starters, bench, Taxi and IR all count) and the SAME
participation-conditional PlayerWeekFantasy projections:

* Pool A (full): every rostered player with a game that week and a projection, as if nobody were injured.
* Pool B (usable): Pool A without the players who were demonstrably not usable because of an injury.
* ``Impact`` = best(A) - best(B). It is an opportunity cost under a modelled scenario, never an actual loss of points.

Rules (CP2 of Issue #1584, approved by Robert 2026-11-22):

* E1/E5 Players without a game (``bye`` state) are in neither pool and create no impact. A player without any availability record
  (for example a free agent without an NFL roster row) is in neither pool and is counted as ``NoRecord``. A player whose NFL roster
  status is not active (``not-on-active-roster``: cut, development squad, suspended and so on) is not an injury case and is in neither
  pool; it is counted as ``NotOnActiveRoster``.
* E2 States ``not-played-reported`` (including a Questionable player who then did not play) and ``not-played-reserve`` leave Pool B.
* E3/E4 ``healthy-scratch`` and ``played`` stay in Pool B, also a player the report called Out but who played.
* E6 ``unknown`` and ``not-played-unexplained`` leave Pool B and mark the team week ``HasUnknownEvidence``; they are never healthy.
* P2 An injured player without a projection cannot be valued: the team week is a lower bound (``IsLowerBound``) and the player is
  counted as ``Undeterminable``; nothing is filled with zero.
* P3 A usable player without a projection is missing from both pools alike (neutral) and counted as ``NoProjection``.
* A1 ``SingleReturnImpact`` of an injured player is best(B plus that player) - best(B). These values are not additive.

An unknown availability state fails closed (ValueError). Immutable after its first productive use; any change is ``injury-impact-v2``.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from weekly_lineup_optimizer import ScoredPlayer, StartingSlot, maximize_lineup

MODEL_ID = "injury-impact-v1"
KIND = "injury-impact"

DIGITS = 4
QUANTUM = Decimal(1).scaleb(-DIGITS)

PARAMS = MappingProxyType({
    "Scenario": "best-lineup-full-roster-minus-best-lineup-usable-roster",
    "Projection": "player-week-fantasy-conditional-on-participation",
    "RosterScope": "starters-bench-taxi-ir",
    "InjuredStates": ("not-played-reported", "not-played-reserve"),
    "UsableStates": ("played", "healthy-scratch"),
    "UnknownStates": ("unknown", "not-played-unexplained"),
    "NoGameStates": ("bye",),
    "NotInjuryStates": ("not-on-active-roster",),
    "Digits": DIGITS,
})

# Player categories (in this order of precedence the classification below applies)
CATEGORIES = ("Usable", "Injured", "Unknown", "Bye", "NotOnActiveRoster", "NoRecord")


def quantize(value: Decimal) -> float:
    """Half-up rounding to the product precision (+ 0.0 turns -0.0 into 0.0)."""
    return float(value.quantize(QUANTUM, rounding=ROUND_HALF_UP)) + 0.0


def classify(availability: Mapping[str, Any] | None) -> str:
    """Category of one rostered player-week from its availability record (None when the product has no record)."""
    if availability is None:
        return "NoRecord"
    state = availability.get("State")
    if state in PARAMS["UsableStates"]:
        return "Usable"
    if state in PARAMS["InjuredStates"]:
        return "Injured"
    if state in PARAMS["UnknownStates"]:
        return "Unknown"
    if state in PARAMS["NoGameStates"]:
        return "Bye"
    if state in PARAMS["NotInjuryStates"]:
        return "NotOnActiveRoster"
    raise ValueError(f"Unknown availability state {state!r}")


def _best(slots: Sequence[StartingSlot], players: Sequence[tuple[str, str, Decimal]]) -> Decimal:
    return maximize_lineup(slots, [ScoredPlayer(pid, pos, pts) for pid, pos, pts in players]).points


def compute_team_week(slots: Sequence[StartingSlot], players: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Impact of one team week.

    ``players``: one mapping per rostered player with ``CanonicalPlayerID``, ``Position``, ``Availability`` (the product record or
    None) and ``Projection`` (points or None). Order does not matter; the result is sorted deterministically.
    """
    ids = [p["CanonicalPlayerID"] for p in players]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate player in team week")
    counts = {name: 0 for name in CATEGORIES}
    counts.update({"Rostered": len(players), "Undeterminable": 0, "NoProjection": 0})
    pool_a: list[tuple[str, str, Decimal]] = []
    pool_b: list[tuple[str, str, Decimal]] = []
    injured: list[dict[str, Any]] = []
    for player in sorted(players, key=lambda p: p["CanonicalPlayerID"]):
        category = classify(player.get("Availability"))
        counts[category] += 1
        if category in ("Bye", "NotOnActiveRoster", "NoRecord"):
            continue
        projection = player.get("Projection")
        availability = player["Availability"]
        if projection is None:
            if category == "Injured":
                counts["Undeterminable"] += 1
                injured.append(_injured_row(player, availability, None, None))
            elif category == "Usable":
                counts["NoProjection"] += 1
            continue
        entry = (player["CanonicalPlayerID"], player["Position"], Decimal(str(projection)))
        pool_a.append(entry)
        if category == "Usable":
            pool_b.append(entry)
        elif category == "Injured":
            injured.append(_injured_row(player, availability, projection, entry))
    best_a = _best(slots, pool_a)
    best_b = _best(slots, pool_b)
    for row in injured:
        entry = row.pop("_entry")
        if entry is not None:
            row["SingleReturnImpact"] = quantize(_best(slots, pool_b + [entry]) - best_b)
    injured.sort(key=lambda r: (-(r["SingleReturnImpact"] or 0.0), r["CanonicalPlayerID"]))
    return {
        "ProjectedBest": quantize(best_a),
        "ProjectedBestHealthy": quantize(best_b),
        "Impact": quantize(best_a - best_b),
        "IsLowerBound": counts["Undeterminable"] > 0,
        "HasUnknownEvidence": counts["Unknown"] > 0,
        "Counts": counts,
        "Injured": injured,
    }


def _injured_row(player: Mapping[str, Any], availability: Mapping[str, Any], projection: Any, entry: Any) -> dict[str, Any]:
    report = availability.get("Report") or []
    designations = sorted({o["Game"] for o in report if isinstance(o, Mapping) and o.get("Game")})
    return {
        "CanonicalPlayerID": player["CanonicalPlayerID"],
        "State": availability["State"],
        "Available": availability.get("Available"),
        "Played": availability.get("Played"),
        "Projection": None if projection is None else float(projection),
        "SingleReturnImpact": None,
        "_entry": entry,
        "ReportedGameStatus": designations,
    }


def season_totals(week_rows: Sequence[Mapping[str, Any]], roster_ids: Sequence[str]) -> list[dict[str, Any]]:
    """Per team: sum of the (rounded) weekly impacts, so totals always equal the weekly values; top single-return players by season sum."""
    totals = []
    for roster_id in sorted(roster_ids):
        impact, with_impact, weeks, lower = Decimal(0), 0, 0, False
        per_player: dict[str, list[Any]] = {}
        undeterminable = 0
        peak: dict[str, Any] | None = None
        for week in week_rows:
            team = next((t for t in week["Teams"] if t["CanonicalLeagueRosterID"] == roster_id), None)
            if team is None:
                continue
            weeks += 1
            value = Decimal(str(team["Impact"]))
            impact += value
            with_impact += 1 if value > 0 else 0
            lower = lower or team["IsLowerBound"]
            undeterminable += team["Counts"]["Undeterminable"]
            if peak is None or team["Impact"] > peak["Impact"]:
                peak = {"Week": week["Week"], "Impact": team["Impact"]}
            for row in team["Injured"]:
                if row["SingleReturnImpact"] is not None:
                    acc = per_player.setdefault(row["CanonicalPlayerID"], [Decimal(0), 0])
                    acc[0] += Decimal(str(row["SingleReturnImpact"]))
                    acc[1] += 1
        ranked = sorted(per_player.items(), key=lambda kv: (-kv[1][0], kv[0]))
        totals.append({
            "CanonicalLeagueRosterID": roster_id,
            "Impact": quantize(impact),
            "ImpactPerWeek": quantize(impact / weeks) if weeks else None,
            "WeeksComputed": weeks,
            "WeeksWithImpact": with_impact,
            "IsLowerBound": lower,
            "Undeterminable": undeterminable,
            "PeakWeek": peak,
            "TopPlayers": [{"CanonicalPlayerID": pid, "SingleReturnImpact": quantize(v[0]), "Weeks": v[1]} for pid, v in ranked[:5]],
        })
    return totals
