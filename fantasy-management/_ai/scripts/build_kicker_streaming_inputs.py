#!/usr/bin/env python3
"""Build deterministic inputs for later Kicker Streaming analysis.

This layer selects the managed team's held kickers and all fantasy-free-agent
kickers from the already materialized Operations datasets. It also reconciles
provider stat projections with the current league kicker scoring where the
source fields permit it. Ambiguous distance coverage is represented as explicit
point bounds rather than false precision. No add/drop recommendation is made.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
CONFIG_SCHEMA_VERSION = 1
DATASET_ID = "kicker-streaming-inputs"

KICKER_SCORING_KEYS = [
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
]


class KickerStreamingInputError(RuntimeError):
    """Raised when Kicker Streaming inputs cannot be built safely."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KickerStreamingInputError(f"Could not load JSON from {path}: {exc}") from exc


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise KickerStreamingInputError(f"Expected numeric {label}, got {value!r}")
    return float(value)


def optional_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise KickerStreamingInputError("Unexpected Kicker Streaming config schema version")
    population = config.get("population") if isinstance(config.get("population"), dict) else {}
    if population.get("position") != "K":
        raise KickerStreamingInputError("Kicker Streaming population must use position K")
    if population.get("held_selector") != "managed_team":
        raise KickerStreamingInputError("Held kicker selector must use managed_team")
    if population.get("free_agent_ownership_status") != "fantasy_free_agent":
        raise KickerStreamingInputError("Free-agent kicker ownership must be fantasy_free_agent")


def validate_source(document: dict[str, Any], dataset_id: str) -> None:
    if document.get("schema_version") != 1 or document.get("dataset_id") != dataset_id:
        raise KickerStreamingInputError(f"Input is not a schema-version-1 {dataset_id} dataset")
    fingerprint = document.get("input_fingerprint")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise KickerStreamingInputError(f"{dataset_id} input_fingerprint is missing or invalid")
    quality = document.get("quality") if isinstance(document.get("quality"), dict) else {}
    if quality.get("status") not in {"ok", "warning"}:
        raise KickerStreamingInputError(f"{dataset_id} quality must be ok or warning")
    if not isinstance(document.get("players"), list) or not document["players"]:
        raise KickerStreamingInputError(f"{dataset_id} must contain a non-empty players array")


def ownership_status(player: dict[str, Any]) -> str | None:
    ownership = player.get("ownership") if isinstance(player.get("ownership"), dict) else {}
    value = ownership.get("status")
    return str(value) if value is not None else None


def owned_by_team(player: dict[str, Any], team_id: str) -> bool:
    ownership = player.get("ownership") if isinstance(player.get("ownership"), dict) else {}
    teams = ownership.get("teams") if isinstance(ownership.get("teams"), list) else []
    return any(
        isinstance(team, dict) and str(team.get("team_id")) == team_id
        for team in teams
    )


def kicker_scoring(league: dict[str, Any]) -> dict[str, float]:
    scoring = league.get("ScoringType") if isinstance(league.get("ScoringType"), dict) else None
    if scoring is None:
        raise KickerStreamingInputError("League ScoringType is missing")
    result: dict[str, float] = {}
    for key in KICKER_SCORING_KEYS:
        if key not in scoring:
            raise KickerStreamingInputError(f"League kicker scoring key is missing: {key}")
        result[key] = number(scoring[key], f"ScoringType.{key}")
    return result


def projection_provider(player: dict[str, Any], key: str) -> dict[str, Any] | None:
    projections = player.get("projections") if isinstance(player.get("projections"), dict) else {}
    providers = projections.get("providers") if isinstance(projections.get("providers"), dict) else {}
    provider = providers.get(key)
    if not isinstance(provider, dict) or not provider.get("listed"):
        return None
    return provider


def validate_attempts(made: float, attempts: float, label: str) -> float:
    if made < 0 or attempts < 0 or made > attempts:
        raise KickerStreamingInputError(
            f"Invalid projected makes/attempts for {label}: made={made}, attempts={attempts}"
        )
    return attempts - made


def unavailable(reason: str) -> dict[str, Any]:
    return {
        "status": "not_available",
        "points_min": None,
        "points_max": None,
        "provider_projected_fantasy_points": None,
        "reason": reason,
        "components": {},
    }


