"""Experimental team/game PBP metric candidates, never a published NFL Games contract.

Issue #1077. Uses original game play rows already checked by the GameDetail
builder. No canonical player identity, player position, or player-stat input.
A complete gzip read is not proof of upstream play completeness.
"""
from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

_TEAM_METRIC_IDS = (
    "offensive_dropbacks_faced", "pass_attempts_faced", "rush_attempts_faced",
    "rush_epa_per_play_allowed", "rush_success_rate_allowed",
    "rush_explosive_10_rate_allowed", "rush_first_down_rate_allowed",
    "pass_epa_per_attempt_allowed", "dropback_epa_per_play_allowed",
    "dropback_success_rate_allowed", "pass_explosive_20_rate_allowed",
    "pass_yac_per_completion_allowed", "air_yards_per_attempt_allowed",
    "third_down_conversion_rate_allowed", "red_zone_epa_and_success_allowed",
    "down_distance_efficiency_allowed", "drive_start_context",
)
_POSITION_DEFERRED_IDS = (
    "rb_target_share_allowed", "rb_rushing_yards_per_carry_allowed",
    "rb_target_yards_and_epa_allowed", "wr_target_coverage_proxy",
    "te_target_coverage_proxy", "qb_passing_vs_scramble_context",
)
_NULLS = frozenset(("", "NA", "N/A", "NaN", "nan", "NULL", "null"))


def _number(row: Mapping[str, str], field: str) -> float | None:
    raw = str(row.get(field) or "").strip()
    if raw in _NULLS:
        return None
    try:
        number = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid PBP metric field {field}: {raw!r}") from exc
    if not number.is_finite():
        raise ValueError(f"Nonfinite PBP metric field {field}")
    return float(number)


def _flag(row: Mapping[str, str], field: str) -> int | None:
    value = _number(row, field)
    if value is not None and value not in (0, 1):
        raise ValueError(f"Invalid PBP metric flag {field}: {value}")
    return int(value) if value is not None else None


def _count(rows: list[Mapping[str, Any]], selector) -> tuple[list[Mapping[str, Any]], dict]:
    selected = []
    unknown = 0
    for play in rows:
        status = selector(play)
        if status is None:
            unknown += 1
        elif status:
            selected.append(play)
    return selected, {
        "Value": len(selected) if len(rows) > unknown else None,
        "KnownPlayCount": len(rows) - unknown,
        "UnknownFlagCount": unknown,
        "Status": "candidate-observed" if len(rows) > unknown else "no-observed-source-evidence",
    }


def _ratio(rows: list[Mapping[str, Any]], value_fn, *, kind: str = "rate") -> dict:
    observed = []
    for play in rows:
        value = value_fn(play)
        if value is not None:
            observed.append(float(value))
    numerator = math.fsum(observed)
    result = {
        "Eligible": len(rows), "Observed": len(observed),
        "Missing": len(rows) - len(observed),
        "Numerator": round(numerator, 3) if observed else None,
        "Denominator": len(observed),
        "Value": round(numerator / len(observed), 4) if observed else None,
        "Status": "candidate-observed" if observed else "no-observed-source-evidence",
    }
    if kind == "epa":
        result["SumEPA"] = result["Numerator"]
    return result


def _throw(play: Mapping[str, Any]) -> bool | None:
    row = play["SourceRow"]
    attempt = _flag(row, "pass_attempt")
    if attempt is None:
        return None
    if attempt == 0:
        return False
    sack = _flag(row, "sack")
    spike = _flag(row, "qb_spike")
    return sack == 0 and spike == 0 if sack is not None and spike is not None else None


def _rush(play: Mapping[str, Any]) -> bool | None:
    value = _flag(play["SourceRow"], "rush_attempt")
    return value == 1 if value is not None else None


def _dropback(play: Mapping[str, Any]) -> bool | None:
    value = _flag(play["SourceRow"], "qb_dropback")
    return value == 1 if value is not None else None


def _success(play: Mapping[str, Any]) -> float | None:
    value = play["Success"]
    return float(value) if value is not None else None


def _down_distance(play: Mapping[str, Any]) -> str | None:
    down, yards = play["Down"], play["YardsToGo"]
    if down is None or yards is None:
        return None
    # Research bins only; no published boundary/eligibility semantics.
    dist = "0-3" if yards <= 3 else "4-6" if yards <= 6 else "7-10" if yards <= 10 else "11+"
    return f"D{down}:{dist}"


