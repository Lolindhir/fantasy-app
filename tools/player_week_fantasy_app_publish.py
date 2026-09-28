#!/usr/bin/env python3
"""Publish Shared-Derived PlayerWeekFantasy into the App delivery layer."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from player_week_fantasy import (
    CONTRACT_VERSION,
    build_player_week_fantasy_contract,
)

APP_SCHEMA_VERSION = 1
IDENTITY_PROVIDER = "Sleeper"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Required PlayerWeekFantasy publication input is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"PlayerWeekFantasy publication input is invalid JSON: {path}") from exc


def _text(value: Any, field: str, *, allow_none: bool = False) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized:
        if allow_none:
            return None
        raise ValueError(f"{field} must be a non-empty string")
    return normalized


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _normalize_source_contract(source: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(source, Mapping):
        raise ValueError("PlayerWeekFantasy source must be an object")
    if source.get("ContractVersion") != CONTRACT_VERSION:
        raise ValueError(
            "Unsupported PlayerWeekFantasy ContractVersion: "
            f"{source.get('ContractVersion')!r}"
        )

    canonical_league_id = _text(
        source.get("CanonicalLeagueID"),
        "PlayerWeekFantasy.CanonicalLeagueID",
    )
    season = _positive_int(source.get("Season"), "PlayerWeekFantasy.Season")
    week = _positive_int(source.get("Week"), "PlayerWeekFantasy.Week")

    scoring_profile = source.get("ScoringProfile")
    if not isinstance(scoring_profile, Mapping):
        raise ValueError("PlayerWeekFantasy.ScoringProfile must be an object")
    scoring_profile_with_league = dict(scoring_profile)
    scoring_profile_with_league["CanonicalLeagueID"] = canonical_league_id

    records = source.get("Records")
    if not isinstance(records, list):
        raise ValueError("PlayerWeekFantasy.Records must be an array")

    return build_player_week_fantasy_contract(
        canonical_league_id=canonical_league_id,
        season=season,
        week=week,
        scoring_profile=scoring_profile_with_league,
        records=records,
    )


def _build_identity_bridge(
    identity_payload: Mapping[str, Any],
    sleeper_payload: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(identity_payload, Mapping):
        raise ValueError("Canonical player identity document must be an object")
    identity_rows = identity_payload.get("Players")
    if not isinstance(identity_rows, list):
        raise ValueError("Canonical player identity document must contain Players array")

    canonical_to_sleeper: dict[str, str] = {}
    sleeper_to_canonical: dict[str, str] = {}
    seen_canonical: set[str] = set()

    for index, row in enumerate(identity_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"Canonical identity Players[{index}] must be an object")
        canonical_id = _text(
            row.get("CanonicalPlayerID"),
            f"Canonical identity Players[{index}].CanonicalPlayerID",
        )
        if canonical_id in seen_canonical:
            raise ValueError(f"Duplicate CanonicalPlayerID in identity bridge: {canonical_id}")
        seen_canonical.add(canonical_id)

        ids = row.get("IDs")
        if ids is None:
            ids = {}
        if not isinstance(ids, Mapping):
            raise ValueError(f"Canonical identity {canonical_id} IDs must be an object")

        sleeper_id = _text(
            ids.get("Sleeper"),
            f"Canonical identity {canonical_id} IDs.Sleeper",
            allow_none=True,
        )
        if sleeper_id is None:
            continue

        previous_canonical = sleeper_to_canonical.get(sleeper_id)
        if previous_canonical is not None and previous_canonical != canonical_id:
            raise ValueError(
                "Duplicate active Sleeper identity link: "
                f"{sleeper_id} -> {previous_canonical}, {canonical_id}"
            )
        canonical_to_sleeper[canonical_id] = sleeper_id
        sleeper_to_canonical[sleeper_id] = canonical_id

    if not isinstance(sleeper_payload, Mapping):
        raise ValueError("Canonical Sleeper player document must be an object")
    sleeper_rows = sleeper_payload.get("Records")
    if not isinstance(sleeper_rows, list):
        raise ValueError("Canonical Sleeper player document must contain Records array")

    platform_by_canonical: dict[str, str] = {}
    platform_by_sleeper: dict[str, str | None] = {}

    for index, row in enumerate(sleeper_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"Sleeper Records[{index}] must be an object")
        sleeper_id = _text(
            row.get("SleeperPlayerID"),
            f"Sleeper Records[{index}].SleeperPlayerID",
        )
        canonical_id = _text(
            row.get("CanonicalPlayerID"),
            f"Sleeper Records[{index}].CanonicalPlayerID",
            allow_none=True,
        )

        if sleeper_id in platform_by_sleeper:
            raise ValueError(f"Duplicate SleeperPlayerID in canonical platform data: {sleeper_id}")
        platform_by_sleeper[sleeper_id] = canonical_id

        if canonical_id is None:
            continue
        if canonical_id in platform_by_canonical:
            raise ValueError(
                f"Duplicate CanonicalPlayerID in canonical Sleeper platform data: {canonical_id}"
            )
        platform_by_canonical[canonical_id] = sleeper_id

        identity_sleeper = canonical_to_sleeper.get(canonical_id)
        if identity_sleeper is not None and identity_sleeper != sleeper_id:
            raise ValueError(
                "Canonical/Sleeper identity disagreement for "
                f"{canonical_id}: identity={identity_sleeper} platform={sleeper_id}"
            )

        identity_canonical = sleeper_to_canonical.get(sleeper_id)
        if identity_canonical is not None and identity_canonical != canonical_id:
            raise ValueError(
                "Canonical/Sleeper identity disagreement for "
                f"SleeperPlayerID {sleeper_id}: identity={identity_canonical} "
                f"platform={canonical_id}"
            )

    return canonical_to_sleeper


def build_app_player_week_fantasy_read_model(
    source: Mapping[str, Any],
    identity_payload: Mapping[str, Any],
    sleeper_payload: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _normalize_source_contract(source)
    identity_bridge = _build_identity_bridge(identity_payload, sleeper_payload)

    records: list[dict[str, Any]] = []
    resolved = 0
    unavailable = 0

    for source_record in normalized["Records"]:
        canonical_id = source_record["CanonicalPlayerID"]
        player_id = identity_bridge.get(canonical_id)
        if player_id is None:
            unavailable += 1
        else:
            resolved += 1

        records.append(
            {
                "PlayerID": player_id,
                "CanonicalPlayerID": canonical_id,
                "Projection": source_record["Projection"],
                "Actual": source_record["Actual"],
            }
        )

    return {
        "SchemaVersion": APP_SCHEMA_VERSION,
        "CanonicalLeagueID": normalized["CanonicalLeagueID"],
        "Season": normalized["Season"],
        "Week": normalized["Week"],
        "ScoringProfile": normalized["ScoringProfile"],
        "IdentityCoverage": {
            "Provider": IDENTITY_PROVIDER,
            "ResolvedRecordCount": resolved,
            "UnavailableRecordCount": unavailable,
        },
        "Records": records,
    }


def write_json_if_changed(path: Path, payload: Mapping[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def materialize_app_player_week_fantasy(
    repo_root: Path,
    canonical_league_id: str,
    season: int,
    week: int,
    *,
    output_path: Path | None = None,
) -> tuple[dict[str, Any], bool]:
    canonical_league_id = _text(canonical_league_id, "CanonicalLeagueID")
    season = _positive_int(season, "Season")
    week = _positive_int(week, "Week")

    source_path = (
        repo_root
        / "derived-data"
        / "player-week-fantasy"
        / canonical_league_id
        / str(season)
        / f"{week:02d}.json"
    )
    identity_path = repo_root / "source-data" / "nfl" / "identities" / "players.json"
    sleeper_path = repo_root / "source-data" / "nfl" / "platform" / "sleeper" / "players.json"
    target_path = output_path or (repo_root / "public" / "data" / "PlayerWeekFantasy.json")

    payload = build_app_player_week_fantasy_read_model(
        _read_json(source_path),
        _read_json(identity_path),
        _read_json(sleeper_path),
    )
    if payload["CanonicalLeagueID"] != canonical_league_id:
        raise ValueError(
            "PlayerWeekFantasy publication league mismatch: "
            f"requested={canonical_league_id} source={payload['CanonicalLeagueID']}"
        )
    if payload["Season"] != season or payload["Week"] != week:
        raise ValueError(
            "PlayerWeekFantasy publication target mismatch: "
            f"requested={season}/W{week} source={payload['Season']}/W{payload['Week']}"
        )

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
