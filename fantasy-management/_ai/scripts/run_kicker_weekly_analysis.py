#!/usr/bin/env python3
"""Run Kicker Streaming weekly analysis only after research-context validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import analyze_kicker_streaming
import validate_kicker_weekly_context


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def held_bye_candidate(plan: dict[str, Any]) -> dict[str, Any] | None:
    held = [
        candidate
        for candidate in plan.get("candidates", [])
        if isinstance(candidate, dict) and candidate.get("availability") == "held"
    ]
    if len(held) != 1:
        return None
    schedule = held[0].get("schedule") if isinstance(held[0].get("schedule"), dict) else {}
    return held[0] if schedule.get("status") == "bye" else None


def apply_held_bye_recommendation(
    analysis: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    held_bye = held_bye_candidate(plan)
    if held_bye is None:
        return analysis

    held_player_id = str(held_bye.get("player_id"))
    held_row = next(
        (
            row
            for row in analysis.get("ranking", [])
            if isinstance(row, dict)
            and row.get("availability") == "held"
            and str(row.get("player_id")) == held_player_id
        ),
        None,
    )
    if held_row is None:
        analysis["recommendation"] = {
            "status": "insufficient_context",
            "held_player_id": held_player_id,
            "target_player_id": None,
            "score_delta": None,
            "reason_codes": ["held_bye_player_missing_from_analysis"],
            "summary": "Der gehaltene Bye-Kicker konnte nicht eindeutig mit dem Analysebestand abgeglichen werden.",
        }
        return analysis

    alternatives = [
        row
        for row in analysis.get("ranking", [])
        if isinstance(row, dict)
        and row.get("availability") == "free_agent"
        and isinstance(row.get("weekly"), dict)
        and row["weekly"].get("eligible") is True
        and isinstance(row["weekly"].get("final_score"), (int, float))
        and not isinstance(row["weekly"].get("final_score"), bool)
    ]
    alternatives.sort(
        key=lambda row: (
            -float(row["weekly"]["final_score"]),
            str(row.get("name") or "").casefold(),
            str(row.get("player_id")),
        )
    )

    held_name = held_row.get("name") or held_player_id
    if not alternatives:
        analysis["recommendation"] = {
            "status": "insufficient_context",
            "held_player_id": held_player_id,
            "target_player_id": None,
            "score_delta": None,
            "reason_codes": ["held_kicker_bye_week", "no_eligible_free_agent_weekly_context"],
            "summary": (
                f"{held_name} hat in dieser Woche Bye. Es ist noch keine vollständig verifizierte, "
                "spielende Free-Agent-Alternative für einen Wochen-Stream verfügbar."
            ),
        }
        return analysis

    best = alternatives[0]
    target_player_id = str(best.get("player_id"))
    target_name = best.get("name") or target_player_id
    analysis["recommendation"] = {
        "status": "switch_recommended",
        "held_player_id": held_player_id,
        "target_player_id": target_player_id,
        "score_delta": None,
        "reason_codes": ["held_kicker_bye_week", "best_verified_free_agent_selected"],
        "summary": (
            f"Für die Bye-Woche von {held_name} wird {target_name} als beste verifizierte, spielende "
            "Free-Agent-Alternative empfohlen. Das ist eine Wochen-Streaming-Empfehlung; die Bye-Woche "
            f"wird nicht als Job- oder Injury-Problem von {held_name} gewertet."
        ),
    }
    return analysis


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--weekly-context", type=Path, required=True)
    parser.add_argument("--research-plan", type=Path, required=True)
    parser.add_argument("--analysis-config", type=Path, default=Path("fantasy-management/_ai/kicker-streaming-analysis-config.json"))
    parser.add_argument("--research-config", type=Path, default=Path("fantasy-management/_ai/kicker-weekly-research-config.json"))
    parser.add_argument("--context-schema", type=Path, default=Path("fantasy-management/_ai/schemas/kicker-weekly-context.schema.json"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    root = args.root.resolve()
    context_path = resolve(root, args.weekly_context)
    plan_path = resolve(root, args.research_plan)
    analysis_config_path = resolve(root, args.analysis_config)
    research_config_path = resolve(root, args.research_config)
    context_schema_path = resolve(root, args.context_schema)

    context = validate_kicker_weekly_context.load_json(context_path)
    plan = validate_kicker_weekly_context.load_json(plan_path)
    research_config = validate_kicker_weekly_context.load_json(research_config_path)
    context_schema = validate_kicker_weekly_context.load_json(context_schema_path)
    validation = validate_kicker_weekly_context.validate_context(
        context,
        plan,
        research_config,
        context_schema,
        require_decision_ready=True,
    )

    analysis = analyze_kicker_streaming.build(root, analysis_config_path, context_path)
    analysis = apply_held_bye_recommendation(analysis, plan)
    payload = {
        "weekly_context_validation": validation,
        "analysis": analysis,
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        output_path = resolve(root, args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
