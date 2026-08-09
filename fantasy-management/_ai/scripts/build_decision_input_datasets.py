#!/usr/bin/env python3
"""Build deterministic Fantasy Operations decision-input datasets.

This layer derives reusable Free-Agent, Kicker and Sleeper depth-chart coverage
inputs from the already materialized central player-signal dataset. It never
browses, calls an AI service or emits Add/Drop/Start/Sit recommendations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
CONFIG_SCHEMA_VERSION = 1
FREE_AGENT_DATASET_ID = "free-agent-signals"
KICKER_DATASET_ID = "kicker-streaming-inputs"
DEPTH_DATASET_ID = "depth-chart-coverage"
MANAGED_OWNERSHIP_STATUS = "mighty_giants"
FREE_AGENT_OWNERSHIP_STATUS = "fantasy_free_agent"

WEEKLY_KICKER_CONTEXT_REQUIRED = [
    "current_week_and_opponent",
    "team_offense_and_expected_scoring_environment",
    "field_goal_opportunity",
    "stadium_and_weather",
    "kicker_job_security_and_active_status",
    "quarterback_and_relevant_injury_context",
]


class DecisionInputMaterializationError(RuntimeError):
    """Raised when deterministic decision inputs cannot be built safely."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DecisionInputMaterializationError(f"Missing required JSON input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DecisionInputMaterializationError(f"Invalid JSON input {path}: {exc}") from exc


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_record(source_id: str, path: Path, root: Path, source_timestamp: Any = None) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise DecisionInputMaterializationError(f"Missing required source file: {path}") from exc
    return {
        "id": source_id,
        "path": path.resolve().relative_to(root.resolve()).as_posix(),
        "content_sha256": sha256_text(content),
        "source_timestamp": source_timestamp,
    }


def optional_number(value: Any) -> float | int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed.is_integer():
        return int(parsed)
    return round(parsed, 4)


def scoring_number(scoring: dict[str, Any], key: str) -> float | None:
    value = optional_number(scoring.get(key))
    return float(value) if value is not None else None


def player_sort_key(player: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(player.get("position") or ""),
        str(player.get("name") or "").casefold(),
        str(player.get("player_id") or ""),
    )


def depth_coverage_status(role: dict[str, Any]) -> str:
    position = role.get("sleeper_depth_chart_position")
    order = role.get("sleeper_depth_chart_order")
    if position is not None and order is not None:
        return "full"
    if position is not None:
        return "position_only"
    if order is not None:
        return "order_only"
    return "unavailable"


