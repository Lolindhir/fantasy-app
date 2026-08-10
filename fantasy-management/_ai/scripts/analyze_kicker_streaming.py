#!/usr/bin/env python3
"""Rank Kicker Streaming candidates and make a gated weekly decision.

The deterministic Operations layer prepares facts only. This analysis layer reads
`kicker-streaming-inputs.json`, builds a preseason/base ranking, and optionally
combines it with externally researched weekly context. Without complete weekly
context it intentionally does not produce an add/drop recommendation.

Repository persistence is opt-in via --output. The default is stdout only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
CONTEXT_SCHEMA_VERSION = 1
ANALYSIS_ID = "kicker-streaming"


class KickerStreamingAnalysisError(RuntimeError):
    """Raised when a Kicker Streaming analysis cannot be produced safely."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KickerStreamingAnalysisError(f"Could not load JSON from {path}: {exc}") from exc


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def optional_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def bounded_score(value: Any, label: str) -> float:
    number = optional_number(value)
    if number is None or not 0 <= number <= 100:
        raise KickerStreamingAnalysisError(f"{label} must be numeric between 0 and 100")
    return number


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != 1 or config.get("analysis_id") != ANALYSIS_ID:
        raise KickerStreamingAnalysisError("Unexpected Kicker Streaming analysis config identity")

    baseline = config.get("baseline") if isinstance(config.get("baseline"), dict) else {}
    baseline_weights = baseline.get("weights") if isinstance(baseline.get("weights"), dict) else {}
    required_baseline = {
        "cbs_league_scoring_percentile",
        "fftoday_projection_percentile",
        "ffc_kicker_adp_percentile",
    }
    if set(baseline_weights) != required_baseline:
        raise KickerStreamingAnalysisError("Unexpected baseline weight keys")
    if any(optional_number(value) is None or float(value) <= 0 for value in baseline_weights.values()):
        raise KickerStreamingAnalysisError("Baseline weights must be positive numbers")
    if abs(sum(float(value) for value in baseline_weights.values()) - 1.0) > 1e-9:
        raise KickerStreamingAnalysisError("Baseline weights must sum to 1.0")

    minimum = baseline.get("minimum_core_signal_count")
    if not isinstance(minimum, int) or isinstance(minimum, bool) or not 1 <= minimum <= 3:
        raise KickerStreamingAnalysisError("minimum_core_signal_count must be between 1 and 3")
    shortlist = baseline.get("shortlist_free_agent_count")
    if not isinstance(shortlist, int) or isinstance(shortlist, bool) or shortlist < 1:
        raise KickerStreamingAnalysisError("shortlist_free_agent_count must be positive")
    if baseline.get("activity_policy") != "research_tiebreaker_only":
        raise KickerStreamingAnalysisError("Sleeper activity must remain a research-only tiebreaker")

    weekly = config.get("weekly") if isinstance(config.get("weekly"), dict) else {}
    weekly_weights = weekly.get("weights") if isinstance(weekly.get("weights"), dict) else {}
    required_weekly = {
        "baseline_score",
        "matchup_score",
        "offense_scoring_environment_score",
        "field_goal_opportunity_score",
        "weather_stadium_score",
        "qb_injury_context_score",
    }
    if set(weekly_weights) != required_weekly:
        raise KickerStreamingAnalysisError("Unexpected weekly weight keys")
    if any(optional_number(value) is None or float(value) < 0 for value in weekly_weights.values()):
        raise KickerStreamingAnalysisError("Weekly weights must be non-negative numbers")
    if abs(sum(float(value) for value in weekly_weights.values()) - 1.0) > 1e-9:
        raise KickerStreamingAnalysisError("Weekly weights must sum to 1.0")

    threshold = optional_number(weekly.get("switch_threshold_points"))
    if threshold is None or threshold < 0:
        raise KickerStreamingAnalysisError("switch_threshold_points must be non-negative")
    allowed_jobs = weekly.get("allowed_job_security")
    if not isinstance(allowed_jobs, list) or not allowed_jobs or not all(isinstance(item, str) for item in allowed_jobs):
        raise KickerStreamingAnalysisError("allowed_job_security must be a non-empty string list")
    injuries = weekly.get("disqualifying_player_injury_status")
    if not isinstance(injuries, list) or not injuries or not all(isinstance(item, str) for item in injuries):
        raise KickerStreamingAnalysisError("disqualifying_player_injury_status must be a non-empty string list")

    persistence = config.get("persistence") if isinstance(config.get("persistence"), dict) else {}
    if persistence.get("default") != "stdout_only":
        raise KickerStreamingAnalysisError("Kicker Streaming analysis must default to stdout_only")
    if persistence.get("repository_analysis_write_requires_explicit_approval") is not True:
        raise KickerStreamingAnalysisError("Repository analysis writes must require explicit approval")


