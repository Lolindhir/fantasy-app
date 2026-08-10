#!/usr/bin/env python3
"""Validate researched Kicker weekly context against its deterministic research plan."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema


class KickerWeeklyContextValidationError(RuntimeError):
    """Raised when weekly Kicker context is not safe for the requested use."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KickerWeeklyContextValidationError(f"Could not load JSON from {path}: {exc}") from exc


def parse_datetime(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise KickerWeeklyContextValidationError(f"{label} must be a date-time string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise KickerWeeklyContextValidationError(f"{label} is not a valid date-time") from exc
    if parsed.tzinfo is None:
        raise KickerWeeklyContextValidationError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def age_hours(checked_at: datetime, evidence_at: datetime, label: str) -> float:
    age = (checked_at - evidence_at).total_seconds() / 3600.0
    if age < -1e-6:
        raise KickerWeeklyContextValidationError(f"{label} is dated after context checked_at")
    return age


def validate_schema(context: dict[str, Any], schema: dict[str, Any]) -> None:
    try:
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(context)
    except jsonschema.ValidationError as exc:
        raise KickerWeeklyContextValidationError(f"Weekly context schema validation failed: {exc.message}") from exc


def validate_context(
    context: dict[str, Any],
    research_plan: dict[str, Any],
    research_config: dict[str, Any],
    schema: dict[str, Any],
    *,
    require_decision_ready: bool = False,
) -> dict[str, Any]:
    validate_schema(context, schema)

    if research_plan.get("schema_version") != 1 or research_plan.get("dataset_id") != "kicker-weekly-research-plan":
        raise KickerWeeklyContextValidationError("Unexpected Kicker weekly research-plan identity")
    if research_config.get("schema_version") != 1 or research_config.get("research_id") != "kicker-weekly-context":
        raise KickerWeeklyContextValidationError("Unexpected Kicker weekly research config identity")

    plan_fingerprint = research_plan.get("input_fingerprint")
    if context.get("research_plan_fingerprint") != plan_fingerprint:
        raise KickerWeeklyContextValidationError("Weekly context does not match the current research-plan fingerprint")
    if context.get("source_input_fingerprint") != research_plan.get("source_input_fingerprint"):
        raise KickerWeeklyContextValidationError("Weekly context does not match the Kicker input fingerprint used by the research plan")
    if str(context.get("season")) != str(research_plan.get("season")) or int(context.get("week", -1)) != int(research_plan.get("week", -2)):
        raise KickerWeeklyContextValidationError("Weekly context season/week does not match the research plan")

    context_status = context.get("context_status")
    if context_status not in {"preliminary", "decision_ready"}:
        raise KickerWeeklyContextValidationError("Weekly context requires context_status preliminary or decision_ready")
    if require_decision_ready and context_status != "decision_ready":
        raise KickerWeeklyContextValidationError("Kicker recommendation requires a decision_ready weekly context")

    plan_candidates = {
        str(candidate.get("player_id")): candidate
        for candidate in research_plan.get("candidates", [])
        if isinstance(candidate, dict)
    }
    held_ids = {
        player_id
        for player_id, candidate in plan_candidates.items()
        if candidate.get("availability") == "held"
    }
    context_players = context.get("players") if isinstance(context.get("players"), list) else []
    context_ids: set[str] = set()
    for player in context_players:
        player_id = str(player.get("player_id"))
        if player_id not in plan_candidates:
            raise KickerWeeklyContextValidationError(f"Weekly context contains player outside research plan: {player_id}")
        if player_id in context_ids:
            raise KickerWeeklyContextValidationError(f"Weekly context contains duplicate player: {player_id}")
        context_ids.add(player_id)

    if not held_ids.issubset(context_ids):
        raise KickerWeeklyContextValidationError("Weekly context must include every held Kicker from the research plan")
    if require_decision_ready and not any(
        plan_candidates[player_id].get("availability") == "free_agent" for player_id in context_ids
    ):
        raise KickerWeeklyContextValidationError("Decision-ready context requires at least one researched free-agent alternative")

    checked_at = parse_datetime(context.get("checked_at"), "checked_at")
    policy = research_config.get("research") if isinstance(research_config.get("research"), dict) else {}
    max_before = float(policy.get("decision_ready_max_hours_before_kickoff", 168))
    weather_max = float(policy.get("weather_max_age_hours", 24))
    job_max = float(policy.get("job_security_max_age_hours", 24))
    player_injury_max = float(policy.get("player_injury_max_age_hours", 24))
    qb_injury_max = float(policy.get("qb_injury_max_age_hours", 24))
    venue_max = float(policy.get("venue_max_age_hours", 168))

    scheduled_count = 0
    for player in context_players:
        player_id = str(player["player_id"])
        plan_candidate = plan_candidates[player_id]
        schedule = plan_candidate.get("schedule") if isinstance(plan_candidate.get("schedule"), dict) else {}
        schedule_status = schedule.get("status")

        if schedule_status == "bye":
            if context_status == "decision_ready":
                raise KickerWeeklyContextValidationError(
                    f"Decision-ready context cannot score bye-week candidate {player_id}; held-bye recommendation support is a separate engine case"
                )
            continue
        if schedule_status != "scheduled":
            raise KickerWeeklyContextValidationError(f"Research plan has unsupported schedule status for {player_id}")
        scheduled_count += 1

        if player.get("game_id") != schedule.get("game_id"):
            raise KickerWeeklyContextValidationError(f"Weekly context game_id mismatch for {player_id}")

        if context_status != "decision_ready":
            continue

        kickoff_epoch = schedule.get("kickoff_epoch")
        if isinstance(kickoff_epoch, bool) or not isinstance(kickoff_epoch, (int, float)):
            raise KickerWeeklyContextValidationError(f"Scheduled candidate {player_id} is missing kickoff_epoch")
        kickoff = datetime.fromtimestamp(float(kickoff_epoch), tz=timezone.utc)
        hours_before = (kickoff - checked_at).total_seconds() / 3600.0
        if hours_before < 0:
            raise KickerWeeklyContextValidationError(f"Decision context for {player_id} is after kickoff")
        if hours_before > max_before:
            raise KickerWeeklyContextValidationError(
                f"Decision context for {player_id} is too early ({hours_before:.1f}h before kickoff; max {max_before:.1f}h)"
            )

        venue = player.get("venue")
        weather = player.get("weather")
        if not isinstance(venue, dict) or not isinstance(weather, dict):
            raise KickerWeeklyContextValidationError(f"Decision-ready context for {player_id} requires structured venue and weather")

        venue_age = age_hours(checked_at, parse_datetime(venue.get("checked_at"), f"{player_id}.venue.checked_at"), f"{player_id}.venue")
        if venue_age > venue_max:
            raise KickerWeeklyContextValidationError(f"Venue evidence for {player_id} is stale")

        job_age = age_hours(checked_at, parse_datetime(player.get("job_security_checked_at"), f"{player_id}.job_security_checked_at"), f"{player_id}.job_security")
        if job_age > job_max:
            raise KickerWeeklyContextValidationError(f"Job-security evidence for {player_id} is stale")

        injury_age = age_hours(checked_at, parse_datetime(player.get("player_injury_checked_at"), f"{player_id}.player_injury_checked_at"), f"{player_id}.player_injury")
        if injury_age > player_injury_max:
            raise KickerWeeklyContextValidationError(f"Player-injury evidence for {player_id} is stale")

        qb_age = age_hours(checked_at, parse_datetime(player.get("qb_injury_checked_at"), f"{player_id}.qb_injury_checked_at"), f"{player_id}.qb_injury")
        if qb_age > qb_injury_max:
            raise KickerWeeklyContextValidationError(f"QB/injury evidence for {player_id} is stale")

        weather_age = age_hours(checked_at, parse_datetime(weather.get("checked_at"), f"{player_id}.weather.checked_at"), f"{player_id}.weather")
        weather_limit = weather_max if weather.get("applicable") is True else venue_max
        if weather_age > weather_limit:
            raise KickerWeeklyContextValidationError(f"Weather/roof evidence for {player_id} is stale")

        exposure = venue.get("weather_exposure")
        if exposure == "exposed" and weather.get("applicable") is not True:
            raise KickerWeeklyContextValidationError(f"Weather-exposed venue for {player_id} requires applicable weather")
        if exposure == "uncertain":
            raise KickerWeeklyContextValidationError(f"Decision-ready venue weather exposure is uncertain for {player_id}")

    return {
        "status": "ok",
        "context_status": context_status,
        "player_count": len(context_players),
        "scheduled_player_count": scheduled_count,
        "research_plan_fingerprint_match": True,
        "source_input_fingerprint_match": True,
        "decision_ready": context_status == "decision_ready",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("context", type=Path)
    parser.add_argument("--research-plan", type=Path, required=True)
    parser.add_argument("--research-config", type=Path, default=Path("fantasy-management/_ai/kicker-weekly-research-config.json"))
    parser.add_argument("--schema", type=Path, default=Path("fantasy-management/_ai/schemas/kicker-weekly-context.schema.json"))
    parser.add_argument("--require-decision-ready", action="store_true")
    args = parser.parse_args()

    context = load_json(args.context)
    plan = load_json(args.research_plan)
    config = load_json(args.research_config)
    schema = load_json(args.schema)
    if not all(isinstance(value, dict) for value in (context, plan, config, schema)):
        raise KickerWeeklyContextValidationError("Context, plan, config and schema must be JSON objects")
    result = validate_context(
        context,
        plan,
        config,
        schema,
        require_decision_ready=args.require_decision_ready,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
