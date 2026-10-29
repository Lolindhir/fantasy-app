#!/usr/bin/env python3
"""Shared PlayerWeekFantasy v1 contract and scoring-profile identity helpers."""
from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping

from historical_fantasy_scoring import league_season_path, read_json, score_record

CONTRACT_VERSION = 1
SCORING_FINGERPRINT_VERSION = 1

PROJECTION_STATUSES = {
    "available",
    "insufficient-history",
    "no-game",
    "unavailable",
}
AVAILABLE_RANGE_QUALITIES = {
    "player-volatility",
    "limited-history-fallback",
}
ACTUAL_STATES = {
    "pending",
    "live",
    "final",
    "unavailable",
}
PARTICIPATION_CONDITION = "conditional-on-participation"

# Prediction-range levels published per player. PRIMARY is the level kept in the
# single-range field PredictionRange; DISPLAY is the level UIs show. Changing
# DISPLAY_INTERVAL_LEVEL (it must be published) switches every surface at once.
PUBLISHED_INTERVAL_LEVELS = (0.5, 0.8, 0.9)
PRIMARY_INTERVAL_LEVEL = 0.9
DISPLAY_INTERVAL_LEVEL = 0.9


def _canonical_decimal(value: Any) -> tuple[Decimal, str]:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"Scoring setting must be numeric, got {value!r}")

    raw = str(value).strip()
    if not raw:
        raise ValueError("Scoring setting must not be empty")

    try:
        decimal_value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"Scoring setting must be numeric, got {value!r}") from exc

    if not decimal_value.is_finite():
        raise ValueError(f"Scoring setting must be finite, got {value!r}")

    if decimal_value == 0:
        return decimal_value, "0"

    canonical = format(decimal_value.normalize(), "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    return decimal_value, canonical


def canonical_scoring_settings(scoring_settings: Mapping[str, Any]) -> dict[str, str]:
    """Return the effective active scoring profile in deterministic semantic form.

    Zero-valued settings are omitted because an absent setting and an explicit zero
    are equivalent for fantasy scoring. Numeric formatting is normalized so 1,
    1.0 and "1.000" have the same semantic identity.
    """

    if not isinstance(scoring_settings, Mapping):
        raise ValueError("ScoringSettings must be an object")

    active: dict[str, str] = {}
    for key, value in scoring_settings.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"ScoringSettings contains an invalid key: {key!r}")
        decimal_value, canonical = _canonical_decimal(value)
        if decimal_value == 0:
            continue
        active[key] = canonical

    return dict(sorted(active.items()))


