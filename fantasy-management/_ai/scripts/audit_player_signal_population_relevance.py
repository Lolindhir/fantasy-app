#!/usr/bin/env python3
"""Audit candidate replacements for the legacy player-signal population bridge.

Checkpoint 6Z.2 is analysis-only. The productive builder still uses
Players.json -> TeamAbbr as the explicit has_nfl_team compatibility bridge.
This tool compares that baseline with structured NFL-membership and fantasy-
relevance signals without changing any generated runtime contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_fantasy_operations_inputs as ops  # noqa: E402
import build_player_signal_dataset as player_signals  # noqa: E402

SCHEMA_VERSION = 1
AUDIT_ID = "player-signal-population-relevance"
LEGACY_BRIDGE_REASON = "has_nfl_team"

DOWNSTREAM_DATASETS = {
    "free_agent_signals": (
        "fantasy-management/generated/operations/free-agent-signals.json",
        "players",
    ),
    "fa_board": (
        "fantasy-management/generated/operations/fa-board-readmodel.json",
        "players",
    ),
    "free_agent_movement": (
        "fantasy-management/generated/operations/free-agent-movement-signals.json",
        "discoveries",
    ),
    "free_agent_movement_events": (
        "fantasy-management/generated/operations/free-agent-movement-events.json",
        "events",
    ),
    "kicker_streaming": (
        "fantasy-management/generated/operations/kicker-streaming-inputs.json",
        "candidates",
    ),
    "managed_roster": (
        "fantasy-management/generated/operations/managed-roster-signals.json",
        "players",
    ),
}


class PopulationRelevanceAuditError(RuntimeError):
    """Raised when the population-relevance audit cannot be evaluated safely."""


def boolean_bucket(value: bool | None) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "null"


def load_roster_membership(
    root: Path,
    relative_path: str,
    *,
    expected_season: int,
    expected_week: int | None = None,
) -> tuple[set[str], dict[str, Any]]:
    path = root / relative_path
    document = ops.load_json(path)
    if not isinstance(document, dict):
        raise PopulationRelevanceAuditError(f"{relative_path} must be a JSON object")
    if int(document.get("Season") or -1) != expected_season:
        raise PopulationRelevanceAuditError(
            f"{relative_path} season does not match expected {expected_season}"
        )
    if expected_week is not None and int(document.get("Week") or -1) != expected_week:
        raise PopulationRelevanceAuditError(
            f"{relative_path} week does not match expected {expected_week}"
        )
    records = document.get("Records")
    if not isinstance(records, list):
        raise PopulationRelevanceAuditError(f"{relative_path} Records must be an array")

    members: set[str] = set()
    for row in records:
        if not isinstance(row, dict):
            continue
        canonical_player_id = ops.optional_text(row.get("CanonicalPlayerID"))
        if canonical_player_id:
            members.add(canonical_player_id)

    return members, {
        "path": relative_path,
        "record_count": len(records),
        "resolved_player_count": len(members),
        "finalized": bool(document.get("Finalized")),
    }


def latest_weekly_roster_path(root: Path, season: int) -> tuple[str, int]:
    directory = root / f"source-data/nfl/weekly-rosters/{season}"
    if not directory.exists():
        raise PopulationRelevanceAuditError(
            f"Canonical weekly roster directory is missing for season {season}"
        )

    candidates: list[tuple[int, Path]] = []
    for path in directory.glob("*.json"):
        try:
            week = int(path.stem)
        except ValueError:
            continue
        candidates.append((week, path))

    if not candidates:
        raise PopulationRelevanceAuditError(
            f"No canonical weekly roster partitions found for season {season}"
        )

    week, path = max(candidates, key=lambda item: item[0])
    return path.relative_to(root).as_posix(), week


def downstream_player_ids(document: dict[str, Any], collection_key: str) -> set[str]:
    rows = document.get(collection_key)
    if not isinstance(rows, list):
        raise PopulationRelevanceAuditError(
            f"Downstream collection {collection_key} must be an array"
        )
    ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("player_id") is None:
            continue
        ids.add(str(row["player_id"]))
    return ids


def counter_dict(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def evaluate_policy(
    candidates: dict[str, dict[str, Any]],
    baseline_ids: set[str],
    predicate: Callable[[dict[str, Any]], bool],
) -> dict[str, Any]:
    included_ids: set[str] = set()
    for player_id, candidate in candidates.items():
        if candidate["non_bridge_reasons"] or predicate(candidate):
            included_ids.add(player_id)

    removed_ids = sorted(baseline_ids - included_ids)
    added_ids = sorted(included_ids - baseline_ids)
    return {
        "player_count": len(included_ids),
        "delta": len(included_ids) - len(baseline_ids),
        "removed_count": len(removed_ids),
        "removed_player_ids": removed_ids,
        "added_count": len(added_ids),
        "added_player_ids": added_ids,
    }


def build(root: Path, config_path: Path, *, include_details: bool = False) -> dict[str, Any]:
    config = ops.load_json(config_path)
    baseline = player_signals.build(root, config_path)
    sources = config["sources"]

    legacy_players = ops.load_json(root / sources["players"])
    canonical_identities = ops.load_json(root / sources["canonical_player_identities"])
    canonical_sleeper_players = ops.load_json(root / sources["canonical_sleeper_players"])
    if not isinstance(legacy_players, list):
        raise PopulationRelevanceAuditError("Players input must be a JSON array")

    try:
        identity_by_sleeper = ops.build_canonical_identity_by_sleeper(canonical_identities)
        sleeper_player_lookup = ops.build_canonical_sleeper_player_lookup(
            canonical_sleeper_players,
            identity_by_sleeper,
        )
    except ops.MaterializationError as exc:
        raise PopulationRelevanceAuditError(
            f"Canonical player identity/platform inputs are invalid: {exc}"
        ) from exc

    canonical_league_id = ops.optional_text(
        (config.get("canonical_league") or {}).get("canonical_league_id")
    )
    if not canonical_league_id:
        raise PopulationRelevanceAuditError(
            "canonical_league.canonical_league_id is required"
        )
    try:
        season = player_signals.resolve_current_canonical_season(
            root,
            canonical_league_id=canonical_league_id,
        )
    except Exception as exc:  # CanonicalOwnershipError is intentionally wrapped here.
        raise PopulationRelevanceAuditError(
            f"Current canonical league season cannot be resolved: {exc}"
        ) from exc

    current_season_path = f"source-data/nfl/rosters/{season}.json"
    current_season_members, current_season_source = load_roster_membership(
        root,
        current_season_path,
        expected_season=season,
    )

    previous_season = season - 1
    previous_season_path = f"source-data/nfl/rosters/{previous_season}.json"
    previous_season_members, previous_season_source = load_roster_membership(
        root,
        previous_season_path,
        expected_season=previous_season,
    )

    weekly_path, latest_week = latest_weekly_roster_path(root, season)
    weekly_members, weekly_source = load_roster_membership(
        root,
        weekly_path,
        expected_season=season,
        expected_week=latest_week,
    )
    weekly_source["week"] = latest_week

    baseline_by_id = {
        str(player["player_id"]): player
        for player in baseline.get("players") or []
        if isinstance(player, dict) and player.get("player_id") is not None
    }
    baseline_ids = set(baseline_by_id)
    allowed_positions = {
        str(position).upper() for position in config["population"]["positions"]
    }

    candidates: dict[str, dict[str, Any]] = {}
    for legacy_player in legacy_players:
        if not isinstance(legacy_player, dict) or legacy_player.get("ID") is None:
            continue
        player_id = str(legacy_player["ID"])
        try:
            player, identity, sleeper_player = player_signals.canonical_player_context(
                player_id,
                legacy_player,
                identity_by_sleeper,
                sleeper_player_lookup,
            )
        except player_signals.PlayerSignalMaterializationError:
            raise

        position = str(player.get("Position") or "").upper()
        if position not in allowed_positions:
            continue

        canonical_player_id = ops.optional_text(identity.get("CanonicalPlayerID"))
        baseline_player = baseline_by_id.get(player_id)
        baseline_reasons = sorted(
            str(reason)
            for reason in (baseline_player or {}).get("population_reasons") or []
        )
        non_bridge_reasons = [
            reason for reason in baseline_reasons if reason != LEGACY_BRIDGE_REASON
        ]

        candidates[player_id] = {
            "player_id": player_id,
            "canonical_player_id": canonical_player_id,
            "name": ops.optional_text(player.get("Name")),
            "position": position,
            "baseline_reasons": baseline_reasons,
            "non_bridge_reasons": non_bridge_reasons,
            "canonical_sleeper_team": ops.optional_text(sleeper_player.get("Team")),
            "sleeper_status": ops.optional_text(sleeper_player.get("Status")),
            "tank01_is_free_agent": ops.optional_bool(legacy_player.get("IsFreeAgent")),
            "current_week_nfl_member": bool(
                canonical_player_id and canonical_player_id in weekly_members
            ),
            "current_season_nfl_history": bool(
                canonical_player_id and canonical_player_id in current_season_members
            ),
            "previous_season_nfl_history": bool(
                canonical_player_id and canonical_player_id in previous_season_members
            ),
        }

    recent_history_members = current_season_members | previous_season_members

    policies = {
        "canonical_sleeper_team": evaluate_policy(
            candidates,
            baseline_ids,
            lambda candidate: bool(candidate["canonical_sleeper_team"]),
        ),
        "latest_weekly_nfl_membership": evaluate_policy(
            candidates,
            baseline_ids,
            lambda candidate: candidate["current_week_nfl_member"],
        ),
        "current_season_nfl_history": evaluate_policy(
            candidates,
            baseline_ids,
            lambda candidate: candidate["current_season_nfl_history"],
        ),
        "current_plus_previous_season_nfl_history": evaluate_policy(
            candidates,
            baseline_ids,
            lambda candidate: bool(
                candidate["canonical_player_id"]
                and candidate["canonical_player_id"] in recent_history_members
            ),
        ),
        "current_season_or_tank01_not_free_agent": evaluate_policy(
            candidates,
            baseline_ids,
            lambda candidate: (
                candidate["current_season_nfl_history"]
                or candidate["tank01_is_free_agent"] is False
            ),
        ),
    }

    bridge_only = [
        candidate
        for candidate in candidates.values()
        if candidate["baseline_reasons"] == [LEGACY_BRIDGE_REASON]
    ]

    reason_sets = Counter(
        "|".join(sorted(player.get("population_reasons") or []))
        for player in baseline_by_id.values()
    )

    downstream_documents: dict[str, tuple[set[str], int]] = {}
    for dataset_id, (relative_path, collection_key) in DOWNSTREAM_DATASETS.items():
        document = ops.load_json(root / relative_path)
        if not isinstance(document, dict):
            raise PopulationRelevanceAuditError(
                f"{relative_path} must be a JSON object"
            )
        ids = downstream_player_ids(document, collection_key)
        downstream_documents[dataset_id] = (ids, len(ids))

    for policy in policies.values():
        removed = set(policy["removed_player_ids"])
        impacts: dict[str, Any] = {}
        for dataset_id, (ids, current_count) in downstream_documents.items():
            affected = sorted(ids & removed)
            impacts[dataset_id] = {
                "current_player_count": current_count,
                "removed_count": len(affected),
                "projected_player_count_after_removals": current_count - len(affected),
                "removed_player_ids": affected,
            }
        policy["downstream"] = impacts

        removed_rows = [
            candidates[player_id]
            for player_id in policy["removed_player_ids"]
            if player_id in candidates
        ]
        policy["removed_evidence"] = {
            "positions": counter_dict([row["position"] for row in removed_rows]),
            "tank01_is_free_agent": counter_dict(
                [boolean_bucket(row["tank01_is_free_agent"]) for row in removed_rows]
            ),
            "sleeper_status": counter_dict(
                [row["sleeper_status"] or "null" for row in removed_rows]
            ),
            "canonical_sleeper_team_present": counter_dict(
                ["true" if row["canonical_sleeper_team"] else "false" for row in removed_rows]
            ),
        }

    current_season_removed = [
        candidates[player_id]
        for player_id in policies["current_season_nfl_history"]["removed_player_ids"]
        if player_id in candidates
    ]
    current_plus_previous_removed = [
        candidates[player_id]
        for player_id in policies[
            "current_plus_previous_season_nfl_history"
        ]["removed_player_ids"]
        if player_id in candidates
    ]

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "audit_id": AUDIT_ID,
        "baseline": {
            "dataset_id": baseline.get("dataset_id"),
            "generated_at": baseline.get("generated_at"),
            "input_fingerprint": baseline.get("input_fingerprint"),
            "player_count": len(baseline_ids),
            "reason_counts": (baseline.get("population") or {}).get("reason_counts"),
            "exact_reason_sets": dict(sorted(reason_sets.items())),
        },
        "canonical_nfl_roster_sources": {
            "current_season": current_season_source,
            "latest_weekly": weekly_source,
            "previous_season": previous_season_source,
        },
        "signal_roles": {
            "league_owned": {
                "population_role": "hard_include",
                "semantics": "current fantasy-league ownership",
            },
            "listed_in_external_source": {
                "population_role": "fantasy_relevance",
                "semantics": "current normalized ranking/projection listing, not NFL contract evidence",
            },
            "present_in_external_signal": {
                "population_role": "fantasy_relevance",
                "semantics": "current external activity signal, not NFL contract evidence",
            },
            "canonical_weekly_nfl_roster": {
                "population_role": "current_nfl_membership",
                "semantics": "primary canonical in-season NFL membership snapshot",
            },
            "canonical_season_nfl_roster": {
                "population_role": "recent_nfl_history",
                "semantics": "current-season NFL roster history, not proof of present-week membership",
            },
            "canonical_previous_season_nfl_roster": {
                "population_role": "bounded_recent_nfl_history_candidate",
                "semantics": "previous-season NFL roster history retained only as a relevance window",
            },
            "tank01_is_free_agent": {
                "population_role": "diagnostic_secondary_evidence",
                "semantics": "legacy structured NFL free-agent signal; not canonical membership truth",
            },
            "canonical_sleeper_team": {
                "population_role": "context_only",
                "semantics": "Sleeper platform team fact; not NFL contract truth",
            },
            "sleeper_status": {
                "population_role": "context_only",
                "semantics": "Sleeper platform status; Active/Inactive is not NFL contract truth",
            },
            "nfl_contracts": {
                "population_role": "unavailable",
                "semantics": "durable canonical contract primary is unresolved and not activated",
            },
        },
        "summary": {
            "eligible_candidate_count": len(candidates),
            "bridge_only_count": len(bridge_only),
            "bridge_only": {
                "positions": counter_dict([row["position"] for row in bridge_only]),
                "canonical_sleeper_team_present": counter_dict(
                    ["true" if row["canonical_sleeper_team"] else "false" for row in bridge_only]
                ),
                "tank01_is_free_agent": counter_dict(
                    [boolean_bucket(row["tank01_is_free_agent"]) for row in bridge_only]
                ),
                "sleeper_status": counter_dict(
                    [row["sleeper_status"] or "null" for row in bridge_only]
                ),
                "current_week_nfl_member": counter_dict(
                    ["true" if row["current_week_nfl_member"] else "false" for row in bridge_only]
                ),
                "current_season_nfl_history": counter_dict(
                    ["true" if row["current_season_nfl_history"] else "false" for row in bridge_only]
                ),
                "previous_season_nfl_history": counter_dict(
                    ["true" if row["previous_season_nfl_history"] else "false" for row in bridge_only]
                ),
            },
            "current_season_source_disagreement": {
                "removed_count": len(current_season_removed),
                "tank01_not_free_agent_count": sum(
                    row["tank01_is_free_agent"] is False
                    for row in current_season_removed
                ),
                "sleeper_team_present_count": sum(
                    bool(row["canonical_sleeper_team"])
                    for row in current_season_removed
                ),
            },
            "current_plus_previous_source_disagreement": {
                "removed_count": len(current_plus_previous_removed),
                "tank01_not_free_agent_count": sum(
                    row["tank01_is_free_agent"] is False
                    for row in current_plus_previous_removed
                ),
                "sleeper_team_present_count": sum(
                    bool(row["canonical_sleeper_team"])
                    for row in current_plus_previous_removed
                ),
            },
            "policies": policies,
        },
    }

    if include_details:
        result["details"] = {
            "bridge_only_players": sorted(
                bridge_only,
                key=lambda row: (row["position"], (row["name"] or "").casefold(), row["player_id"]),
            ),
            "current_season_removed_players": sorted(
                current_season_removed,
                key=lambda row: (row["position"], (row["name"] or "").casefold(), row["player_id"]),
            ),
            "current_plus_previous_removed_players": sorted(
                current_plus_previous_removed,
                key=lambda row: (row["position"], (row["name"] or "").casefold(), row["player_id"]),
            ),
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("fantasy-management/automation/player-signal-materialization.json"),
    )
    parser.add_argument("--details", action="store_true", help="Include per-player audit rows")
    args = parser.parse_args()

    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    print(
        json.dumps(
            build(root, config_path, include_details=args.details),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