def validate_source(source: dict[str, Any]) -> None:
    if source.get("schema_version") != 1 or source.get("dataset_id") != "kicker-streaming-inputs":
        raise KickerStreamingAnalysisError("Input is not a schema-version-1 kicker-streaming-inputs dataset")
    fingerprint = source.get("input_fingerprint")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise KickerStreamingAnalysisError("Kicker Streaming source fingerprint is missing or invalid")
    quality = source.get("quality") if isinstance(source.get("quality"), dict) else {}
    if quality.get("status") not in {"ok", "warning"}:
        raise KickerStreamingAnalysisError("Kicker Streaming source quality must be ok or warning")
    candidates = source.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise KickerStreamingAnalysisError("Kicker Streaming source must contain candidates")
    ids = [str(candidate.get("player_id")) for candidate in candidates if isinstance(candidate, dict)]
    if len(ids) != len(candidates) or len(ids) != len(set(ids)):
        raise KickerStreamingAnalysisError("Kicker Streaming source candidate IDs must be complete and unique")


def value_percentiles(values: dict[str, float]) -> dict[str, float]:
    """Return 0..100 percentiles with ties receiving the same percentile."""
    if not values:
        return {}
    if len(values) == 1:
        only_id = next(iter(values))
        return {only_id: 100.0}
    result: dict[str, float] = {}
    all_values = list(values.values())
    denominator = len(all_values) - 1
    for player_id, value in values.items():
        lower = sum(1 for other in all_values if other < value)
        result[player_id] = round(100.0 * lower / denominator, 2)
    return result


def cbs_midpoint(candidate: dict[str, Any]) -> float | None:
    league_projection = candidate.get("league_scoring_projection")
    if not isinstance(league_projection, dict):
        return None
    cbs = league_projection.get("cbs_sports")
    if not isinstance(cbs, dict) or cbs.get("status") not in {"exact", "bounded"}:
        return None
    minimum = optional_number(cbs.get("points_min"))
    maximum = optional_number(cbs.get("points_max"))
    if minimum is None or maximum is None or maximum < minimum:
        return None
    return round((minimum + maximum) / 2.0, 4)


def provider_percentile(candidate: dict[str, Any], provider_id: str) -> float | None:
    projections = candidate.get("projections") if isinstance(candidate.get("projections"), dict) else {}
    providers = projections.get("providers") if isinstance(projections.get("providers"), dict) else {}
    provider = providers.get(provider_id)
    if not isinstance(provider, dict) or provider.get("listed") is not True:
        return None
    percentile = optional_number(provider.get("percentile"))
    if percentile is None or not 0 <= percentile <= 100:
        return None
    return percentile


def ffc_percentile(candidate: dict[str, Any]) -> float | None:
    redraft = candidate.get("redraft_adp") if isinstance(candidate.get("redraft_adp"), dict) else {}
    primary = redraft.get("primary") if isinstance(redraft.get("primary"), dict) else {}
    if primary.get("listed") is not True or primary.get("applicable") is not True:
        return None
    percentile = optional_number(primary.get("percentile"))
    if percentile is None or not 0 <= percentile <= 100:
        return None
    return percentile


def sleeper_add_count(candidate: dict[str, Any]) -> float | None:
    activity = candidate.get("activity") if isinstance(candidate.get("activity"), dict) else {}
    add = activity.get("add") if isinstance(activity.get("add"), dict) else {}
    if add.get("status") != "listed":
        return None
    value = optional_number(add.get("count"))
    if value is None or value < 0:
        return None
    return value


def baseline_confidence(signal_count: int) -> str:
    if signal_count >= 3:
        return "high"
    if signal_count == 2:
        return "medium"
    return "low"


