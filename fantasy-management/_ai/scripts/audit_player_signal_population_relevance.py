#!/usr/bin/env python3
"""Audit future player-signal population relevance without changing runtime population.

Checkpoint 6Z.2 keeps the productive ``has_nfl_team`` compatibility bridge intact
and evaluates which already-versioned structured facts could replace it later.
The audit deliberately separates:

* fantasy relevance (league ownership, external rankings/projections/market and
  external activity);
* current Sleeper team/status platform facts;
* Tank01 ``IsFreeAgent`` evidence;
* canonical nflverse season and latest-week roster membership.

No candidate contract emitted here is applied by the productive player-signal
builder. The result exists to make later population-cutover deltas reproducible.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_fantasy_operations_inputs as ops  # noqa: E402
import build_player_signal_dataset as player_signals  # noqa: E402
import materialize_external_signals as external_signals  # noqa: E402
from canonical_league_ownership import (  # noqa: E402
    CanonicalOwnershipError,
    build_canonical_ownership_snapshot,
    enrich_canonical_ownership_with_display,
    resolve_current_canonical_season,
)

SCHEMA_VERSION = 1
AUDIT_ID = "player-signal-population-relevance"
BRIDGE_REASON = "has_nfl_team"
FANTASY_RELEVANCE_REASONS = {
    "league_owned",
    "listed_in_external_source",
    "present_in_external_signal",
}
CANDIDATE_CONTRACTS = {
    "canonical_sleeper_team_or_fantasy_relevance": (
        "Current non-bridge fantasy relevance OR Canonical Sleeper Team presence."
    ),
    "tank01_not_free_agent_or_fantasy_relevance": (
        "Current non-bridge fantasy relevance OR Tank01 IsFreeAgent=false."
    ),
    "latest_weekly_roster_or_fantasy_relevance": (
        "Current non-bridge fantasy relevance OR latest canonical nflverse weekly-roster membership."
    ),
    "season_roster_or_fantasy_relevance": (
        "Current non-bridge fantasy relevance OR canonical nflverse current-season roster membership."
    ),
    "weekly_or_season_roster_or_fantasy_relevance": (
        "Current non-bridge fantasy relevance OR latest weekly OR current-season roster membership."
    ),
    "structured_union_or_fantasy_relevance": (
        "Current non-bridge fantasy relevance OR Canonical Sleeper Team OR latest weekly roster "
        "OR current-season roster OR Tank01 IsFreeAgent=false."
    ),
}


class PopulationRelevanceAuditError(RuntimeError):
    """Raised when the population relevance audit cannot be evaluated safely."""


def _records(document: Any, *, source_name: str) -> list[dict[str, Any]]:
    if not isinstance(document, dict):
        raise PopulationRelevanceAuditError(f"{source_name} must be a JSON object")
    records = document.get("Records")
    if not isinstance(records, list):
        raise PopulationRelevanceAuditError(f"{source_name} must contain Records[]")
    if any(not isinstance(row, dict) for row in records):
        raise PopulationRelevanceAuditError(f"{source_name} Records must contain objects")
    return records


def _canonical_id(identity: dict[str, Any]) -> str | None:
    return ops.optional_text(identity.get("CanonicalPlayerID"))


def build_roster_membership_index(
    document: Any,
    identity_by_sleeper: dict[str, dict[str, Any]],
    *,
    source_name: str,
) -> dict[str, set[str]]:
    sleeper_ids: set[str] = set()
    canonical_ids: set[str] = set()

    for row in _records(document, source_name=source_name):
        canonical_id = ops.optional_text(row.get("CanonicalPlayerID"))
        source_ids = row.get("SourceIDs") if isinstance(row.get("SourceIDs"), dict) else {}
        sleeper_id = ops.optional_text(source_ids.get("Sleeper"))

        if canonical_id:
            canonical_ids.add(canonical_id)
        if sleeper_id:
            identity = identity_by_sleeper.get(sleeper_id)
            if identity is None:
                sleeper_ids.add(sleeper_id)
                continue
            identity_canonical_id = _canonical_id(identity)
            if canonical_id and identity_canonical_id and canonical_id != identity_canonical_id:
                raise PopulationRelevanceAuditError(
                    f"{source_name} Sleeper {sleeper_id} maps to {canonical_id}, "
                    f"but Canonical Identity maps it to {identity_canonical_id}"
                )
            sleeper_ids.add(sleeper_id)

    return {"sleeper_ids": sleeper_ids, "canonical_ids": canonical_ids}


def in_roster_membership(
    player_id: str,
    identity: dict[str, Any],
    membership: dict[str, set[str]],
) -> bool:
    canonical_id = _canonical_id(identity)
    return (
        player_id in membership["sleeper_ids"]
        or bool(canonical_id and canonical_id in membership["canonical_ids"])
    )


def resolve_latest_weekly_roster_path(root: Path, season: int) -> tuple[int, Path]:
    directory = root / "source-data" / "nfl" / "weekly-rosters" / str(season)
    if not directory.is_dir():
        raise PopulationRelevanceAuditError(
            f"Canonical weekly-roster directory is missing for season {season}: {directory}"
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
            f"No canonical weekly-roster partitions found for season {season}"
        )
    return max(candidates, key=lambda item: item[0])


def evaluate_contracts(
    *,
    non_bridge_relevant: bool,
    canonical_team_present: bool,
    tank01_is_free_agent: bool | None,
    latest_weekly_roster_member: bool,
    season_roster_member: bool,
) -> dict[str, bool]:
    return {
        "canonical_sleeper_team_or_fantasy_relevance": (
            non_bridge_relevant or canonical_team_present
        ),
        "tank01_not_free_agent_or_fantasy_relevance": (
            non_bridge_relevant or tank01_is_free_agent is False
        ),
        "latest_weekly_roster_or_fantasy_relevance": (
            non_bridge_relevant or latest_weekly_roster_member
        ),
        "season_roster_or_fantasy_relevance": (
            non_bridge_relevant or season_roster_member
        ),
        "weekly_or_season_roster_or_fantasy_relevance": (
            non_bridge_relevant or latest_weekly_roster_member or season_roster_member
        ),
        "structured_union_or_fantasy_relevance": (
            non_bridge_relevant
            or canonical_team_present
            or latest_weekly_roster_member
            or season_roster_member
            or tank01_is_free_agent is False
        ),
    }


def _load_optional_generated(root: Path, relative_path: str, *, list_key: str) -> set[str]:
    path = root / relative_path
    if not path.is_file():
        return set()
    document = ops.load_json(path)
    if not isinstance(document, dict):
        raise PopulationRelevanceAuditError(f"{relative_path} must be a JSON object")
    rows = document.get(list_key)
    if not isinstance(rows, list):
        raise PopulationRelevanceAuditError(f"{relative_path} must contain {list_key}[]")
    return {
        str(row["player_id"])
        for row in rows
        if isinstance(row, dict) and row.get("player_id") is not None
    }


def build(root: Path, config_path: Path, *, include_details: bool = False) -> dict[str, Any]:
    config = ops.load_json(config_path)
    baseline = player_signals.build(root, config_path)
    sources = config["sources"]

    legacy_players = ops.load_json(root / sources["players"])
    canonical_identities = ops.load_json(root / sources["canonical_player_identities"])
    canonical_sleeper_players = ops.load_json(root / sources["canonical_sleeper_players"])
    league_display = ops.load_json(root / sources["league_display"])

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

    canonical_config = config.get("canonical_league") or {}
    canonical_league_id = ops.optional_text(canonical_config.get("canonical_league_id"))
    if not canonical_league_id:
        raise PopulationRelevanceAuditError(
            "canonical_league.canonical_league_id is required"
        )
    try:
        season = resolve_current_canonical_season(
            root,
            canonical_league_id=canonical_league_id,
        )
        ownership_snapshot = build_canonical_ownership_snapshot(
            root,
            canonical_league_id=canonical_league_id,
            season=season,
        )
        ownership_teams = enrich_canonical_ownership_with_display(
            ownership_snapshot,
            league_display,
        )
    except CanonicalOwnershipError as exc:
        raise PopulationRelevanceAuditError(
            f"Canonical league ownership is unavailable: {exc}"
        ) from exc

    managed_team_id = str(config["managed_team"]["team_id"])
    ownership = external_signals.build_ownership(ownership_teams)

    season_roster_path = root / "source-data" / "nfl" / "rosters" / f"{season}.json"
    if not season_roster_path.is_file():
        raise PopulationRelevanceAuditError(
            f"Canonical season roster is missing for {season}: {season_roster_path}"
        )
    latest_week, latest_weekly_path = resolve_latest_weekly_roster_path(root, int(season))

    season_roster = ops.load_json(season_roster_path)
    latest_weekly_roster = ops.load_json(latest_weekly_path)
    season_membership = build_roster_membership_index(
        season_roster,
        identity_by_sleeper,
        source_name=str(season_roster_path.relative_to(root)),
    )
    weekly_membership = build_roster_membership_index(
        latest_weekly_roster,
        identity_by_sleeper,
        source_name=str(latest_weekly_path.relative_to(root)),
    )

    baseline_by_id = {
        str(player["player_id"]): player
        for player in baseline["players"]
    }
    baseline_ids = set(baseline_by_id)
    allowed_positions = {str(value).upper() for value in config["population"]["positions"]}

    generated_movement_ids = _load_optional_generated(
        root,
        "fantasy-management/generated/operations/free-agent-movement-signals.json",
        list_key="discoveries",
    )
    generated_kicker_ids = _load_optional_generated(
        root,
        "fantasy-management/generated/operations/kicker-streaming-inputs.json",
        list_key="candidates",
    )
    generated_managed_ids = _load_optional_generated(
        root,
        "fantasy-management/generated/operations/managed-roster-signals.json",
        list_key="players",
    )

    current_reason_counts: Counter[str] = Counter()
    bridge_only_count = 0
    bridge_only_rows: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []

    contract_ids = {name: set() for name in CANDIDATE_CONTRACTS}
    contract_free_agent_ids = {name: set() for name in CANDIDATE_CONTRACTS}

    eligible_count = 0
    for legacy_player in legacy_players:
        if not isinstance(legacy_player, dict) or legacy_player.get("ID") is None:
            continue

        player_id = str(legacy_player["ID"])
        player, identity, sleeper_player = player_signals.canonical_player_context(
            player_id,
            legacy_player,
            identity_by_sleeper,
            sleeper_player_lookup,
        )

        position = str(player.get("Position") or "").upper()
        if position not in allowed_positions:
            continue
        eligible_count += 1

        baseline_player = baseline_by_id.get(player_id)
        reasons = sorted(str(value) for value in ((baseline_player or {}).get("population_reasons") or []))
        for reason in reasons:
            current_reason_counts[reason] += 1
        reason_set = set(reasons)
        non_bridge_reasons = sorted(reason_set - {BRIDGE_REASON})
        non_bridge_relevant = bool(non_bridge_reasons)

        canonical_team = ops.optional_text(sleeper_player.get("Team"))
        sleeper_status = ops.optional_text(sleeper_player.get("Status"))
        tank01_is_free_agent = ops.optional_bool(legacy_player.get("IsFreeAgent"))
        weekly_member = in_roster_membership(player_id, identity, weekly_membership)
        season_member = in_roster_membership(player_id, identity, season_membership)

        ownership_value = external_signals.ownership_for(
            player_id,
            ownership,
            managed_team_id,
        )
        ownership_status = ops.optional_text(ownership_value.get("status"))
        if ownership_status is None:
            raise PopulationRelevanceAuditError(
                f"Player {player_id} has no canonical fantasy ownership status"
            )

        evaluations = evaluate_contracts(
            non_bridge_relevant=non_bridge_relevant,
            canonical_team_present=bool(canonical_team),
            tank01_is_free_agent=tank01_is_free_agent,
            latest_weekly_roster_member=weekly_member,
            season_roster_member=season_member,
        )
        for name, included in evaluations.items():
            if included:
                contract_ids[name].add(player_id)
                if ownership_status == "fantasy_free_agent":
                    contract_free_agent_ids[name].add(player_id)

        bridge_only = reason_set == {BRIDGE_REASON}
        if bridge_only:
            bridge_only_count += 1
            bridge_only_rows.append(
                {
                    "player_id": player_id,
                    "name": ops.optional_text(identity.get("Name")),
                    "position": position,
                    "canonical_team": canonical_team,
                    "tank01_is_free_agent": tank01_is_free_agent,
                    "sleeper_status": sleeper_status,
                    "latest_weekly_roster_member": weekly_member,
                    "season_roster_member": season_member,
                    "ownership_status": ownership_status,
                }
            )

        if include_details:
            all_rows.append(
                {
                    "player_id": player_id,
                    "name": ops.optional_text(identity.get("Name")),
                    "position": position,
                    "baseline_in_population": player_id in baseline_ids,
                    "baseline_population_reasons": reasons,
                    "canonical_team": canonical_team,
                    "tank01_is_free_agent": tank01_is_free_agent,
                    "sleeper_status": sleeper_status,
                    "latest_weekly_roster_member": weekly_member,
                    "season_roster_member": season_member,
                    "ownership_status": ownership_status,
                    "candidate_contracts": evaluations,
                }
            )

    baseline_free_agent_ids = {
        player_id
        for player_id, row in baseline_by_id.items()
        if ((row.get("ownership") or {}).get("status") == "fantasy_free_agent")
    }
    baseline_league_owned_ids = baseline_ids - baseline_free_agent_ids

    contract_summaries: dict[str, Any] = {}
    for name, description in CANDIDATE_CONTRACTS.items():
        ids = contract_ids[name]
        free_agent_ids = contract_free_agent_ids[name]
        added = sorted(ids - baseline_ids)
        removed = sorted(baseline_ids - ids)
        removed_set = set(removed)
        added_set = set(added)
        removed_free_agents = sorted(baseline_free_agent_ids - free_agent_ids)
        added_free_agents = sorted(free_agent_ids - baseline_free_agent_ids)

        contract_summaries[name] = {
            "description": description,
            "player_count": len(ids),
            "delta": len(ids) - len(baseline_ids),
            "added_count": len(added),
            "removed_count": len(removed),
            "added_player_ids": added,
            "removed_player_ids": removed,
            "league_owned_removed_count": len(baseline_league_owned_ids - ids),
            "free_agent_count": len(free_agent_ids),
            "free_agent_delta": len(free_agent_ids) - len(baseline_free_agent_ids),
            "free_agent_added_count": len(added_free_agents),
            "free_agent_removed_count": len(removed_free_agents),
            "movement_discoveries_removed_count": len(generated_movement_ids & removed_set),
            "movement_discoveries_added_population_count": len(generated_movement_ids & added_set),
            "kicker_candidates_removed_count": len(generated_kicker_ids & removed_set),
            "kicker_candidates_added_population_count": len(generated_kicker_ids & added_set),
            "managed_roster_players_removed_count": len(generated_managed_ids & removed_set),
        }

    naive_name = "canonical_sleeper_team_or_fantasy_relevance"
    naive_removed = baseline_ids - contract_ids[naive_name]
    false_drop_risk_rows = [
        row
        for row in bridge_only_rows
        if row["player_id"] in naive_removed
        and (
            row["tank01_is_free_agent"] is False
            or row["latest_weekly_roster_member"]
            or row["season_roster_member"]
        )
    ]
    false_drop_risk_rows.sort(key=lambda row: (row["position"], row["name"] or "", row["player_id"]))

    bridge_only_classification = {
        "count": bridge_only_count,
        "tank01_is_free_agent": dict(
            sorted(
                Counter(str(row["tank01_is_free_agent"]).lower() for row in bridge_only_rows).items()
            )
        ),
        "sleeper_status": dict(
            sorted(Counter(row["sleeper_status"] or "null" for row in bridge_only_rows).items())
        ),
        "canonical_team_present": dict(
            sorted(Counter(str(bool(row["canonical_team"])).lower() for row in bridge_only_rows).items())
        ),
        "latest_weekly_roster_member": dict(
            sorted(Counter(str(row["latest_weekly_roster_member"]).lower() for row in bridge_only_rows).items())
        ),
        "season_roster_member": dict(
            sorted(Counter(str(row["season_roster_member"]).lower() for row in bridge_only_rows).items())
        ),
        "structured_membership_or_not_free_agent_count": sum(
            1
            for row in bridge_only_rows
            if row["tank01_is_free_agent"] is False
            or row["latest_weekly_roster_member"]
            or row["season_roster_member"]
        ),
        "no_positive_structured_nfl_relevance_count": sum(
            1
            for row in bridge_only_rows
            if row["tank01_is_free_agent"] is True
            and not row["canonical_team"]
            and not row["latest_weekly_roster_member"]
            and not row["season_roster_member"]
        ),
    }

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "audit_id": AUDIT_ID,
        "baseline": {
            "main_population_contract": (
                "configured fantasy position AND at least one of has_nfl_team, league_owned, "
                "listed_in_external_source, present_in_external_signal"
            ),
            "player_count": len(baseline_ids),
            "free_agent_count": len(baseline_free_agent_ids),
            "league_owned_count": len(baseline_league_owned_ids),
            "population_reason_counts": dict(sorted(current_reason_counts.items())),
            "exclusive_has_nfl_team_count": bridge_only_count,
        },
        "canonical_nfl_membership_evidence": {
            "season": int(season),
            "season_roster_path": str(season_roster_path.relative_to(root)).replace("\\", "/"),
            "latest_week": latest_week,
            "latest_weekly_roster_path": str(latest_weekly_path.relative_to(root)).replace("\\", "/"),
            "semantics": {
                "latest_weekly_roster": (
                    "canonical primary NFL membership evidence for the latest materialized week; "
                    "not a complete NFL free-agent contract"
                ),
                "season_roster": (
                    "season-level NFL roster context; not proof of membership in every week"
                ),
                "tank01_is_free_agent": (
                    "direct current structured NFL free-agent signal retained by the app; "
                    "durable canonical free-agent contract remains unresolved"
                ),
                "sleeper_status": (
                    "Sleeper platform status; not NFL employment proof"
                ),
                "canonical_sleeper_team": (
                    "Sleeper platform team fact used by player-signals.nfl_team; "
                    "not canonical NFL membership truth"
                ),
            },
        },
        "exclusive_legacy_bridge": bridge_only_classification,
        "candidate_contracts": contract_summaries,
        "naive_canonical_team_false_drop_risk": {
            "count": len(false_drop_risk_rows),
            "players": false_drop_risk_rows,
            "definition": (
                "Players removed by replacing has_nfl_team with Canonical Sleeper Team presence "
                "despite Tank01 IsFreeAgent=false and/or canonical nflverse current-season/latest-week "
                "roster evidence."
            ),
        },
        "downstream_contracts": {
            "free_agent_signals": (
                "selects fantasy_free_agent rows from player-signals; population removal propagates directly"
            ),
            "fa_board": (
                "iterates the full player-signals population; population removal removes board rows"
            ),
            "free_agent_movement": (
                "consumes free-agent-signals and player-signals; candidate summaries report current discovery intersections"
            ),
            "kicker": (
                "consumes held K from player-signals and free-agent K from free-agent-signals; "
                "candidate summaries report current kicker intersections"
            ),
            "managed_roster": (
                "membership is independently canonical; any candidate contract that retains league_owned "
                "should remove zero managed-roster players"
            ),
        },
        "design_findings": {
            "contract_separation": (
                "Population relevance must remain separate from nfl_team display/schedule context and from "
                "NFL employment/free-agent semantics."
            ),
            "recommended_reason_shape": [
                "league_owned",
                "listed_in_external_source",
                "present_in_external_signal",
                "canonical_nfl_membership",
            ],
            "canonical_nfl_membership_note": (
                "A later runtime contract should be phase-aware: latest canonical weekly roster is the "
                "strong in-season membership fact; season roster is secondary/offseason context. Do not "
                "promote Sleeper Team/Status or Tank01 IsFreeAgent into a durable canonical membership "
                "truth without a separate source-of-truth decision."
            ),
            "retired_note": (
                "The repository currently has no accepted canonical retired/employment contract. "
                "Players with no positive structured NFL membership/relevance evidence may be candidates "
                "for population removal, but must not be labeled retired solely from absence."
            ),
        },
        "repository_scope": {
            "eligible_player_count": eligible_count,
            "generated_movement_discovery_count": len(generated_movement_ids),
            "generated_kicker_candidate_count": len(generated_kicker_ids),
            "generated_managed_roster_player_count": len(generated_managed_ids),
        },
    }
    if include_details:
        result["details"] = all_rows
    return result


def compact_summary(result: dict[str, Any]) -> dict[str, Any]:
    contracts = result["candidate_contracts"]
    return {
        "baseline": result["baseline"],
        "canonical_nfl_membership_evidence": result["canonical_nfl_membership_evidence"],
        "exclusive_legacy_bridge": result["exclusive_legacy_bridge"],
        "candidate_contracts": {
            name: {
                key: value
                for key, value in summary.items()
                if key
                in {
                    "player_count",
                    "delta",
                    "added_count",
                    "removed_count",
                    "league_owned_removed_count",
                    "free_agent_count",
                    "free_agent_delta",
                    "movement_discoveries_removed_count",
                    "kicker_candidates_removed_count",
                    "managed_roster_players_removed_count",
                }
            }
            for name, summary in contracts.items()
        },
        "naive_canonical_team_false_drop_risk": result[
            "naive_canonical_team_false_drop_risk"
        ],
        "repository_scope": result["repository_scope"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("fantasy-management/automation/player-signal-materialization.json"),
    )
    parser.add_argument("--details", action="store_true", help="Include per-player evidence rows")
    parser.add_argument("--compact", action="store_true", help="Print only the audit summary")
    args = parser.parse_args()

    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    result = build(root, config_path, include_details=args.details)
    if args.compact:
        result = compact_summary(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
