"""Sleeper-keyed view of the persisted PlayerWeekFantasy product (Shared Derived, product-neutral; Issue #1263 CP2, finding F2).

The Shared Derived PlayerWeekFantasy product is keyed by CanonicalPlayerID. The league provider (Sleeper) addresses players by its own
player ID, so every consumer that joins PlayerWeekFantasy to league facts (FantasyGameContext starters, MatchupProjections, the App
delivery) needs the same canonical -> Sleeper bridge. This module owns that bridge and the in-memory view so that the Shared Derived
matchup-context materializer and the App publisher share one implementation instead of one importing the other's adapter.
Nothing is written here; ``tools/player_week_fantasy_app_publish.py`` renders the App delivery file from this view.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT
from player_week_fantasy import CONTRACT_VERSION, build_player_week_fantasy_contract

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


def normalize_source_contract(source: Mapping[str, Any]) -> dict[str, Any]:
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


def build_identity_bridge(
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


def build_sleeper_keyed_view(
    source: Mapping[str, Any],
    identity_payload: Mapping[str, Any],
    sleeper_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """One week of PlayerWeekFantasy with the canonical Sleeper player ID per record (PlayerID is None when unmapped)."""
    normalized = normalize_source_contract(source)
    identity_bridge = build_identity_bridge(identity_payload, sleeper_payload)

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


def load_sleeper_keyed_view(
    repo_root: Path,
    canonical_league_id: str,
    season: int,
    week: int,
) -> dict[str, Any]:
    """In-memory Sleeper-keyed view of the persisted PlayerWeekFantasy product of one week; writes nothing."""
    canonical_league_id = _text(canonical_league_id, "CanonicalLeagueID")
    season = _positive_int(season, "Season")
    week = _positive_int(week, "Week")

    source_path = (
        repo_root
        / DATA_DERIVED_ROOT
        / "player-week-fantasy"
        / canonical_league_id
        / str(season)
        / f"{week:02d}.json"
    )
    identity_path = repo_root / DATA_SOURCE_ROOT / "nfl" / "identities" / "players.json"
    sleeper_path = repo_root / DATA_SOURCE_ROOT / "nfl" / "platform" / "sleeper" / "players.json"

    view = build_sleeper_keyed_view(
        _read_json(source_path),
        _read_json(identity_path),
        _read_json(sleeper_path),
    )
    if view["CanonicalLeagueID"] != canonical_league_id:
        raise ValueError(
            "PlayerWeekFantasy league mismatch: "
            f"requested={canonical_league_id} source={view['CanonicalLeagueID']}"
        )
    if view["Season"] != season or view["Week"] != week:
        raise ValueError(
            "PlayerWeekFantasy target mismatch: "
            f"requested={season}/W{week} source={view['Season']}/W{view['Week']}"
        )
    return view
