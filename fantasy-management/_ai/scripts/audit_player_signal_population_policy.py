#!/usr/bin/env python3
"""Adjudicate the future player-signal population policy without changing runtime.

Checkpoint 6Z.4 consumes the 6Z.3 shadow audit and turns its raw removal gap into
explicit policy alternatives. It deliberately keeps Canonical NFL roster facts,
Fantasy relevance, previous-season history and provider context separate.

The policy audit uses the union of season-roster and weekly-roster Canonical
history. This matters for statuses such as DEV/practice-squad history that can
appear in weekly Canonical partitions while being absent from the season roster.

Nothing in this module changes productive player-signals population reasons.
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

import audit_player_signal_population_relevance as population_audit  # noqa: E402
import build_fantasy_operations_inputs as ops  # noqa: E402

SCHEMA_VERSION = 1
AUDIT_ID = "player-signal-population-policy-adjudication"
BRIDGE_REASON = "has_nfl_team"

POLICY_VARIANTS = {
    "current_canonical": (
        "Non-bridge Fantasy relevance OR latest-week Canonical NFL membership "
        "OR any current-season Canonical NFL roster history from season/weekly rosters."
    ),
    "current_plus_previous_history": (
        "Current Canonical policy plus any previous-season Canonical season/weekly roster history."
    ),
    "current_plus_provider_context": (
        "Current Canonical policy plus Sleeper Team presence or Tank01 IsFreeAgent=false."
    ),
    "current_plus_previous_and_provider_context": (
        "Current Canonical policy plus both previous-season Canonical history and provider context."
    ),
}


class PopulationPolicyAuditError(RuntimeError):
    """Raised when 6Z.4 policy adjudication cannot be evaluated safely."""


def provider_context_shape(
    *,
    canonical_team_present: bool,
    tank01_is_free_agent: bool | None,
) -> str:
    tank01_not_free_agent = tank01_is_free_agent is False
    if canonical_team_present and tank01_not_free_agent:
        return "sleeper_team_and_tank01_not_free_agent"
    if canonical_team_present:
        return "sleeper_team_only"
    if tank01_not_free_agent:
        return "tank01_not_free_agent_only"
    return "none"


def age_bucket(value: Any) -> str:
    age = ops.optional_number(value)
    if age is None:
        return "unknown"
    if age < 25:
        return "under_25"
    if age < 30:
        return "25_to_29"
    if age < 35:
        return "30_to_34"
    return "35_plus"


def experience_bucket(value: Any) -> str:
    years = ops.optional_number(value)
    if years is None:
        return "unknown"
    if years <= 1:
        return "0_to_1"
    if years <= 3:
        return "2_to_3"
    if years <= 6:
        return "4_to_6"
    return "7_plus"


def build_weekly_history_membership(
    root: Path,
    season: int,
    identity_by_sleeper: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    directory = root / "source-data" / "nfl" / "weekly-rosters" / str(season)
    if not directory.is_dir():
        raise PopulationPolicyAuditError(
            f"Canonical weekly-roster directory is missing for season {season}: {directory}"
        )

    partitions: list[tuple[int, Path]] = []
    for path in directory.glob("*.json"):
        try:
            week = int(path.stem)
        except ValueError:
            continue
        partitions.append((week, path))
    partitions.sort(key=lambda item: item[0])
    if not partitions:
        raise PopulationPolicyAuditError(
            f"No Canonical weekly-roster partitions found for season {season}"
        )

    sleeper_ids: set[str] = set()
    canonical_ids: set[str] = set()
    record_count = 0
    mismatch_count = 0
    unresolved_count = 0
    for week, path in partitions:
        membership = population_audit.build_roster_membership_index(
            ops.load_json(path),
            identity_by_sleeper,
            source_name=str(path.relative_to(root)),
        )
        sleeper_ids.update(membership["sleeper_ids"])
        canonical_ids.update(membership["canonical_ids"])
        record_count += int(membership["record_count"])
        mismatch_count += int(membership["current_sleeper_mapping_mismatch_count"])
        unresolved_count += int(membership["unresolved_record_count"])

    return {
        "sleeper_ids": sleeper_ids,
        "canonical_ids": canonical_ids,
        "weeks": [week for week, _ in partitions],
        "partition_count": len(partitions),
        "record_count": record_count,
        "current_sleeper_mapping_mismatch_count": mismatch_count,
        "unresolved_record_count": unresolved_count,
    }


def cohort_for_row(row: dict[str, Any]) -> str:
    if row["previous_season_canonical_history_member"]:
        return "previous_season_history"
    if row["canonical_team"] or row["tank01_is_free_agent"] is False:
        return "provider_context_exception"
    if row["tank01_is_free_agent"] is True:
        return "free_agent_no_current_or_recent_roster_evidence"
    return "unresolved_diagnostic_state"


def evaluate_policy_variants(row: dict[str, Any]) -> dict[str, bool]:
    reasons = set(row.get("baseline_population_reasons") or [])
    non_bridge_relevant = bool(reasons - {BRIDGE_REASON})
    current_canonical = (
        non_bridge_relevant
        or bool(row["latest_weekly_roster_member"])
        or bool(row["current_season_canonical_history_member"])
    )
    previous_history = bool(row["previous_season_canonical_history_member"])
    provider_context = (
        bool(row["canonical_team"])
        or row["tank01_is_free_agent"] is False
    )
    return {
        "current_canonical": current_canonical,
        "current_plus_previous_history": current_canonical or previous_history,
        "current_plus_provider_context": current_canonical or provider_context,
        "current_plus_previous_and_provider_context": (
            current_canonical or previous_history or provider_context
        ),
    }


def _generated_ids(root: Path, relative_path: str, list_key: str) -> set[str]:
    return population_audit._load_optional_generated(  # noqa: SLF001
        root,
        relative_path,
        list_key=list_key,
    )


def _diagnostic_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(rows),
        "positions": dict(sorted(Counter(row["position"] for row in rows).items())),
        "sleeper_status": dict(
            sorted(Counter(row["sleeper_status"] or "null" for row in rows).items())
        ),
        "tank01_is_free_agent": dict(
            sorted(Counter(str(row["tank01_is_free_agent"]).lower() for row in rows).items())
        ),
        "provider_context_shape": dict(
            sorted(
                Counter(
                    provider_context_shape(
                        canonical_team_present=bool(row["canonical_team"]),
                        tank01_is_free_agent=row["tank01_is_free_agent"],
                    )
                    for row in rows
                ).items()
            )
        ),
        "age_buckets": dict(sorted(Counter(age_bucket(row["age"]) for row in rows).items())),
        "experience_buckets": dict(
            sorted(Counter(experience_bucket(row["years_experience"]) for row in rows).items())
        ),
    }


def _brief_player(row: dict[str, Any], *, cohort: str) -> dict[str, Any]:
    return {
        "player_id": row["player_id"],
        "name": row["name"],
        "position": row["position"],
        "cohort": cohort,
        "age": row["age"],
        "years_experience": row["years_experience"],
        "sleeper_status": row["sleeper_status"],
        "canonical_team": row["canonical_team"],
        "tank01_is_free_agent": row["tank01_is_free_agent"],
        "current_season_roster_member": row["season_roster_member"],
        "current_season_weekly_history_member": row[
            "current_season_weekly_history_member"
        ],
        "previous_season_roster_member": row["previous_season_roster_member"],
        "previous_season_weekly_history_member": row[
            "previous_season_weekly_history_member"
        ],
    }


def build(root: Path, config_path: Path) -> dict[str, Any]:
    shadow = population_audit.build(root, config_path, include_details=True)
    rows = shadow.get("details")
    if not isinstance(rows, list):
        raise PopulationPolicyAuditError("6Z.3 audit details are unavailable")

    config = ops.load_json(config_path)
    sources = config["sources"]
    canonical_identities = ops.load_json(root / sources["canonical_player_identities"])
    try:
        identity_by_sleeper = ops.build_canonical_identity_by_sleeper(canonical_identities)
    except ops.MaterializationError as exc:
        raise PopulationPolicyAuditError(
            f"Canonical player identities are invalid: {exc}"
        ) from exc

    current_evidence = shadow["canonical_nfl_membership_evidence"]
    current_season = int(current_evidence["season"])
    previous_season = int(current_evidence["previous_season"])
    current_weekly_history = build_weekly_history_membership(
        root,
        current_season,
        identity_by_sleeper,
    )
    previous_weekly_history = build_weekly_history_membership(
        root,
        previous_season,
        identity_by_sleeper,
    )

    current_weekly_only_additions = 0
    previous_weekly_only_additions = 0
    for row in rows:
        player_id = str(row["player_id"])
        identity = identity_by_sleeper.get(player_id)
        if identity is None:
            raise PopulationPolicyAuditError(
                f"Eligible player {player_id} has no Canonical Identity mapping"
            )

        current_weekly_history_member = population_audit.in_roster_membership(
            player_id,
            identity,
            current_weekly_history,
        )
        previous_weekly_history_member = population_audit.in_roster_membership(
            player_id,
            identity,
            previous_weekly_history,
        )
        row["current_season_weekly_history_member"] = current_weekly_history_member
        row["current_season_canonical_history_member"] = (
            bool(row["season_roster_member"]) or current_weekly_history_member
        )
        row["previous_season_weekly_history_member"] = previous_weekly_history_member
        row["previous_season_canonical_history_member"] = (
            bool(row["previous_season_roster_member"])
            or previous_weekly_history_member
        )
        if current_weekly_history_member and not row["season_roster_member"]:
            current_weekly_only_additions += 1
        if previous_weekly_history_member and not row["previous_season_roster_member"]:
            previous_weekly_only_additions += 1

    baseline_rows = [row for row in rows if row.get("baseline_in_population")]
    baseline_ids = {str(row["player_id"]) for row in baseline_rows}
    baseline_free_agent_ids = {
        str(row["player_id"])
        for row in baseline_rows
        if row.get("ownership_status") == "fantasy_free_agent"
    }
    baseline_league_owned_ids = baseline_ids - baseline_free_agent_ids

    movement_ids = _generated_ids(
        root,
        "fantasy-management/generated/operations/free-agent-movement-signals.json",
        "discoveries",
    )
    kicker_ids = _generated_ids(
        root,
        "fantasy-management/generated/operations/kicker-streaming-inputs.json",
        "candidates",
    )
    managed_ids = _generated_ids(
        root,
        "fantasy-management/generated/operations/managed-roster-signals.json",
        "players",
    )

    variant_ids = {name: set() for name in POLICY_VARIANTS}
    variant_free_agent_ids = {name: set() for name in POLICY_VARIANTS}

    for row in rows:
        player_id = str(row["player_id"])
        evaluations = evaluate_policy_variants(row)
        for name, included in evaluations.items():
            if included:
                variant_ids[name].add(player_id)
                if row.get("ownership_status") == "fantasy_free_agent":
                    variant_free_agent_ids[name].add(player_id)

    variants: dict[str, Any] = {}
    for name, description in POLICY_VARIANTS.items():
        ids = variant_ids[name]
        free_agent_ids = variant_free_agent_ids[name]
        added = sorted(ids - baseline_ids)
        removed = sorted(baseline_ids - ids)
        removed_set = set(removed)
        variants[name] = {
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
            "free_agent_removed_count": len(baseline_free_agent_ids - free_agent_ids),
            "movement_discoveries_removed_count": len(movement_ids & removed_set),
            "kicker_candidates_removed_count": len(kicker_ids & removed_set),
            "managed_roster_players_removed_count": len(managed_ids & removed_set),
        }

    recommended_name = "current_canonical"
    recommended_removed = set(variants[recommended_name]["removed_player_ids"])
    removed_rows = [
        row for row in baseline_rows if str(row["player_id"]) in recommended_removed
    ]

    cohorts: dict[str, list[dict[str, Any]]] = {
        "previous_season_history": [],
        "provider_context_exception": [],
        "free_agent_no_current_or_recent_roster_evidence": [],
        "unresolved_diagnostic_state": [],
    }
    for row in removed_rows:
        cohorts[cohort_for_row(row)].append(row)

    provider_exception_players = sorted(
        (
            _brief_player(row, cohort="provider_context_exception")
            for row in cohorts["provider_context_exception"]
        ),
        key=lambda row: (row["position"], row["name"] or "", row["player_id"]),
    )
    removed_kicker_players = sorted(
        (
            _brief_player(row, cohort=cohort_for_row(row))
            for row in removed_rows
            if str(row["player_id"]) in kicker_ids
        ),
        key=lambda row: (row["cohort"], row["name"] or "", row["player_id"]),
    )

    current_week = int(current_evidence["latest_week"])
    current_season_records = int(
        current_evidence["season_roster_index_quality"]["record_count"]
    )
    if current_week < 1 or current_season_records <= 0:
        raise PopulationPolicyAuditError(
            "6Z.4 current in-season policy requires materialized current-season roster evidence"
        )

    result = {
        "schema_version": SCHEMA_VERSION,
        "audit_id": AUDIT_ID,
        "runtime_effect": "analysis_only_no_population_change",
        "baseline": shadow["baseline"],
        "canonical_history_quality": {
            "season": current_season,
            "latest_week": current_week,
            "current_season_roster_record_count": current_season_records,
            "current_season_weekly_history": {
                "weeks": current_weekly_history["weeks"],
                "partition_count": current_weekly_history["partition_count"],
                "record_count": current_weekly_history["record_count"],
                "current_sleeper_mapping_mismatch_count": current_weekly_history[
                    "current_sleeper_mapping_mismatch_count"
                ],
                "unresolved_record_count": current_weekly_history["unresolved_record_count"],
                "eligible_player_additions_over_season_roster": current_weekly_only_additions,
            },
            "previous_season": previous_season,
            "previous_season_roster_record_count": current_evidence[
                "previous_season_roster_index_quality"
            ]["record_count"],
            "previous_season_weekly_history": {
                "weeks": previous_weekly_history["weeks"],
                "partition_count": previous_weekly_history["partition_count"],
                "record_count": previous_weekly_history["record_count"],
                "current_sleeper_mapping_mismatch_count": previous_weekly_history[
                    "current_sleeper_mapping_mismatch_count"
                ],
                "unresolved_record_count": previous_weekly_history["unresolved_record_count"],
                "eligible_player_additions_over_season_roster": previous_weekly_only_additions,
            },
            "identity_policy": current_evidence["identity_policy"],
        },
        "policy_variants": variants,
        "recommended_policy": {
            "variant": recommended_name,
            "contract": (
                "configured fantasy position AND (league_owned OR listed_in_external_source "
                "OR present_in_external_signal OR canonical_nfl_membership "
                "OR canonical_nfl_recent_history)"
            ),
            "canonical_nfl_membership": (
                "latest materialized weekly Canonical NFL roster membership"
            ),
            "canonical_nfl_recent_history": (
                "current-season Canonical NFL roster history as the union of the season roster "
                "and every materialized current-season weekly-roster partition"
            ),
            "previous_season_history": (
                "diagnostic only while current-season Canonical roster evidence is available; "
                "may serve only as a temporary new-season fallback before current-season roster "
                "data becomes available, never concurrently as a permanent in-season include"
            ),
            "provider_context": (
                "Sleeper Team/Status and Tank01 IsFreeAgent remain diagnostic only and do not "
                "become population truth"
            ),
            "reentry": (
                "A removed player re-enters deterministically when league ownership, an external "
                "Fantasy relevance signal, current Canonical weekly membership, or current-season "
                "Canonical roster history becomes true."
            ),
            "current_expected_player_count": variants[recommended_name]["player_count"],
            "current_expected_delta": variants[recommended_name]["delta"],
            "current_expected_removed_count": variants[recommended_name]["removed_count"],
        },
        "recommended_removal_cohorts": {
            name: {
                **_diagnostic_summary(cohort_rows),
                "kicker_candidate_count": sum(
                    1 for row in cohort_rows if str(row["player_id"]) in kicker_ids
                ),
                "movement_discovery_count": sum(
                    1 for row in cohort_rows if str(row["player_id"]) in movement_ids
                ),
                "managed_roster_count": sum(
                    1 for row in cohort_rows if str(row["player_id"]) in managed_ids
                ),
            }
            for name, cohort_rows in cohorts.items()
        },
        "provider_context_exceptions": {
            "count": len(provider_exception_players),
            "players": provider_exception_players,
        },
        "removed_kicker_adjudication": {
            "count": len(removed_kicker_players),
            "players": removed_kicker_players,
        },
        "decision_findings": {
            "canonical_history_coverage": (
                "Season-roster membership alone is not a complete recent-history signal. Weekly "
                "Canonical rosters can contain DEV/practice-squad history absent from the season "
                "roster, so current/previous-season history is evaluated as a season+weekly union."
            ),
            "previous_season_history": (
                "Previous-season-only rows have no current-season Canonical roster evidence and "
                "no independent Fantasy relevance reason. During an established regular season "
                "they do not justify a permanent include; current-season season+weekly history "
                "already preserves players who were relevant earlier in the same season."
            ),
            "provider_context_exceptions": (
                "After Canonical season+weekly history is exhausted, remaining Sleeper/Tank01 "
                "disagreement is retained for diagnosis but cannot override the repository's "
                "primary Canonical NFL-membership source."
            ),
            "low_evidence": (
                "These rows are fantasy free agents with no non-bridge Fantasy relevance, no "
                "current or previous-season Canonical season/weekly roster evidence, and no "
                "positive provider-context exception. They are the strongest removal cases."
            ),
            "kicker": (
                "Kicker removals are explicitly enumerated because Kicker is the largest sensitive "
                "downstream surface. The later runtime cutover must retain the existing fail-closed "
                "weekly job/schedule verification and validate the exact candidate delta."
            ),
        },
    }
    return result


def compact_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "baseline": result["baseline"],
        "canonical_history_quality": result["canonical_history_quality"],
        "policy_variants": {
            name: {
                key: value
                for key, value in summary.items()
                if key in {
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
            for name, summary in result["policy_variants"].items()
        },
        "recommended_policy": result["recommended_policy"],
        "recommended_removal_cohorts": result["recommended_removal_cohorts"],
        "provider_context_exceptions": result["provider_context_exceptions"],
        "removed_kicker_adjudication": result["removed_kicker_adjudication"],
        "decision_findings": result["decision_findings"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("fantasy-management/automation/player-signal-materialization.json"),
    )
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    result = build(root, config_path)
    if args.compact:
        result = compact_summary(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