def cbs_scoring_projection(player: dict[str, Any], scoring: dict[str, float]) -> dict[str, Any]:
    provider = projection_provider(player, "cbs_sports")
    if provider is None:
        return unavailable("CBS Sports projection not listed for this player")

    buckets = [
        ("1_19", "fg_1_19_made", "fg_1_19_attempts", "fgm_0_19", "fgmiss_0_19"),
        ("20_29", "fg_20_29_made", "fg_20_29_attempts", "fgm_20_29", "fgmiss_20_29"),
        ("30_39", "fg_30_39_made", "fg_30_39_attempts", "fgm_30_39", "fgmiss_30_39"),
        ("40_49", "fg_40_49_made", "fg_40_49_attempts", "fgm_40_49", "fgmiss_40_49"),
    ]
    exact_field_goal_points = 0.0
    components: dict[str, Any] = {}
    for label, made_key, attempts_key, score_key, miss_key in buckets:
        made = number(provider.get(made_key), f"CBS {made_key}")
        attempts = number(provider.get(attempts_key), f"CBS {attempts_key}")
        misses = validate_attempts(made, attempts, f"CBS {label}")
        points = made * scoring[score_key] + misses * scoring[miss_key]
        exact_field_goal_points += points
        components[label] = {
            "made": made,
            "attempts": attempts,
            "misses": misses,
            "points": round(points, 4),
        }

    made_50_plus = number(provider.get("fg_50_plus_made"), "CBS fg_50_plus_made")
    attempts_50_plus = number(provider.get("fg_50_plus_attempts"), "CBS fg_50_plus_attempts")
    misses_50_plus = validate_attempts(made_50_plus, attempts_50_plus, "CBS 50+")
    make_values = [scoring["fgm_50_59"], scoring["fgm_60p"]]
    miss_values = [scoring["fgmiss_50_59"], scoring["fgmiss_60p"]]
    points_50_min = made_50_plus * min(make_values) + misses_50_plus * min(miss_values)
    points_50_max = made_50_plus * max(make_values) + misses_50_plus * max(miss_values)

    xpm = number(provider.get("xpm"), "CBS xpm")
    xpa = number(provider.get("xpa"), "CBS xpa")
    xp_misses = validate_attempts(xpm, xpa, "CBS extra points")
    xp_points = xpm * scoring["xpm"] + xp_misses * scoring["xpmiss"]

    minimum = exact_field_goal_points + points_50_min + xp_points
    maximum = exact_field_goal_points + points_50_max + xp_points
    bounded = abs(maximum - minimum) > 1e-9
    components["50_plus"] = {
        "made": made_50_plus,
        "attempts": attempts_50_plus,
        "misses": misses_50_plus,
        "points_min": round(points_50_min, 4),
        "points_max": round(points_50_max, 4),
        "ambiguity": "CBS combines 50-59 and 60+ while league scoring separates them",
    }
    components["extra_points"] = {
        "made": xpm,
        "attempts": xpa,
        "misses": xp_misses,
        "points": round(xp_points, 4),
    }

    return {
        "status": "bounded" if bounded else "exact",
        "points_min": round(minimum, 4),
        "points_max": round(maximum, 4),
        "provider_projected_fantasy_points": optional_number(provider.get("projected_fantasy_points")),
        "reason": (
            "CBS 50+ field goals are bounded across the league's separate 50-59 and 60+ scoring"
            if bounded
            else "Available CBS distance buckets map exactly to current league scoring"
        ),
        "components": components,
    }


