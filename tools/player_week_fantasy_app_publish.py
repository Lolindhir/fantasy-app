#!/usr/bin/env python3
"""Publish Shared-Derived PlayerWeekFantasy into the App delivery layer."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping

from player_week_fantasy import (
    CONTRACT_VERSION,
    DISPLAY_INTERVAL_LEVEL,
    build_player_week_fantasy_contract,
)
from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT
from derived_data_lib.player_week_fantasy_view import (  # noqa: F401
    IDENTITY_PROVIDER,
    _positive_int,
    _read_json,
    _text,
    build_identity_bridge as _build_identity_bridge,
    build_sleeper_keyed_view,
    load_sleeper_keyed_view,
    normalize_source_contract as _normalize_source_contract,
)

APP_SCHEMA_VERSION = 1


RANGE_AXIS_STEP = 5


def _range_axis(records: list[dict[str, Any]], level: float) -> dict[str, int] | None:
    """Shared player-range scale at the display level, snapped outward to the step."""

    lowers: list[float] = []
    uppers: list[float] = []
    for record in records:
        for item in record["Projection"].get("PredictionRanges", []):
            if item["Level"] == level:
                lowers.append(item["Lower"])
                uppers.append(item["Upper"])
    if not lowers:
        return None
    return {
        "Min": math.floor(min(lowers) / RANGE_AXIS_STEP) * RANGE_AXIS_STEP,
        "Max": math.ceil(max(uppers) / RANGE_AXIS_STEP) * RANGE_AXIS_STEP,
    }


def build_app_player_week_fantasy_read_model(
    source: Mapping[str, Any],
    identity_payload: Mapping[str, Any],
    sleeper_payload: Mapping[str, Any],
) -> dict[str, Any]:
    return build_app_player_week_fantasy_read_model_from_view(
        build_sleeper_keyed_view(source, identity_payload, sleeper_payload)
    )


def write_json_if_changed(path: Path, payload: Mapping[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def load_app_player_week_fantasy(
    repo_root: Path,
    canonical_league_id: str,
    season: int,
    week: int,
) -> dict[str, Any]:
    """In-memory App adaptation of the persisted PlayerWeekFantasy product of one week; writes nothing."""
    view = load_sleeper_keyed_view(repo_root, canonical_league_id, season, week)
    return build_app_player_week_fantasy_read_model_from_view(view)


def build_app_player_week_fantasy_read_model_from_view(view: Mapping[str, Any]) -> dict[str, Any]:
    records = view["Records"]
    return {
        "SchemaVersion": APP_SCHEMA_VERSION,
        **{key: view[key] for key in ("CanonicalLeagueID", "Season", "Week", "ScoringProfile", "IdentityCoverage")},
        "Display": {
            "RangeLevel": DISPLAY_INTERVAL_LEVEL,
            "RangeAxis": _range_axis(records, DISPLAY_INTERVAL_LEVEL),
        },
        "Records": records,
    }


def materialize_app_player_week_fantasy(
    repo_root: Path,
    canonical_league_id: str,
    season: int,
    week: int,
    *,
    output_path: Path | None = None,
) -> tuple[dict[str, Any], bool]:
    payload = load_app_player_week_fantasy(repo_root, canonical_league_id, season, week)
    target_path = output_path or (repo_root / "public" / "data" / "PlayerWeekFantasy.json")
    changed = write_json_if_changed(target_path, payload)
    return payload, changed


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish PlayerWeekFantasy into public/data with the canonical Sleeper app identity bridge."
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", required=True, dest="canonical_league_id")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = args.repo_root.resolve()
    output = args.output
    if output is not None and not output.is_absolute():
        output = repo_root / output

    payload, changed = materialize_app_player_week_fantasy(
        repo_root,
        args.canonical_league_id,
        args.season,
        args.week,
        output_path=output,
    )
    coverage = payload["IdentityCoverage"]
    print(
        json.dumps(
            {
                "CanonicalLeagueID": payload["CanonicalLeagueID"],
                "Season": payload["Season"],
                "Week": payload["Week"],
                "RecordCount": len(payload["Records"]),
                "ResolvedRecordCount": coverage["ResolvedRecordCount"],
                "UnavailableRecordCount": coverage["UnavailableRecordCount"],
                "Changed": changed,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