def build_baseline_rows(source: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = source["candidates"]
    cbs_values = {
        str(candidate["player_id"]): midpoint
        for candidate in candidates
        if isinstance(candidate, dict)
        and (midpoint := cbs_midpoint(candidate)) is not None
    }
    cbs_percentiles = value_percentiles(cbs_values)
    add_values = {
        str(candidate["player_id"]): count
        for candidate in candidates
        if isinstance(candidate, dict)
        and (count := sleeper_add_count(candidate)) is not None
    }
    add_percentiles = value_percentiles(add_values)

    baseline = config["baseline"]
    weights = {key: float(value) for key, value in baseline["weights"].items()}
    minimum_core = int(baseline["minimum_core_signal_count"])
    rows: list[dict[str, Any]] = []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        player_id = str(candidate["player_id"])
        signals = {
            "cbs_league_scoring_midpoint": cbs_values.get(player_id),
            "cbs_league_scoring_percentile": cbs_percentiles.get(player_id),
            "fftoday_projection_percentile": provider_percentile(candidate, "fftoday"),
            "ffc_kicker_adp_percentile": ffc_percentile(candidate),
            "sleeper_add_activity_percentile": add_percentiles.get(player_id),
        }
        weighted_values = {
            key: signals[key]
            for key in weights
            if signals[key] is not None
        }
        signal_count = len(weighted_values)
        score: float | None = None
        if signal_count >= minimum_core:
            available_weight = sum(weights[key] for key in weighted_values)
            score = round(
                sum(float(weighted_values[key]) * weights[key] for key in weighted_values) / available_weight,
                2,
            )

        role = candidate.get("role") if isinstance(candidate.get("role"), dict) else {}
        injury = candidate.get("injury") if isinstance(candidate.get("injury"), dict) else {}
        rows.append(
            {
                "player_id": player_id,
                "name": candidate.get("name"),
                "nfl_team": candidate.get("nfl_team"),
                "availability": candidate.get("availability"),
                "baseline_rank": None,
                "weekly_rank": None,
                "baseline_score": score,
                "baseline_core_signal_count": signal_count,
                "baseline_confidence": baseline_confidence(signal_count),
                "signals": signals,
                "nominal_role": {
                    "depth_chart_position": role.get("sleeper_depth_chart_position"),
                    "depth_chart_order": role.get("sleeper_depth_chart_order"),
                    "coverage_status": role.get("coverage_status"),
                    "interpretation": role.get("interpretation"),
                },
                "injury": {
                    "coverage_status": injury.get("coverage_status"),
                    "is_injured": injury.get("is_injured"),
                    "designation": injury.get("designation"),
                    "external_verification_priority": injury.get("external_verification_priority"),
                },
                "weekly": None,
            }
        )

    rows.sort(
        key=lambda row: (
            row["baseline_score"] is None,
            -(row["baseline_score"] if row["baseline_score"] is not None else -1.0),
            -(
                row["signals"]["sleeper_add_activity_percentile"]
                if row["signals"]["sleeper_add_activity_percentile"] is not None
                else -1.0
            ),
            str(row.get("name") or "").casefold(),
            row["player_id"],
        )
    )
    rank = 0
    for row in rows:
        if row["baseline_score"] is None:
            row["baseline_rank"] = None
            continue
        rank += 1
        row["baseline_rank"] = rank
    return rows


def build_shortlist(rows: list[dict[str, Any]], config: dict[str, Any]) -> list[str]:
    held = [row for row in rows if row["availability"] == "held"]
    free_agents = [
        row
        for row in rows
        if row["availability"] == "free_agent" and row["baseline_score"] is not None
    ]
    limit = int(config["baseline"]["shortlist_free_agent_count"])
    shortlist = [row["player_id"] for row in held]
    shortlist.extend(row["player_id"] for row in free_agents[:limit])
    return list(dict.fromkeys(shortlist))


def validate_weekly_context(
    context: dict[str, Any],
    source: dict[str, Any],
    candidate_ids: set[str],
) -> dict[str, dict[str, Any]]:
    if context.get("schema_version") != CONTEXT_SCHEMA_VERSION:
        raise KickerStreamingAnalysisError("Unexpected weekly-context schema version")
    if context.get("source_input_fingerprint") != source.get("input_fingerprint"):
        raise KickerStreamingAnalysisError("Weekly context does not match the current Kicker Streaming input fingerprint")

    source_league = source.get("league") if isinstance(source.get("league"), dict) else {}
    if str(context.get("season")) != str(source_league.get("season")):
        raise KickerStreamingAnalysisError("Weekly context season does not match Kicker Streaming inputs")
    source_week = source_league.get("current_week")
    if source_week is not None and int(context.get("week", -1)) != int(source_week):
        raise KickerStreamingAnalysisError("Weekly context week does not match Kicker Streaming inputs")
    if not isinstance(context.get("checked_at"), str) or not context["checked_at"]:
        raise KickerStreamingAnalysisError("Weekly context checked_at is required")

    players = context.get("players")
    if not isinstance(players, list) or not players:
        raise KickerStreamingAnalysisError("Weekly context must contain players")

    result: dict[str, dict[str, Any]] = {}
    allowed_jobs = {
        "confirmed_starter",
        "probable_starter",
        "competition",
        "uncertain",
        "not_current_starter",
    }
    allowed_injuries = {"clear", "monitor", "questionable", "out"}
    score_fields = [
        "matchup_score",
        "offense_scoring_environment_score",
        "field_goal_opportunity_score",
        "weather_stadium_score",
        "qb_injury_context_score",
    ]

    for player in players:
        if not isinstance(player, dict):
            raise KickerStreamingAnalysisError("Weekly context player entries must be objects")
        player_id = str(player.get("player_id"))
        if player_id not in candidate_ids:
            raise KickerStreamingAnalysisError(f"Weekly context references unknown candidate {player_id}")
        if player_id in result:
            raise KickerStreamingAnalysisError(f"Weekly context contains duplicate player {player_id}")
        if player.get("job_security") not in allowed_jobs:
            raise KickerStreamingAnalysisError(f"Invalid job_security for {player_id}")
        if player.get("player_injury_status") not in allowed_injuries:
            raise KickerStreamingAnalysisError(f"Invalid player_injury_status for {player_id}")
        for field in score_fields:
            bounded_score(player.get(field), f"{player_id}.{field}")
        evidence = player.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise KickerStreamingAnalysisError(f"Weekly context for {player_id} requires evidence")
        result[player_id] = player
    return result


def apply_weekly_context(
    rows: list[dict[str, Any]],
    context_by_player: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> None:
    weekly = config["weekly"]
    weights = {key: float(value) for key, value in weekly["weights"].items()}
    allowed_jobs = set(weekly["allowed_job_security"])
    disqualifying_injuries = set(weekly["disqualifying_player_injury_status"])
    component_fields = [
        "matchup_score",
        "offense_scoring_environment_score",
        "field_goal_opportunity_score",
        "weather_stadium_score",
        "qb_injury_context_score",
    ]
    weekly_component_weight = sum(weights[field] for field in component_fields)

    for row in rows:
        context = context_by_player.get(row["player_id"])
        if context is None:
            continue
        component_score = sum(
            bounded_score(context[field], f"{row['player_id']}.{field}") * weights[field]
            for field in component_fields
        ) / weekly_component_weight
        final_score: float | None = None
        if row["baseline_score"] is not None:
            final_score = round(
                row["baseline_score"] * weights["baseline_score"]
                + sum(
                    bounded_score(context[field], f"{row['player_id']}.{field}") * weights[field]
                    for field in component_fields
                ),
                2,
            )

        risk_flags: list[str] = []
        if context["job_security"] not in allowed_jobs:
            risk_flags.append("job_security_not_confirmed")
        if context["player_injury_status"] != "clear":
            risk_flags.append(f"player_injury_{context['player_injury_status']}")
        if row["nominal_role"].get("depth_chart_order") != 1:
            risk_flags.append("nominal_depth_chart_k1_not_confirmed")
        if row["injury"].get("is_injured") is True:
            risk_flags.append("repository_injury_signal_positive")

        eligible = (
            context["job_security"] in allowed_jobs
            and context["player_injury_status"] not in disqualifying_injuries
            and final_score is not None
        )
        row["weekly"] = {
            "job_security": context["job_security"],
            "player_injury_status": context["player_injury_status"],
            "eligible": eligible,
            "weekly_component_score": round(component_score, 2),
            "final_score": final_score,
            "risk_flags": risk_flags,
            "evidence_count": len(context["evidence"]),
        }

    ranked = [
        row
        for row in rows
        if row["weekly"] is not None and row["weekly"]["final_score"] is not None
    ]
    ranked.sort(
        key=lambda row: (
            -float(row["weekly"]["final_score"]),
            0 if row["availability"] == "held" else 1,
            str(row.get("name") or "").casefold(),
            row["player_id"],
        )
    )
    for index, row in enumerate(ranked, start=1):
        row["weekly_rank"] = index


def recommendation(
    rows: list[dict[str, Any]],
    mode: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    held = [row for row in rows if row["availability"] == "held"]
    held_id = held[0]["player_id"] if len(held) == 1 else None
    if len(held) != 1:
        return {
            "status": "insufficient_context",
            "held_player_id": held_id,
            "target_player_id": None,
            "score_delta": None,
            "reason_codes": ["held_kicker_population_not_exactly_one"],
            "summary": "Die Analyse erwartet genau einen aktuell gehaltenen Kicker.",
        }

    held_row = held[0]
    held_name = held_row.get("name") or held_row["player_id"]
    if mode == "baseline":
        return {
            "status": "weekly_context_required",
            "held_player_id": held_row["player_id"],
            "target_player_id": None,
            "score_delta": None,
            "reason_codes": ["weekly_context_missing"],
            "summary": (
                f"Für {held_name} wird noch keine Wechsel-Empfehlung erzeugt. "
                "Zuerst müssen Matchup, Offense, Field-Goal-Opportunity, Wetter, Job-Sicherheit und QB-/Injury-Kontext aktuell geprüft werden."
            ),
        }

    held_weekly = held_row.get("weekly")
    if not isinstance(held_weekly, dict) or held_weekly.get("final_score") is None:
        return {
            "status": "insufficient_context",
            "held_player_id": held_row["player_id"],
            "target_player_id": None,
            "score_delta": None,
            "reason_codes": ["held_kicker_weekly_context_missing"],
            "summary": f"Für {held_name} fehlt vollständiger aktueller Wochenkontext.",
        }

    alternatives = [
        row
        for row in rows
        if row["availability"] == "free_agent"
        and isinstance(row.get("weekly"), dict)
        and row["weekly"].get("eligible") is True
        and row["weekly"].get("final_score") is not None
    ]
    if not alternatives:
        return {
            "status": "insufficient_context",
            "held_player_id": held_row["player_id"],
            "target_player_id": None,
            "score_delta": None,
            "reason_codes": ["no_eligible_free_agent_weekly_context"],
            "summary": "Es wurde noch keine aktuell verifizierte, startberechtigte Free-Agent-Alternative vollständig bewertet.",
        }

    alternatives.sort(
        key=lambda row: (
            -float(row["weekly"]["final_score"]),
            str(row.get("name") or "").casefold(),
            row["player_id"],
        )
    )
    best = alternatives[0]
    delta = round(float(best["weekly"]["final_score"]) - float(held_weekly["final_score"]), 2)
    target_name = best.get("name") or best["player_id"]
    threshold = float(config["weekly"]["switch_threshold_points"])

    if held_weekly.get("eligible") is not True:
        return {
            "status": "switch_recommended",
            "held_player_id": held_row["player_id"],
            "target_player_id": best["player_id"],
            "score_delta": delta,
            "reason_codes": ["held_kicker_not_weekly_eligible", "best_verified_free_agent_selected"],
            "summary": (
                f"Wechsel von {held_name} zu {target_name} empfohlen, weil der gehaltene Kicker den aktuellen "
                "Job-/Injury-Gate nicht erfüllt und die Alternative verifiziert spielbar ist."
            ),
        }

    if delta >= threshold:
        return {
            "status": "switch_recommended",
            "held_player_id": held_row["player_id"],
            "target_player_id": best["player_id"],
            "score_delta": delta,
            "reason_codes": ["material_weekly_score_advantage"],
            "summary": (
                f"Wechsel von {held_name} zu {target_name} empfohlen. Die beste verifizierte Alternative liegt "
                f"{delta:.2f} Score-Punkte vor dem gehaltenen Kicker und überschreitet die Wechselhürde von {threshold:.2f}."
            ),
        }

    return {
        "status": "no_switch_recommended",
        "held_player_id": held_row["player_id"],
        "target_player_id": best["player_id"],
        "score_delta": delta,
        "reason_codes": ["no_material_weekly_score_advantage"],
        "summary": (
            f"Kein Wechsel empfohlen. {target_name} ist die beste verifizierte Free-Agent-Alternative, liegt aber nur "
            f"{delta:.2f} Score-Punkte relativ zu {held_name}; für einen Wechsel sind mindestens {threshold:.2f} erforderlich."
        ),
    }


def build(
    root: Path,
    config_path: Path,
    weekly_context_path: Path | None = None,
) -> dict[str, Any]:
    config = load_json(config_path)
    if not isinstance(config, dict):
        raise KickerStreamingAnalysisError("Kicker Streaming analysis config must be an object")
    validate_config(config)

    source_path = root / str(config["source"])
    source = load_json(source_path)
    if not isinstance(source, dict):
        raise KickerStreamingAnalysisError("Kicker Streaming inputs must be an object")
    validate_source(source)

    rows = build_baseline_rows(source, config)
    shortlist_ids = build_shortlist(rows, config)
    candidate_ids = {row["player_id"] for row in rows}

    mode = "baseline"
    context: dict[str, Any] | None = None
    context_by_player: dict[str, dict[str, Any]] = {}
    if weekly_context_path is not None:
        loaded_context = load_json(weekly_context_path)
        if not isinstance(loaded_context, dict):
            raise KickerStreamingAnalysisError("Weekly context must be an object")
        context = loaded_context
        context_by_player = validate_weekly_context(context, source, candidate_ids)
        apply_weekly_context(rows, context_by_player, config)
        mode = "weekly"

    source_league = source.get("league") if isinstance(source.get("league"), dict) else {}
    quality = source.get("quality") if isinstance(source.get("quality"), dict) else {}
    comparable_count = sum(1 for row in rows if row["baseline_score"] is not None)
    fingerprint_payload = {
        "config": config,
        "source_input_fingerprint": source["input_fingerprint"],
        "weekly_context": context,
    }

    result = {
        "schema_version": SCHEMA_VERSION,
        "analysis_id": ANALYSIS_ID,
        "mode": mode,
        "evaluated_at": context.get("checked_at") if context is not None else source.get("generated_at"),
        "input_fingerprint": sha256_text(canonical_json(fingerprint_payload)),
        "source": {
            "path": str(config["source"]),
            "dataset_id": source["dataset_id"],
            "input_fingerprint": source["input_fingerprint"],
        },
        "league": {
            "season": source_league.get("season"),
            "phase": source_league.get("phase"),
            "week": context.get("week") if context is not None else source_league.get("current_week"),
            "managed_team": source.get("managed_team") if isinstance(source.get("managed_team"), dict) else {},
        },
        "methodology": {
            "baseline_weights": config["baseline"]["weights"],
            "minimum_core_signal_count": config["baseline"]["minimum_core_signal_count"],
            "activity_policy": config["baseline"]["activity_policy"],
            "weekly_weights": config["weekly"]["weights"],
            "switch_threshold_points": config["weekly"]["switch_threshold_points"],
            "job_security_gate": config["weekly"]["allowed_job_security"],
        },
        "ranking": rows,
        "research_shortlist_ids": shortlist_ids,
        "recommendation": recommendation(rows, mode, config),
        "quality": {
            "source_quality": quality.get("status"),
            "held_count": sum(1 for row in rows if row["availability"] == "held"),
            "comparable_candidate_count": comparable_count,
            "weekly_context_player_count": len(context_by_player),
            "weekly_context_fingerprint_match": True if context is not None else None,
        },
    }
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repository root",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("fantasy-management/_ai/kicker-streaming-analysis-config.json"),
        help="Analysis config path relative to repository root unless absolute",
    )
    parser.add_argument(
        "--weekly-context",
        type=Path,
        default=None,
        help="Optional externally researched weekly-context JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output path. Without this flag the analysis is printed only to stdout.",
    )
    return parser.parse_args()


def resolve(root: Path, path: Path | None) -> Path | None:
    if path is None or path.is_absolute():
        return path
    return root / path


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    config_path = resolve(root, args.config)
    weekly_context_path = resolve(root, args.weekly_context)
    assert config_path is not None
    result = build(root, config_path, weekly_context_path)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        output_path = resolve(root, args.output)
        assert output_path is not None
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
