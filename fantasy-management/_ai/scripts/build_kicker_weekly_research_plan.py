#!/usr/bin/env python3
"""Build the deterministic research plan for a weekly Kicker Streaming decision.

The plan narrows the current Kicker candidate set to the held kicker(s) plus the
configured free-agent shortlist, then joins those candidates to the canonical
repository NFL schedule. It deliberately does not research weather, venue roof,
job security, injuries or qualitative matchup context. Those remain fresh
analysis inputs and are listed as explicit research requirements.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from analyze_kicker_streaming import (
    KickerStreamingAnalysisError,
    build_baseline_rows,
    build_shortlist,
    canonical_json,
    load_json,
    sha256_text,
    validate_config as validate_analysis_config,
    validate_source,
)

SCHEMA_VERSION = 1
DATASET_ID = "kicker-weekly-research-plan"


class KickerWeeklyResearchPlanError(RuntimeError):
    """Raised when a weekly research plan cannot be built safely."""


def parse_bool(value: Any, label: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    raise KickerWeeklyResearchPlanError(f"{label} must be boolean-like")


def optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def optional_epoch(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise KickerWeeklyResearchPlanError("gameTime_epoch must be numeric")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise KickerWeeklyResearchPlanError("gameTime_epoch must be numeric") from exc


def validate_research_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION or config.get("research_id") != "kicker-weekly-context":
        raise KickerWeeklyResearchPlanError("Unexpected Kicker weekly research config identity")

    inputs = config.get("inputs") if isinstance(config.get("inputs"), dict) else {}
    for key in ("kicker_streaming", "schedule", "analysis_config"):
        if not isinstance(inputs.get(key), str) or not inputs[key]:
            raise KickerWeeklyResearchPlanError(f"Research config input {key} is required")

    schedule = config.get("schedule") if isinstance(config.get("schedule"), dict) else {}
    if schedule.get("zero_games_semantics") != "bye":
        raise KickerWeeklyResearchPlanError("Zero-game schedule semantics must remain bye")
    if schedule.get("multiple_games_semantics") != "error":
        raise KickerWeeklyResearchPlanError("Multiple-game schedule semantics must remain error")

    research = config.get("research") if isinstance(config.get("research"), dict) else {}
    numeric_fields = (
        "decision_ready_max_hours_before_kickoff",
        "weather_max_age_hours",
        "job_security_max_age_hours",
        "player_injury_max_age_hours",
        "qb_injury_max_age_hours",
        "venue_max_age_hours",
    )
    for key in numeric_fields:
        value = research.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise KickerWeeklyResearchPlanError(f"Research config {key} must be a non-negative number")

    requirements = research.get("required_factors")
    if not isinstance(requirements, list) or not requirements or not all(isinstance(item, str) and item for item in requirements):
        raise KickerWeeklyResearchPlanError("Research required_factors must be a non-empty string list")

    persistence = config.get("persistence") if isinstance(config.get("persistence"), dict) else {}
    if persistence.get("weekly_context") != "ephemeral_by_default":
        raise KickerWeeklyResearchPlanError("Weekly context must remain ephemeral by default")
    if persistence.get("repository_analysis_write_requires_explicit_approval") is not True:
        raise KickerWeeklyResearchPlanError("Repository analysis writes must require explicit approval")


def parse_week_label(value: Any) -> int | None:
    text = optional_string(value)
    if text is None:
        return None
    prefix = "week "
    lowered = text.casefold()
    if not lowered.startswith(prefix):
        return None
    try:
        return int(text[len(prefix):].strip())
    except ValueError:
        return None


def normalize_schedule_games(schedule: Any, season: str, week: int, season_type: str) -> list[dict[str, Any]]:
    if not isinstance(schedule, list):
        raise KickerWeeklyResearchPlanError("Schedule input must be a JSON array")

    games: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in schedule:
        if not isinstance(row, dict):
            continue
        if str(row.get("season")) != season:
            continue
        if row.get("seasonType") != season_type:
            continue
        if parse_week_label(row.get("gameWeek")) != week:
            continue

        game_id = optional_string(row.get("gameID"))
        home = optional_string(row.get("home"))
        away = optional_string(row.get("away"))
        if game_id is None or home is None or away is None:
            raise KickerWeeklyResearchPlanError("Target-week schedule row is missing gameID/home/away")
        if game_id in seen_ids:
            raise KickerWeeklyResearchPlanError(f"Duplicate target-week gameID: {game_id}")
        seen_ids.add(game_id)

        games.append(
            {
                "game_id": game_id,
                "home": home,
                "away": away,
                "game_date": optional_string(row.get("gameDate")),
                "game_time": optional_string(row.get("gameTime")),
                "kickoff_epoch": optional_epoch(row.get("gameTime_epoch")),
                "neutral_site": parse_bool(row.get("neutralSite", False), f"neutralSite for {game_id}"),
                "espn_id": optional_string(row.get("espnID")),
                "espn_link": optional_string(row.get("espnLink")),
                "cbs_link": optional_string(row.get("cbsLink")),
                "game_status": optional_string(row.get("gameStatus")),
                "game_status_code": optional_string(row.get("gameStatusCode")),
            }
        )

    if not games:
        raise KickerWeeklyResearchPlanError(f"No {season_type} schedule rows found for season {season} week {week}")
    return games


def resolve_team_schedule(team: str | None, games: list[dict[str, Any]]) -> dict[str, Any]:
    if not team:
        raise KickerWeeklyResearchPlanError("Shortlisted Kicker is missing nfl_team")
    matches = [game for game in games if team in {game["home"], game["away"]}]
    if len(matches) > 1:
        raise KickerWeeklyResearchPlanError(f"Team {team} has multiple games in target week")
    if not matches:
        return {
            "status": "bye",
            "game_id": None,
            "opponent": None,
            "team_side": "bye",
            "home": None,
            "away": None,
            "kickoff_epoch": None,
            "game_date": None,
            "game_time": None,
            "neutral_site": False,
            "espn_id": None,
            "espn_link": None,
            "cbs_link": None,
        }

    game = matches[0]
    side = "home" if game["home"] == team else "away"
    opponent = game["away"] if side == "home" else game["home"]
    return {
        "status": "scheduled",
        "game_id": game["game_id"],
        "opponent": opponent,
        "team_side": side,
        "home": game["home"],
        "away": game["away"],
        "kickoff_epoch": game["kickoff_epoch"],
        "game_date": game["game_date"],
        "game_time": game["game_time"],
        "neutral_site": game["neutral_site"],
        "espn_id": game["espn_id"],
        "espn_link": game["espn_link"],
        "cbs_link": game["cbs_link"],
    }


def build_research_plan(
    source: dict[str, Any],
    analysis_config: dict[str, Any],
    research_config: dict[str, Any],
    schedule: Any,
    week: int | None = None,
) -> dict[str, Any]:
    validate_source(source)
    validate_analysis_config(analysis_config)
    validate_research_config(research_config)

    league = source.get("league") if isinstance(source.get("league"), dict) else {}
    season = str(league.get("season"))
    source_week = league.get("current_week")
    target_week = int(week if week is not None else source_week)
    if not 1 <= target_week <= 18:
        raise KickerWeeklyResearchPlanError("Target week must be between 1 and 18")

    games = normalize_schedule_games(
        schedule,
        season,
        target_week,
        str(research_config["schedule"].get("season_type", "Regular Season")),
    )

    try:
        baseline_rows = build_baseline_rows(source, analysis_config)
        shortlist_ids = build_shortlist(baseline_rows, analysis_config)
    except KickerStreamingAnalysisError as exc:
        raise KickerWeeklyResearchPlanError(str(exc)) from exc

    rows_by_id = {row["player_id"]: row for row in baseline_rows}
    research_requirements = list(research_config["research"]["required_factors"])
    candidates: list[dict[str, Any]] = []
    for player_id in shortlist_ids:
        row = rows_by_id.get(player_id)
        if row is None:
            raise KickerWeeklyResearchPlanError(f"Shortlist player missing from baseline rows: {player_id}")
        schedule_view = resolve_team_schedule(row.get("nfl_team"), games)
        neutral = bool(schedule_view["neutral_site"])
        expected_home = schedule_view["home"] if schedule_view["status"] == "scheduled" and not neutral else None
        if schedule_view["status"] == "bye":
            venue_reason = "Bye week: no game venue; candidate is not playable this week."
        elif neutral:
            venue_reason = "Neutral-site game: verify the actual venue and roof; home-team stadium assumptions are invalid."
        else:
            venue_reason = "Verify the current game venue and roof before weather scoring; Schedule.json does not carry venue metadata."

        candidates.append(
            {
                "player_id": player_id,
                "name": row.get("name"),
                "nfl_team": row.get("nfl_team"),
                "availability": row.get("availability"),
                "baseline_rank": row.get("baseline_rank"),
                "baseline_score": row.get("baseline_score"),
                "schedule": schedule_view,
                "venue_research": {
                    "required": True,
                    "reason": venue_reason,
                    "expected_home_team": expected_home,
                    "neutral_site_override_required": neutral,
                },
                "research_requirements": research_requirements,
            }
        )

    ids = [candidate["player_id"] for candidate in candidates]
    if len(ids) != len(set(ids)):
        raise KickerWeeklyResearchPlanError("Research plan candidate IDs are not unique")

    held_count = sum(1 for candidate in candidates if candidate["availability"] == "held")
    free_agent_count = sum(1 for candidate in candidates if candidate["availability"] == "free_agent")
    schedule_fingerprint = sha256_text(canonical_json(games))
    fingerprint_payload = {
        "schema_version": SCHEMA_VERSION,
        "source_input_fingerprint": source["input_fingerprint"],
        "season": season,
        "week": target_week,
        "analysis_config": analysis_config,
        "research_config": research_config,
        "schedule_fingerprint": schedule_fingerprint,
        "candidate_ids": ids,
    }

    policy = research_config["research"]
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": DATASET_ID,
        "generated_at": source.get("generated_at"),
        "input_fingerprint": sha256_text(canonical_json(fingerprint_payload)),
        "source_input_fingerprint": source["input_fingerprint"],
        "season": season,
        "week": target_week,
        "population": {
            "held_count": held_count,
            "shortlisted_free_agent_count": free_agent_count,
            "candidate_count": len(candidates),
        },
        "candidates": candidates,
        "research_policy": {
            "decision_ready_max_hours_before_kickoff": policy["decision_ready_max_hours_before_kickoff"],
            "weather_max_age_hours": policy["weather_max_age_hours"],
            "job_security_max_age_hours": policy["job_security_max_age_hours"],
            "player_injury_max_age_hours": policy["player_injury_max_age_hours"],
            "qb_injury_max_age_hours": policy["qb_injury_max_age_hours"],
            "venue_max_age_hours": policy["venue_max_age_hours"],
            "venue_policy": policy["venue_policy"],
            "weather_policy": policy["weather_policy"],
            "official_evidence_priority": policy["official_evidence_priority"],
        },
        "quality": {
            "status": "ok",
            "candidate_ids_unique": True,
            "scheduled_candidates_resolved": True,
            "bye_candidates_supported": True,
        },
    }


def validate_against_schema(payload: dict[str, Any], schema_path: Path) -> None:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - CI installs dependency
        raise KickerWeeklyResearchPlanError("jsonschema is required for schema validation") from exc
    schema = load_json(schema_path)
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="fantasy-management/generated/operations/kicker-streaming-inputs.json")
    parser.add_argument("--analysis-config", default="fantasy-management/_ai/kicker-streaming-analysis-config.json")
    parser.add_argument("--research-config", default="fantasy-management/_ai/kicker-weekly-research-config.json")
    parser.add_argument("--schedule", default="public/data/Schedule.json")
    parser.add_argument("--schema", default="fantasy-management/_ai/schemas/kicker-weekly-research-plan.schema.json")
    parser.add_argument("--week", type=int, default=None)
    parser.add_argument("--output", default=None, help="Optional output path. Default is stdout only.")
    args = parser.parse_args()

    source = load_json(Path(args.input))
    analysis_config = load_json(Path(args.analysis_config))
    research_config = load_json(Path(args.research_config))
    schedule = load_json(Path(args.schedule))
    payload = build_research_plan(source, analysis_config, research_config, schedule, args.week)
    validate_against_schema(payload, Path(args.schema))
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