def scoring_settings_fingerprint(scoring_settings: Mapping[str, Any]) -> str:
    """Return the stable semantic SHA-256 identity of effective ScoringSettings."""

    payload = {
        "ActiveSettings": canonical_scoring_settings(scoring_settings),
        "Version": SCORING_FINGERPRINT_VERSION,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def build_scoring_profile_identity(
    canonical_league_id: str,
    scoring_season: int,
    scoring_settings: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(canonical_league_id, str) or not canonical_league_id.strip():
        raise ValueError("CanonicalLeagueID must be a non-empty string")
    if isinstance(scoring_season, bool) or not isinstance(scoring_season, int) or scoring_season < 1:
        raise ValueError("Scoring profile Season must be a positive integer")

    active = canonical_scoring_settings(scoring_settings)
    return {
        "CanonicalLeagueID": canonical_league_id,
        "Season": scoring_season,
        "SettingsHash": scoring_settings_fingerprint(scoring_settings),
        "FingerprintVersion": SCORING_FINGERPRINT_VERSION,
        "ActiveSettingsCount": len(active),
    }


def load_scoring_profile_identity(
    repo_root: Path,
    canonical_league_id: str,
    scoring_season: int,
) -> dict[str, Any]:
    path = league_season_path(repo_root, canonical_league_id, scoring_season)
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Canonical League season is not an object: {path}")
    if payload.get("CanonicalLeagueID") != canonical_league_id:
        raise ValueError(
            "Canonical League identity mismatch while loading scoring profile: "
            f"expected={canonical_league_id!r} actual={payload.get('CanonicalLeagueID')!r}"
        )
    if payload.get("Season") != scoring_season:
        raise ValueError(
            "Canonical League scoring season mismatch: "
            f"expected={scoring_season} actual={payload.get('Season')!r}"
        )

    scoring_settings = payload.get("ScoringSettings")
    if not isinstance(scoring_settings, dict):
        raise ValueError(f"Canonical League season has no ScoringSettings object: {path}")

    return build_scoring_profile_identity(
        canonical_league_id,
        scoring_season,
        scoring_settings,
    )


def derive_actual_points(
    player_stat_record: dict[str, Any],
    scoring_settings: Mapping[str, Any],
    *,
    special_teams_fumble_events: list[dict[str, Any]] | None = None,
) -> float:
    """Derive one player's realized score through the canonical scorer."""

    result = score_record(
        player_stat_record,
        dict(scoring_settings),
        special_teams_fumble_events=special_teams_fumble_events,
    )
    unsupported = result.get("UnsupportedNonZeroSettings")
    if unsupported:
        raise ValueError(
            "Cannot derive PlayerWeekFantasy Actual with unsupported active scoring settings: "
            + ", ".join(str(value) for value in unsupported)
        )
    points = result.get("FantasyPoints")
    if isinstance(points, bool) or not isinstance(points, (int, float)) or not math.isfinite(float(points)):
        raise ValueError("Canonical scorer returned non-finite FantasyPoints")
    return float(points)


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{field} must be a finite number")
    return numeric


def _history_games(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Projection.HistoryGames must be a non-negative integer")
    return value


def _validate_range(value: Any, field: str) -> dict[str, float]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    level = _finite_number(value.get("Level"), f"{field}.Level")
    lower = _finite_number(value.get("Lower"), f"{field}.Lower")
    upper = _finite_number(value.get("Upper"), f"{field}.Upper")
    if not 0 < level < 1:
        raise ValueError(f"{field}.Level must be between 0 and 1")
    if lower > upper:
        raise ValueError(f"{field}.Lower must not exceed Upper")
    return {"Level": level, "Lower": lower, "Upper": upper}


def validate_prediction_ranges(
    value: Any,
    primary: Mapping[str, float],
) -> list[dict[str, float]]:
    """Validate the multi-level ranges; absent means only the primary range."""

    if value is None:
        return [dict(primary)]
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError("Projection.PredictionRanges must be a non-empty list")

    ranges = [
        _validate_range(item, f"Projection.PredictionRanges[{index}]")
        for index, item in enumerate(value)
    ]
    for previous, current in zip(ranges, ranges[1:]):
        if current["Level"] <= previous["Level"]:
            raise ValueError("Projection.PredictionRanges levels must be strictly ascending")
        if current["Lower"] > previous["Lower"] or current["Upper"] < previous["Upper"]:
            raise ValueError("Projection.PredictionRanges must be nested: higher levels are wider")

    matching = [item for item in ranges if item["Level"] == primary["Level"]]
    if len(matching) != 1 or matching[0] != dict(primary):
        raise ValueError("Projection.PredictionRanges must contain the primary PredictionRange")
    return ranges


def validate_projection(projection: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(projection, Mapping):
        raise ValueError("Projection must be an object")

    status = projection.get("Status")
    if status not in PROJECTION_STATUSES:
        raise ValueError(f"Unsupported Projection.Status: {status!r}")

    history_games = _history_games(projection.get("HistoryGames"))
    participation = projection.get("ParticipationCondition")
    if participation != PARTICIPATION_CONDITION:
        raise ValueError(
            "Projection.ParticipationCondition must be "
            f"{PARTICIPATION_CONDITION!r} in contract v1"
        )
    if projection.get("AvailabilityAdjustmentApplied") is not False:
        raise ValueError(
            "Projection.AvailabilityAdjustmentApplied must be false in contract v1"
        )

    point_model = projection.get("PointModel")
    interval_model = projection.get("IntervalModel")

    if status == "available":
        points = _finite_number(projection.get("Points"), "Projection.Points")
        prediction_range = projection.get("PredictionRange")
        if not isinstance(prediction_range, Mapping):
            raise ValueError("Available projection requires PredictionRange")
        primary_range = _validate_range(prediction_range, "Projection.PredictionRange")
        prediction_ranges = validate_prediction_ranges(
            projection.get("PredictionRanges"),
            primary_range,
        )

        range_quality = projection.get("RangeQuality")
        if range_quality not in AVAILABLE_RANGE_QUALITIES:
            raise ValueError(
                f"Available projection has unsupported RangeQuality: {range_quality!r}"
            )
        if not isinstance(point_model, str) or not point_model.strip():
            raise ValueError("Available projection requires PointModel")
        if not isinstance(interval_model, str) or not interval_model.strip():
            raise ValueError("Available projection requires IntervalModel")

        return {
            "Status": status,
            "Points": points,
            "PredictionRange": primary_range,
            "PredictionRanges": prediction_ranges,
            "RangeQuality": range_quality,
            "HistoryGames": history_games,
            "ParticipationCondition": participation,
            "AvailabilityAdjustmentApplied": False,
            "PointModel": point_model,
            "IntervalModel": interval_model,
        }

    if projection.get("Points") is not None:
        raise ValueError(f"Projection.Points must be null when Status={status}")
    if projection.get("PredictionRange") is not None:
        raise ValueError(f"Projection.PredictionRange must be null when Status={status}")
    if projection.get("PredictionRanges") not in (None, [], ()):
        raise ValueError(f"Projection.PredictionRanges must be empty when Status={status}")
    if projection.get("RangeQuality") != "unavailable":
        raise ValueError(f"Projection.RangeQuality must be 'unavailable' when Status={status}")

    for field, value in (("PointModel", point_model), ("IntervalModel", interval_model)):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"Projection.{field} must be null or a non-empty string")

    return {
        "Status": status,
        "Points": None,
        "PredictionRange": None,
        "PredictionRanges": [],
        "RangeQuality": "unavailable",
        "HistoryGames": history_games,
        "ParticipationCondition": participation,
        "AvailabilityAdjustmentApplied": False,
        "PointModel": point_model,
        "IntervalModel": interval_model,
    }


def validate_actual(actual: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(actual, Mapping):
        raise ValueError("Actual must be an object")

    state = actual.get("State")
    if state not in ACTUAL_STATES:
        raise ValueError(f"Unsupported Actual.State: {state!r}")

    points = actual.get("Points")
    if state in {"live", "final"}:
        normalized_points: float | None = _finite_number(points, "Actual.Points")
    else:
        if points is not None:
            raise ValueError(f"Actual.Points must be null when State={state}")
        normalized_points = None

    return {
        "Points": normalized_points,
        "State": state,
    }


def build_player_week_fantasy_record(
    canonical_player_id: str,
    *,
    projection: Mapping[str, Any],
    actual: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(canonical_player_id, str) or not canonical_player_id.strip():
        raise ValueError("CanonicalPlayerID must be a non-empty string")
    return {
        "CanonicalPlayerID": canonical_player_id,
        "Projection": validate_projection(projection),
        "Actual": validate_actual(actual),
    }


def _validate_settings_hash(value: Any) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise ValueError("ScoringProfile.SettingsHash must use sha256:<hex>")
    digest = value.split(":", 1)[1]
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError("ScoringProfile.SettingsHash must contain a lowercase SHA-256 digest")
    return value


def build_player_week_fantasy_contract(
    *,
    canonical_league_id: str,
    season: int,
    week: int,
    scoring_profile: Mapping[str, Any],
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(canonical_league_id, str) or not canonical_league_id.strip():
        raise ValueError("CanonicalLeagueID must be a non-empty string")
    if isinstance(season, bool) or not isinstance(season, int) or season < 1:
        raise ValueError("Season must be a positive integer")
    if isinstance(week, bool) or not isinstance(week, int) or week < 1:
        raise ValueError("Week must be a positive integer")
    if not isinstance(scoring_profile, Mapping):
        raise ValueError("ScoringProfile must be an object")
    if scoring_profile.get("CanonicalLeagueID") != canonical_league_id:
        raise ValueError("ScoringProfile CanonicalLeagueID does not match contract CanonicalLeagueID")

    scoring_season = scoring_profile.get("Season")
    if isinstance(scoring_season, bool) or not isinstance(scoring_season, int) or scoring_season < 1:
        raise ValueError("ScoringProfile.Season must be a positive integer")
    settings_hash = _validate_settings_hash(scoring_profile.get("SettingsHash"))
    fingerprint_version = scoring_profile.get("FingerprintVersion")
    if fingerprint_version != SCORING_FINGERPRINT_VERSION:
        raise ValueError(
            f"ScoringProfile.FingerprintVersion must be {SCORING_FINGERPRINT_VERSION}"
        )
    active_count = scoring_profile.get("ActiveSettingsCount")
    if isinstance(active_count, bool) or not isinstance(active_count, int) or active_count < 0:
        raise ValueError("ScoringProfile.ActiveSettingsCount must be a non-negative integer")

    normalized_records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_record in records:
        if not isinstance(raw_record, Mapping):
            raise ValueError("PlayerWeekFantasy records must be objects")
        canonical_player_id = raw_record.get("CanonicalPlayerID")
        normalized = build_player_week_fantasy_record(
            canonical_player_id,
            projection=raw_record.get("Projection"),
            actual=raw_record.get("Actual"),
        )
        player_id = normalized["CanonicalPlayerID"]
        if player_id in seen:
            raise ValueError(f"Duplicate CanonicalPlayerID in PlayerWeekFantasy: {player_id}")
        seen.add(player_id)
        normalized_records.append(normalized)

    normalized_records.sort(key=lambda record: record["CanonicalPlayerID"])

    return {
        "ContractVersion": CONTRACT_VERSION,
        "CanonicalLeagueID": canonical_league_id,
        "Season": season,
        "Week": week,
        "ScoringProfile": {
            "Season": scoring_season,
            "SettingsHash": settings_hash,
            "FingerprintVersion": fingerprint_version,
            "ActiveSettingsCount": active_count,
        },
        "Records": normalized_records,
    }
