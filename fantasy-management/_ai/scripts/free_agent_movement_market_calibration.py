#!/usr/bin/env python3
"""Provider-specific market materiality helpers for free-agent movement discovery."""
from __future__ import annotations

from typing import Any


class MarketCalibrationError(RuntimeError):
    """Raised when provider-specific market calibration is invalid."""


def _positive_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) <= 0:
        raise MarketCalibrationError(f"{field} must be a positive number")
    return float(value)


def validate_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise MarketCalibrationError("market_value_materiality must be an object")

    authoritative_tier_source_id = config.get("authoritative_tier_source_id")
    if not isinstance(authoritative_tier_source_id, str) or not authoritative_tier_source_id.strip():
        raise MarketCalibrationError("authoritative_tier_source_id must be a non-empty string")

    fantasycalc = config.get("fantasycalc")
    if not isinstance(fantasycalc, dict):
        raise MarketCalibrationError("market_value_materiality.fantasycalc must be an object")
    source_id = fantasycalc.get("source_id")
    if not isinstance(source_id, str) or not source_id.strip():
        raise MarketCalibrationError("fantasycalc.source_id must be a non-empty string")

    percentile = fantasycalc.get("percentile")
    if not isinstance(percentile, dict):
        raise MarketCalibrationError("fantasycalc.percentile must be an object")
    pct_medium = _positive_number(
        percentile.get("medium_absolute_delta_points"),
        "fantasycalc.percentile.medium_absolute_delta_points",
    )
    pct_high = _positive_number(
        percentile.get("high_absolute_delta_points"),
        "fantasycalc.percentile.high_absolute_delta_points",
    )
    if pct_high < pct_medium:
        raise MarketCalibrationError("FantasyCalc high percentile threshold must be >= medium")

    value = fantasycalc.get("value")
    if not isinstance(value, dict):
        raise MarketCalibrationError("fantasycalc.value must be an object")
    value_medium_abs = _positive_number(
        value.get("medium_absolute_delta"),
        "fantasycalc.value.medium_absolute_delta",
    )
    value_medium_pct = _positive_number(
        value.get("medium_absolute_percent_change"),
        "fantasycalc.value.medium_absolute_percent_change",
    )
    value_high_abs = _positive_number(
        value.get("high_absolute_delta"),
        "fantasycalc.value.high_absolute_delta",
    )
    value_high_pct = _positive_number(
        value.get("high_absolute_percent_change"),
        "fantasycalc.value.high_absolute_percent_change",
    )
    if value_high_abs < value_medium_abs or value_high_pct < value_medium_pct:
        raise MarketCalibrationError("FantasyCalc high value thresholds must be >= medium")

    return config


def configured_source_ids(config: dict[str, Any]) -> set[str]:
    validated = validate_config(config)
    return {
        str(validated["authoritative_tier_source_id"]),
        str(validated["fantasycalc"]["source_id"]),
    }


def materiality_crossings(
    *,
    config: dict[str, Any],
    source_id: str,
    window_days: int,
    percentile_delta: float | None,
    value_delta: float | None,
    value_percent_change: float | None,
    tier_changed: bool,
    tier_from: Any,
    tier_to: Any,
) -> list[dict[str, Any]]:
    validated = validate_config(config)
    crossed: list[dict[str, Any]] = []

    if source_id == validated["authoritative_tier_source_id"] and tier_changed:
        crossed.append(
            {
                "family": "dynasty_market",
                "kind": "tier_change",
                "severity": "high",
                "window_days": window_days,
                "source_id": source_id,
                "from": tier_from,
                "to": tier_to,
            }
        )

    fantasycalc = validated["fantasycalc"]
    if source_id != fantasycalc["source_id"]:
        return crossed

    percentile_cfg = fantasycalc["percentile"]
    if percentile_delta is not None:
        absolute_percentile_delta = abs(float(percentile_delta))
        medium = float(percentile_cfg["medium_absolute_delta_points"])
        high = float(percentile_cfg["high_absolute_delta_points"])
        if absolute_percentile_delta >= medium:
            severity = "high" if absolute_percentile_delta >= high else "medium"
            crossed.append(
                {
                    "family": "dynasty_market",
                    "kind": "fantasycalc_percentile_movement",
                    "severity": severity,
                    "window_days": window_days,
                    "delta": percentile_delta,
                    "threshold": high if severity == "high" else medium,
                    "source_id": source_id,
                }
            )

    value_cfg = fantasycalc["value"]
    if value_delta is not None and value_percent_change is not None:
        absolute_value_delta = abs(float(value_delta))
        absolute_percent_change = abs(float(value_percent_change))
        medium_abs = float(value_cfg["medium_absolute_delta"])
        medium_pct = float(value_cfg["medium_absolute_percent_change"])
        high_abs = float(value_cfg["high_absolute_delta"])
        high_pct = float(value_cfg["high_absolute_percent_change"])
        if absolute_value_delta >= medium_abs and absolute_percent_change >= medium_pct:
            high = absolute_value_delta >= high_abs and absolute_percent_change >= high_pct
            crossed.append(
                {
                    "family": "dynasty_market",
                    "kind": "fantasycalc_value_movement",
                    "severity": "high" if high else "medium",
                    "window_days": window_days,
                    "delta": value_delta,
                    "value_percent_change": value_percent_change,
                    "threshold": {
                        "absolute_value_delta": high_abs if high else medium_abs,
                        "absolute_percent_change": high_pct if high else medium_pct,
                    },
                    "source_id": source_id,
                }
            )

    return crossed