def fftoday_scoring_projection(player: dict[str, Any], scoring: dict[str, float]) -> dict[str, Any]:
    provider = projection_provider(player, "fftoday")
    if provider is None:
        return unavailable("FFToday projection not listed for this player")

    fgm = number(provider.get("fgm"), "FFToday fgm")
    fga = number(provider.get("fga"), "FFToday fga")
    fg_misses = validate_attempts(fgm, fga, "FFToday field goals")
    epm = number(provider.get("epm"), "FFToday epm")
    epa = number(provider.get("epa"), "FFToday epa")
    xp_misses = validate_attempts(epm, epa, "FFToday extra points")

    make_values = [
        scoring["fgm_0_19"],
        scoring["fgm_20_29"],
        scoring["fgm_30_39"],
        scoring["fgm_40_49"],
        scoring["fgm_50_59"],
        scoring["fgm_60p"],
    ]
    miss_values = [
        scoring["fgmiss_0_19"],
        scoring["fgmiss_20_29"],
        scoring["fgmiss_30_39"],
        scoring["fgmiss_40_49"],
        scoring["fgmiss_50_59"],
        scoring["fgmiss_60p"],
    ]
    fg_min = fgm * min(make_values) + fg_misses * min(miss_values)
    fg_max = fgm * max(make_values) + fg_misses * max(miss_values)
    xp_points = epm * scoring["xpm"] + xp_misses * scoring["xpmiss"]
    minimum = fg_min + xp_points
    maximum = fg_max + xp_points
    bounded = abs(maximum - minimum) > 1e-9

    return {
        "status": "bounded" if bounded else "exact",
        "points_min": round(minimum, 4),
        "points_max": round(maximum, 4),
        "provider_projected_fantasy_points": optional_number(provider.get("projected_fantasy_points")),
        "reason": (
            "FFToday supplies total field goals without distance buckets, so league scoring is bounded by the minimum and maximum field-goal values"
            if bounded
            else "Current league field-goal scoring is distance-invariant for the available FFToday totals"
        ),
        "components": {
            "field_goals": {
                "made": fgm,
                "attempts": fga,
                "misses": fg_misses,
                "points_min": round(fg_min, 4),
                "points_max": round(fg_max, 4),
            },
            "extra_points": {
                "made": epm,
                "attempts": epa,
                "misses": xp_misses,
                "points": round(xp_points, 4),
            },
        },
    }


def candidate(player: dict[str, Any], availability: str, scoring: dict[str, float]) -> dict[str, Any]:
    return {
        "player_id": str(player["player_id"]),
        "name": player.get("name"),
        "nfl_team": player.get("nfl_team"),
        "availability": availability,
        "ownership": player.get("ownership") if isinstance(player.get("ownership"), dict) else {},
        "injury": player.get("injury") if isinstance(player.get("injury"), dict) else {},
        "role": player.get("role") if isinstance(player.get("role"), dict) else {},
        "market": player.get("market") if isinstance(player.get("market"), dict) else {},
        "redraft_adp": player.get("redraft_adp") if isinstance(player.get("redraft_adp"), dict) else {},
        "projections": player.get("projections") if isinstance(player.get("projections"), dict) else {},
        "activity": player.get("activity") if isinstance(player.get("activity"), dict) else {},
        "league_scoring_projection": {
            "cbs_sports": cbs_scoring_projection(player, scoring),
            "fftoday": fftoday_scoring_projection(player, scoring),
        },
    }


