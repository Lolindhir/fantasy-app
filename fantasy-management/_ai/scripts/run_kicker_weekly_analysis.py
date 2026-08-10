#!/usr/bin/env python3
"""Run Kicker Streaming weekly analysis only after research-context validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import analyze_kicker_streaming
import validate_kicker_weekly_context


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


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
