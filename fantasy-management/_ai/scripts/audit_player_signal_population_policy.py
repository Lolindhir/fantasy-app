#!/usr/bin/env python3
"""Adjudicate the future player-signal population policy without changing runtime.

Checkpoint 6Z.4 consumes the 6Z.3 shadow audit and turns its raw removal gap into
explicit policy alternatives. It deliberately keeps Canonical NFL roster facts,
Fantasy relevance, previous-season history and provider context separate.

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
        "OR current-season Canonical NFL roster history."
    ),
    "current_plus_previous_history": (
        "Current Canonical policy plus previous-season Canonical roster history."
    ),
    "current_plus_provider_context": (
        "Current Canonical policy plus Sleeper Team presence or Tank01 IsFreeAgent=false."
    ),
    "current_plus_previous_and_provider_context": (
        "Current Canonical policy plus both previous-season history and provider context."
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


def cohort_for_row(row: dict[str, Any]) -> str:
    return population_audit.classify_shadow_gap(
        previous_season_roster_member=bool(row["previous_season_roster_member"]),
        canonical_team_present=bool(row["canonical_team"]),
        tank01_is_free_agent=row["tank01_is_free_agent"],
    )


def evaluate_policy_variants(row: dict[str, Any]) -> dict[str, bool]:
    reasons = set(row.get("baseline_population_reasons") or [])
    non_bridge_relevant = bool(reasons - {BRIDGE_REASON})
    current_canonical = (
        non_bridge_relevant
        or bool(row["latest_weekly_roster_member"])
        or bool(row["season_roster_member"])
    )
    previous_history = bool(row["previous_season_roster_member"])
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
        "previous_season_roster_member": row["previous_season_roster_member"],
    }


def build(root: Path, config_path: Path) -> dict[str, Any]:
    shadow = population_audit.build(root, config_path, include_details=True)
    rows = shadow.get("details")
    if not isinstance(rows, list):
        raise PopulationPolicyAuditError("6Z.3 audit details are unavailable")

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
    policy_by_player: dict[str, dict[str, bool]] = {}

    for row in rows:
        player_id = str(row["player_id"])
        evaluations = evaluate_policy_variants(row)
        policy_by_player[player_id] = evaluations
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

    current_evidence = shadow["canonical_nfl_membership_evidence"]
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
        "current_context": {
            "season": current_evidence["season"],
            "latest_week": current_week,
            "current_season_roster_record_count": current_season_records,
            "latest_weekly_roster_record_count": current_evidence[
                "latest_weekly_roster_index_quality"
            ]["record_count"],
            "previous_season": current_evidence["previous_season"],
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
                "current-season Canonical NFL roster history"
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
            "previous_season_history": (
                "Previous-season-only rows have no current-week/current-season Canonical roster "
                "evidence and no independent Fantasy relevance reason. During an established "
                "regular season they do not justify a permanent include; current-season history "
                "already preserves players who were relevant earlier in the same season."
            ),
            "provider_context_exceptions": (
                "These rows have no current-week/current-season/previous-season Canonical roster "
                "evidence. Sleeper/Tank01 disagreement is retained for diagnosis but cannot override "
                "the repository's primary Canonical NFL-membership source."
            ),
            "low_evidence": (
                "These rows are fantasy free agents with no non-bridge Fantasy relevance, no current "
                "or previous-season Canonical roster evidence, and no positive provider-context "
                "exception. They are the strongest removal cases."
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
        "current_context": result["current_context"],
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