def _team_candidates(plays: list[Mapping[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    dropbacks, metrics["offensive_dropbacks_faced"] = _count(plays, _dropback)
    throws, metrics["pass_attempts_faced"] = _count(plays, _throw)
    rushes, metrics["rush_attempts_faced"] = _count(plays, _rush)

    metrics["rush_epa_per_play_allowed"] = _ratio(rushes, lambda p: p["EPA"], kind="epa")
    metrics["rush_success_rate_allowed"] = _ratio(rushes, _success)
    def explosive_rush(play):
        yards = _number(play["SourceRow"], "rushing_yards")
        return float(yards >= 10) if yards is not None else None
    metrics["rush_explosive_10_rate_allowed"] = _ratio(rushes, explosive_rush)
    metrics["rush_first_down_rate_allowed"] = _ratio(
        rushes, lambda p: _flag(p["SourceRow"], "first_down"),
    )
    metrics["pass_epa_per_attempt_allowed"] = _ratio(throws, lambda p: p["EPA"], kind="epa")
    metrics["dropback_epa_per_play_allowed"] = _ratio(dropbacks, lambda p: p["EPA"], kind="epa")
    metrics["dropback_success_rate_allowed"] = _ratio(dropbacks, _success)

    def explosive_pass(play):
        completed = _flag(play["SourceRow"], "complete_pass")
        if completed is None:
            return None
        if completed == 0:
            return 0.0
        yards = _number(play["SourceRow"], "passing_yards")
        return float(yards >= 20) if yards is not None else None

    metrics["pass_explosive_20_rate_allowed"] = _ratio(throws, explosive_pass)
    completed_throws = [p for p in throws if _flag(p["SourceRow"], "complete_pass") == 1]
    metrics["pass_yac_per_completion_allowed"] = _ratio(
        completed_throws, lambda p: _number(p["SourceRow"], "yards_after_catch"),
    )
    metrics["pass_yac_per_completion_allowed"]["MissingCompletionFlagInThrows"] = sum(
        _flag(p["SourceRow"], "complete_pass") is None for p in throws
    )
    metrics["air_yards_per_attempt_allowed"] = _ratio(
        throws, lambda p: _number(p["SourceRow"], "air_yards"),
    )
    metrics["third_down_conversion_rate_allowed"] = _ratio(
        [p for p in plays if p["Down"] == 3],
        lambda p: _flag(p["SourceRow"], "third_down_converted"),
    )
    red_zone = [p for p in plays if p["Yardline100"] is not None and p["Yardline100"] <= 20]
    metrics["red_zone_epa_and_success_allowed"] = {
        "ObservedRedZoneScrimmagePlays": len(red_zone),
        "MissingYardline": sum(p["Yardline100"] is None for p in plays),
        "EPA": _ratio(red_zone, lambda p: p["EPA"], kind="epa"),
        "Success": _ratio(red_zone, _success),
        "Scope": "research-scrimmage-only-excludes-special-teams-and-conversions",
    }
    keys = sorted({_down_distance(p) for p in plays if _down_distance(p) is not None})
    metrics["down_distance_efficiency_allowed"] = {
        "Bins": {key: {
            "EPA": _ratio([p for p in plays if _down_distance(p) == key],
                          lambda p: p["EPA"], kind="epa"),
            "Success": _ratio([p for p in plays if _down_distance(p) == key], _success),
        } for key in keys},
        "UnknownDownOrDistance": sum(_down_distance(p) is None for p in plays),
        "Scope": "research-bins-0to3-4to6-7to10-11plus-not-approved-product-contract",
    }
    first_by_drive = {}
    missing_drive = 0
    for play in plays:
        if play["Drive"] is None:
            missing_drive += 1
            continue
        key = (play["PossessionTeam"], play["Drive"])
        if key not in first_by_drive or play["PlayID"] < first_by_drive[key]["PlayID"]:
            first_by_drive[key] = play
    firsts = list(first_by_drive.values())
    metrics["drive_start_context"] = {
        "DistinctObservedDrives": len(firsts), "MissingDriveInEligiblePlays": missing_drive,
        "FieldPosition": _ratio(firsts, lambda p: p["Yardline100"]),
        "Scope": "first-observed-scrimmage-row-only-not-verified-actual-drive-start",
    }
    if set(metrics) != set(_TEAM_METRIC_IDS):
        raise ValueError("PBP catalog team metrics incomplete")
    return metrics


def evaluate_team_pbp_metric_candidates(
    plays: list[Mapping[str, Any]], game: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate 17 identity-independent catalog candidates for each defense.

    Unknown qualification/measurement stays missing, never inferred zero.
    This reports candidate evidence only; real source coverage, penalty
    treatment, and predictive validity must be evaluated separately.
    """
    eligible = []
    counts = {"NonScrimmage": 0, "TwoPoint": 0, "UnknownTwoPoint": 0,
              "UnassignedTeams": 0}
    for play in plays:
        if play["PlayType"] not in ("pass", "run"):
            counts["NonScrimmage"] += 1
            continue
        two_point = _flag(play["SourceRow"], "two_point_attempt")
        if two_point is None:
            counts["UnknownTwoPoint"] += 1
        elif two_point == 1:
            counts["TwoPoint"] += 1
        elif not play["PossessionTeam"] or not play["DefenseTeam"]:
            counts["UnassignedTeams"] += 1
        else:
            eligible.append(play)
    teams = (game["AwayTeam"], game["HomeTeam"])
    return {
        "CatalogVersion": 1,
        "Status": "experimental-not-real-source-validated-not-publishable",
        "RequiredCanonicalPlayerID": False,
        "CandidateIDs": list(_TEAM_METRIC_IDS),
        "DeferredPositionDependentIDs": list(_POSITION_DEFERRED_IDS),
        "SourcePlayCount": len(plays), "EligibleScrimmagePlayCount": len(eligible),
        "Excluded": counts,
        "ByDefenseTeam": [{
            "Team": team,
            "AllowedOffensePerspective": True,
            "Metrics": _team_candidates([p for p in eligible if p["DefenseTeam"] == team]),
        } for team in teams],
        "CoverageVerified": False,
        "DefinitionScope": "research-only-no-product-writer-no-player-identity",
    }