def validate_output(data: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "dataset_id",
        "generated_at",
        "input_fingerprint",
        "managed_team",
        "league",
        "population",
        "candidates",
        "quality",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise KickerStreamingInputError(f"Output missing required keys: {missing}")
    if data["schema_version"] != SCHEMA_VERSION or data["dataset_id"] != DATASET_ID:
        raise KickerStreamingInputError("Unexpected Kicker Streaming output identity")
    ids = [candidate["player_id"] for candidate in data["candidates"]]
    if len(ids) != len(set(ids)):
        raise KickerStreamingInputError("Kicker Streaming output contains duplicate player IDs")
    if len(ids) != data["population"]["candidate_count"]:
        raise KickerStreamingInputError("Kicker Streaming candidate count mismatch")


def build(root: Path, config_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    if not isinstance(config, dict):
        raise KickerStreamingInputError("Kicker Streaming config must be an object")
    validate_config(config)

    sources = config["sources"]
    league = load_json(root / sources["league"])
    player_signals = load_json(root / sources["player_signals"])
    free_agent_signals = load_json(root / sources["free_agent_signals"])
    if not isinstance(league, dict) or not isinstance(player_signals, dict) or not isinstance(free_agent_signals, dict):
        raise KickerStreamingInputError("Kicker Streaming inputs must be JSON objects")
    validate_source(player_signals, "player-signals")
    validate_source(free_agent_signals, "free-agent-signals")

    free_agent_source = free_agent_signals.get("source") if isinstance(free_agent_signals.get("source"), dict) else {}
    if free_agent_source.get("input_fingerprint") != player_signals.get("input_fingerprint"):
        raise KickerStreamingInputError("free-agent-signals does not reference the current player-signals fingerprint")

    managed_team_id = str(config["managed_team"]["team_id"])
    teams = league.get("Teams") if isinstance(league.get("Teams"), list) else []
    managed_team = next((team for team in teams if str(team.get("TeamID")) == managed_team_id), None)
    if not isinstance(managed_team, dict):
        raise KickerStreamingInputError(f"Managed team {managed_team_id} not found")

    scoring = kicker_scoring(league)
    held_players = [
        player
        for player in player_signals["players"]
        if isinstance(player, dict)
        and player.get("position") == "K"
        and owned_by_team(player, managed_team_id)
    ]
    free_agent_players = [
        player
        for player in free_agent_signals["players"]
        if isinstance(player, dict) and player.get("position") == "K"
    ]
    if any(ownership_status(player) != "fantasy_free_agent" for player in free_agent_players):
        raise KickerStreamingInputError("free-agent-signals contains a rostered kicker")

    expected_free_agent_ids = {
        str(player["player_id"])
        for player in player_signals["players"]
        if isinstance(player, dict)
        and player.get("position") == "K"
        and ownership_status(player) == "fantasy_free_agent"
    }
    actual_free_agent_ids = {str(player["player_id"]) for player in free_agent_players}
    if actual_free_agent_ids != expected_free_agent_ids:
        raise KickerStreamingInputError("Free-agent kicker population does not match player-signals ownership")

    candidates = [candidate(player, "held", scoring) for player in held_players]
    candidates.extend(candidate(player, "free_agent", scoring) for player in free_agent_players)
    candidates.sort(
        key=lambda item: (
            0 if item["availability"] == "held" else 1,
            str(item.get("name") or "").casefold(),
            item["player_id"],
        )
    )

    quality_player = player_signals["quality"]["status"]
    quality_free_agent = free_agent_signals["quality"]["status"]
    quality_status = "warning" if "warning" in {quality_player, quality_free_agent} else "ok"
    fingerprint_payload = {
        "config": config,
        "league_scoring": scoring,
        "player_signals_fingerprint": player_signals["input_fingerprint"],
        "free_agent_signals_fingerprint": free_agent_signals["input_fingerprint"],
        "candidate_ids": [item["player_id"] for item in candidates],
    }

    result = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": DATASET_ID,
        "generated_at": player_signals.get("generated_at"),
        "input_fingerprint": sha256_text(canonical_json(fingerprint_payload)),
        "managed_team": {
            "team_id": managed_team.get("TeamID"),
            "name": managed_team.get("Team"),
        },
        "league": {
            "season": league.get("Season"),
            "phase": league.get("Phase"),
            "current_week": league.get("CurrentWeek"),
            "kicker_scoring": scoring,
            "projection_reconciliation": {
                "cbs_sports": "50_plus_bucket_requires_50_59_vs_60_plus_bounds",
                "fftoday": "no_distance_buckets_requires_field_goal_scoring_bounds",
                "provider_points_policy": "keep_separate_not_league_scoring",
            },
        },
        "population": {
            "position": "K",
            "held_count": len(held_players),
            "free_agent_count": len(free_agent_players),
            "candidate_count": len(candidates),
        },
        "candidates": candidates,
        "quality": {
            "status": quality_status,
            "player_signal_quality": quality_player,
            "free_agent_quality": quality_free_agent,
            "candidate_ids_unique": True,
            "free_agents_match_upstream": True,
        },
    }
    validate_output(result)
    return result


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("fantasy-management/automation/kicker-streaming-input-materialization.json"),
    )
    parser.add_argument("--check", action="store_true", help="Build and validate without writing output")
    args = parser.parse_args()

    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)
    if not isinstance(config, dict):
        raise KickerStreamingInputError("Kicker Streaming config must be an object")
    result = build(root, config_path)
    if args.check:
        print(
            f"Validated {result['population']['candidate_count']} kicker candidates "
            f"({result['population']['held_count']} held, "
            f"{result['population']['free_agent_count']} free agents); "
            f"quality={result['quality']['status']}."
        )
        return 0

    output_path = root / config["output"]["kicker_streaming_inputs"]
    write_json(output_path, result)
    print(
        f"Wrote {output_path.relative_to(root)} with "
        f"{result['population']['candidate_count']} kicker candidates."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