def build_depth_chart_coverage(
    players: list[dict[str, Any]],
    *,
    generated_at: Any,
    input_fingerprint: str,
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    by_position: dict[str, Counter[str]] = defaultdict(Counter)

    for player in players:
        role = player.get("role") if isinstance(player.get("role"), dict) else {}
        status = depth_coverage_status(role)
        position = str(player.get("position") or "")
        status_counts[status] += 1
        by_position[position][status] += 1
        records.append(
            {
                "player_id": str(player.get("player_id") or ""),
                "name": player.get("name"),
                "position": position,
                "nfl_team": player.get("nfl_team"),
                "sleeper_depth_chart_position": role.get("sleeper_depth_chart_position"),
                "sleeper_depth_chart_order": role.get("sleeper_depth_chart_order"),
                "coverage_status": status,
                "interpretation": "nominal_depth_chart_only_not_usage",
            }
        )

    records.sort(key=player_sort_key)
    available = status_counts["full"] + status_counts["position_only"] + status_counts["order_only"]
    total = len(records)
    by_position_output: dict[str, Any] = {}
    for position, counts in sorted(by_position.items()):
        position_total = sum(counts.values())
        position_available = counts["full"] + counts["position_only"] + counts["order_only"]
        by_position_output[position] = {
            "total": position_total,
            "available": position_available,
            "available_percent": round(position_available / position_total * 100, 2) if position_total else 0.0,
            "status_counts": dict(sorted(counts.items())),
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": DEPTH_DATASET_ID,
        "generated_at": generated_at,
        "input_fingerprint": input_fingerprint,
        "sources": sources,
        "population": {
            "player_count": total,
            "available": available,
            "available_percent": round(available / total * 100, 2) if total else 0.0,
            "status_counts": dict(sorted(status_counts.items())),
            "by_position": by_position_output,
        },
        "records": records,
        "interpretation": {
            "semantic": "Sleeper fields are nominal depth-chart hints only.",
            "usage_truth": False,
            "recommendation_eligible": False,
            "missing_semantics": "Missing depth-chart fields are unknown coverage, not a negative role judgment.",
        },
    }


def extract_scoring_type(league: dict[str, Any]) -> dict[str, Any]:
    scoring = league.get("ScoringType")
    if not isinstance(scoring, dict):
        raise DecisionInputMaterializationError("League input has no ScoringType object")
    return scoring


def cbs_league_scoring_projection(
    cbs: dict[str, Any] | None,
    scoring: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(cbs, dict) or not cbs.get("listed"):
        return {
            "status": "not_available",
            "lower_bound": None,
            "upper_bound": None,
            "exact_points": None,
            "reason": "CBS kicker projection is not listed for this player.",
        }

    exact_buckets = (
        ("fg_1_19", "fgm_0_19", "fgmiss_0_19"),
        ("fg_20_29", "fgm_20_29", "fgmiss_20_29"),
        ("fg_30_39", "fgm_30_39", "fgmiss_30_39"),
        ("fg_40_49", "fgm_40_49", "fgmiss_40_49"),
    )
    required_scoring_keys = [
        "fgm_0_19",
        "fgm_20_29",
        "fgm_30_39",
        "fgm_40_49",
        "fgm_50_59",
        "fgm_60p",
        "xpm",
        "xpmiss",
    ]
    if any(scoring_number(scoring, key) is None for key in required_scoring_keys):
        return {
            "status": "not_available",
            "lower_bound": None,
            "upper_bound": None,
            "exact_points": None,
            "reason": "League kicker scoring is missing a required made-field-goal or XP rule.",
        }

    lower = 0.0
    upper = 0.0
    components: dict[str, Any] = {}
    for source_prefix, made_key, miss_key in exact_buckets:
        made = optional_number(cbs.get(f"{source_prefix}_made"))
        attempts = optional_number(cbs.get(f"{source_prefix}_attempts"))
        made_points = scoring_number(scoring, made_key)
        miss_points = scoring_number(scoring, miss_key)
        if made is None or attempts is None or made_points is None:
            return {
                "status": "not_available",
                "lower_bound": None,
                "upper_bound": None,
                "exact_points": None,
                "reason": f"CBS or league scoring is missing data for {source_prefix}.",
            }
        miss_points = 0.0 if miss_points is None else miss_points
        misses = max(0.0, float(attempts) - float(made))
        points = float(made) * made_points + misses * miss_points
        lower += points
        upper += points
        components[source_prefix] = {
            "made": made,
            "attempts": attempts,
            "league_made_points": made_points,
            "league_miss_points": miss_points,
            "projected_points": round(points, 4),
        }

    made_50_plus = optional_number(cbs.get("fg_50_plus_made"))
    attempts_50_plus = optional_number(cbs.get("fg_50_plus_attempts"))
    if made_50_plus is None or attempts_50_plus is None:
        return {
            "status": "not_available",
            "lower_bound": None,
            "upper_bound": None,
            "exact_points": None,
            "reason": "CBS projection is missing its 50-plus field-goal bucket.",
        }

    made_50 = scoring_number(scoring, "fgm_50_59")
    made_60 = scoring_number(scoring, "fgm_60p")
    miss_50 = scoring_number(scoring, "fgmiss_50_59")
    miss_60 = scoring_number(scoring, "fgmiss_60p")
    miss_50 = 0.0 if miss_50 is None else miss_50
    miss_60 = 0.0 if miss_60 is None else miss_60
    misses_50_plus = max(0.0, float(attempts_50_plus) - float(made_50_plus))
    lower_50 = float(made_50_plus) * min(made_50, made_60) + misses_50_plus * min(miss_50, miss_60)
    upper_50 = float(made_50_plus) * max(made_50, made_60) + misses_50_plus * max(miss_50, miss_60)
    lower += lower_50
    upper += upper_50
    components["fg_50_plus"] = {
        "made": made_50_plus,
        "attempts": attempts_50_plus,
        "league_50_59_made_points": made_50,
        "league_60_plus_made_points": made_60,
        "league_50_59_miss_points": miss_50,
        "league_60_plus_miss_points": miss_60,
        "projected_points_lower": round(lower_50, 4),
        "projected_points_upper": round(upper_50, 4),
    }

    xpm = optional_number(cbs.get("xpm"))
    xpa = optional_number(cbs.get("xpa"))
    if xpm is None or xpa is None:
        return {
            "status": "not_available",
            "lower_bound": None,
            "upper_bound": None,
            "exact_points": None,
            "reason": "CBS projection is missing XP made/attempt data.",
        }
    xp_made_points = scoring_number(scoring, "xpm")
    xp_miss_points = scoring_number(scoring, "xpmiss")
    xp_misses = max(0.0, float(xpa) - float(xpm))
    xp_points = float(xpm) * xp_made_points + xp_misses * xp_miss_points
    lower += xp_points
    upper += xp_points
    components["xp"] = {
        "made": xpm,
        "attempts": xpa,
        "league_made_points": xp_made_points,
        "league_miss_points": xp_miss_points,
        "projected_points": round(xp_points, 4),
    }

    lower = round(lower, 2)
    upper = round(upper, 2)
    exact = lower if lower == upper else None
    return {
        "status": "exact" if exact is not None else "bounded",
        "lower_bound": lower,
        "upper_bound": upper,
        "exact_points": exact,
        "reason": (
            "Exact Mighty Giants season projection from CBS raw buckets."
            if exact is not None
            else "CBS groups all 50-plus field goals together, while Mighty Giants scores 50-59 and 60+ differently; a bounded projection is retained instead of inventing a split."
        ),
        "source_provider": "cbs-sports",
        "source_horizon": "season",
        "components": components,
    }


def compact_kicker_player(player: dict[str, Any], scoring: dict[str, Any]) -> dict[str, Any]:
    projections = player.get("projections") if isinstance(player.get("projections"), dict) else {}
    providers = projections.get("providers") if isinstance(projections.get("providers"), dict) else {}
    cbs = providers.get("cbs_sports") if isinstance(providers.get("cbs_sports"), dict) else None
    fftoday = providers.get("fftoday") if isinstance(providers.get("fftoday"), dict) else None
    redraft = player.get("redraft_adp") if isinstance(player.get("redraft_adp"), dict) else {}
    kicker_adp = redraft.get("kicker_ppr_8_team") if isinstance(redraft.get("kicker_ppr_8_team"), dict) else None
    if kicker_adp is None and isinstance(redraft.get("primary"), dict):
        kicker_adp = redraft.get("primary")

    return {
        "player_id": str(player.get("player_id") or ""),
        "name": player.get("name"),
        "position": player.get("position"),
        "nfl_team": player.get("nfl_team"),
        "ownership": player.get("ownership"),
        "app_data": player.get("app_data"),
        "injury": player.get("injury"),
        "role": player.get("role"),
        "activity": player.get("activity"),
        "comparison_signals": {
            "ffc_kicker_adp": kicker_adp,
            "projection_summary": projections.get("summary"),
            "fftoday_projection": fftoday,
            "cbs_sports_projection": cbs,
            "mighty_giants_cbs_season_points": cbs_league_scoring_projection(cbs, scoring),
        },
    }


def build_free_agent_dataset(
    players: list[dict[str, Any]],
    *,
    generated_at: Any,
    input_fingerprint: str,
    sources: list[dict[str, Any]],
    upstream_quality: dict[str, Any],
) -> dict[str, Any]:
    free_agents = [
        player
        for player in players
        if isinstance(player.get("ownership"), dict)
        and player["ownership"].get("status") == FREE_AGENT_OWNERSHIP_STATUS
    ]
    free_agents.sort(key=player_sort_key)
    position_counts = Counter(str(player.get("position") or "") for player in free_agents)
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": FREE_AGENT_DATASET_ID,
        "generated_at": generated_at,
        "input_fingerprint": input_fingerprint,
        "sources": sources,
        "population": {
            "player_count": len(free_agents),
            "positions": dict(sorted(position_counts.items())),
            "ownership_rule": "ownership.status == fantasy_free_agent from league Roster/Reserve/Taxi materialization",
        },
        "players": free_agents,
        "quality": {
            "upstream_status": upstream_quality.get("status"),
            "upstream_issue_count": upstream_quality.get("issue_count"),
        },
        "interpretation": {
            "players_is_free_agent_source_field_used_for_availability": False,
            "recommendation_eligible": False,
        },
    }


def build_kicker_dataset(
    players: list[dict[str, Any]],
    scoring: dict[str, Any],
    *,
    generated_at: Any,
    input_fingerprint: str,
    sources: list[dict[str, Any]],
    managed_team: dict[str, Any],
    upstream_quality: dict[str, Any],
) -> dict[str, Any]:
    held = [
        compact_kicker_player(player, scoring)
        for player in players
        if player.get("position") == "K"
        and isinstance(player.get("ownership"), dict)
        and player["ownership"].get("status") == MANAGED_OWNERSHIP_STATUS
    ]
    available = [
        compact_kicker_player(player, scoring)
        for player in players
        if player.get("position") == "K"
        and isinstance(player.get("ownership"), dict)
        and player["ownership"].get("status") == FREE_AGENT_OWNERSHIP_STATUS
    ]
    held.sort(key=player_sort_key)
    available.sort(key=player_sort_key)

    scoring_snapshot = {
        key: optional_number(scoring.get(key))
        for key in (
            "fgm_0_19",
            "fgm_20_29",
            "fgm_30_39",
            "fgm_40_49",
            "fgm_50_59",
            "fgm_60p",
            "fgmiss_0_19",
            "fgmiss_20_29",
            "fgmiss_30_39",
            "fgmiss_40_49",
            "fgmiss_50_59",
            "fgmiss_60p",
            "xpm",
            "xpmiss",
        )
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": KICKER_DATASET_ID,
        "generated_at": generated_at,
        "input_fingerprint": input_fingerprint,
        "sources": sources,
        "managed_team": managed_team,
        "league_kicker_scoring": scoring_snapshot,
        "held_kickers": held,
        "available_kickers": available,
        "population": {
            "held_kicker_count": len(held),
            "available_kicker_count": len(available),
        },
        "quality": {
            "upstream_status": upstream_quality.get("status"),
            "upstream_issue_count": upstream_quality.get("issue_count"),
        },
        "analysis_contract": {
            "recommendation_materialized": False,
            "provider_fantasy_points_policy": "kept_separate_not_averaged",
            "ffc_adp_role": "secondary_market_and_stability_signal",
            "weekly_context_required": WEEKLY_KICKER_CONTEXT_REQUIRED,
            "availability_rule": "only ownership.status == fantasy_free_agent is available",
            "held_rule": "only ownership.status == mighty_giants is held by the managed team",
            "weekly_ranking_status": "not_materialized_without_current_week_context",
        },
    }


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise DecisionInputMaterializationError("Unexpected decision-input materialization config schema version")
    if not isinstance(config.get("sources"), dict):
        raise DecisionInputMaterializationError("Decision-input config has no sources object")
    for key in ("player_signals", "league"):
        if not config["sources"].get(key):
            raise DecisionInputMaterializationError(f"Decision-input config has no source path for {key}")
    if not isinstance(config.get("output"), dict):
        raise DecisionInputMaterializationError("Decision-input config has no output object")
    for key in ("free_agents", "kicker_streaming", "depth_chart_coverage"):
        if not config["output"].get(key):
            raise DecisionInputMaterializationError(f"Decision-input config has no output path for {key}")


def build(root: Path, config_path: Path) -> dict[str, dict[str, Any]]:
    config = load_json(config_path)
    validate_config(config)
    player_signals_path = root / config["sources"]["player_signals"]
    league_path = root / config["sources"]["league"]
    player_signals = load_json(player_signals_path)
    league = load_json(league_path)

    if player_signals.get("dataset_id") != "player-signals":
        raise DecisionInputMaterializationError("Unexpected upstream player-signals dataset_id")
    players = player_signals.get("players")
    if not isinstance(players, list):
        raise DecisionInputMaterializationError("Upstream player-signals players must be a list")
    upstream_managed_team = player_signals.get("managed_team")
    if not isinstance(upstream_managed_team, dict):
        raise DecisionInputMaterializationError("Upstream player-signals has no managed_team object")
    configured_team_id = str((config.get("managed_team") or {}).get("team_id") or "")
    if configured_team_id and str(upstream_managed_team.get("team_id")) != configured_team_id:
        raise DecisionInputMaterializationError(
            f"Managed team mismatch: config={configured_team_id}, player-signals={upstream_managed_team.get('team_id')}"
        )

    scoring = extract_scoring_type(league)
    generated_at = player_signals.get("generated_at")
    input_sources = [
        file_record("player_signals", player_signals_path, root, generated_at),
        file_record("league", league_path, root),
        file_record("decision_input_config", config_path, root),
    ]
    fingerprint_payload = {
        "config": config,
        "sources": input_sources,
        "upstream_input_fingerprint": player_signals.get("input_fingerprint"),
    }
    input_fingerprint = sha256_text(canonical_json(fingerprint_payload))
    upstream_quality = player_signals.get("quality") if isinstance(player_signals.get("quality"), dict) else {}

    free_agents = build_free_agent_dataset(
        players,
        generated_at=generated_at,
        input_fingerprint=input_fingerprint,
        sources=input_sources,
        upstream_quality=upstream_quality,
    )
    depth = build_depth_chart_coverage(
        players,
        generated_at=generated_at,
        input_fingerprint=input_fingerprint,
        sources=input_sources,
    )
    kickers = build_kicker_dataset(
        players,
        scoring,
        generated_at=generated_at,
        input_fingerprint=input_fingerprint,
        sources=input_sources,
        managed_team=upstream_managed_team,
        upstream_quality=upstream_quality,
    )
    return {
        "free_agents": free_agents,
        "kicker_streaming": kickers,
        "depth_chart_coverage": depth,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("fantasy-management/automation/decision-input-materialization.json"),
    )
    parser.add_argument("--check", action="store_true", help="Build and validate without writing outputs.")
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)
    outputs = build(root, config_path)

    if not args.check:
        for key, value in outputs.items():
            write_json(root / config["output"][key], value)
    free_agents = outputs["free_agents"]["population"]["player_count"]
    held = outputs["kicker_streaming"]["population"]["held_kicker_count"]
    available = outputs["kicker_streaming"]["population"]["available_kicker_count"]
    depth = outputs["depth_chart_coverage"]["population"]
    print(
        "Validated decision inputs: "
        f"free_agents={free_agents}; held_kickers={held}; available_kickers={available}; "
        f"depth_chart_available={depth['available']}/{depth['player_count']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
