#!/usr/bin/env python3
"""Audit the player-signal legacy TeamAbbr -> Canonical Sleeper Team cutover.

This is a shadow/parity tool only. It never writes player-signals or changes the
productive population contract. It compares the current 6Y baseline with the
hypothetical use of Canonical Sleeper Team for nfl_team / has_nfl_team and for
team-assisted external-source disambiguation.
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

SCHEMA_VERSION = 1
AUDIT_ID = "player-signal-team-shadow-parity"


def boolean_bucket(value: bool | None) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "null"


def classify_team_delta(legacy_team: str | None, canonical_team: str | None) -> str:
    if legacy_team == canonical_team:
        return "equal"
    if legacy_team and canonical_team:
        return "both_present_different"
    if legacy_team:
        return "legacy_present_canonical_empty"
    if canonical_team:
        return "legacy_empty_canonical_present"
    return "both_empty"


def shadow_population_reasons(
    baseline_reasons: list[str],
    *,
    canonical_team: str | None,
    any_external_source_listed: bool,
) -> list[str]:
    reasons = {str(reason) for reason in baseline_reasons}
    if canonical_team:
        reasons.add("has_nfl_team")
    else:
        reasons.discard("has_nfl_team")
    if any_external_source_listed:
        reasons.add("listed_in_external_source")
    else:
        reasons.discard("listed_in_external_source")
    return sorted(reasons)


def build(root: Path, config_path: Path, *, include_details: bool = False) -> dict[str, Any]:
    config = ops.load_json(config_path)
    baseline = player_signals.build(root, config_path)
    sources = config["sources"]

    legacy_players = ops.load_json(root / sources["players"])
    canonical_identities = ops.load_json(root / sources["canonical_player_identities"])
    canonical_sleeper_players = ops.load_json(root / sources["canonical_sleeper_players"])
    catalog = ops.load_json(root / config["source_catalog"])
    ops.validate_catalog(catalog)

    if not isinstance(legacy_players, list):
        raise player_signals.PlayerSignalMaterializationError(
            "Players input must be a JSON array"
        )

    try:
        identity_by_sleeper = ops.build_canonical_identity_by_sleeper(canonical_identities)
        sleeper_player_lookup = ops.build_canonical_sleeper_player_lookup(
            canonical_sleeper_players,
            identity_by_sleeper,
        )
    except ops.MaterializationError as exc:
        raise player_signals.PlayerSignalMaterializationError(
            f"Canonical player identity/platform inputs are invalid: {exc}"
        ) from exc

    loaded_sources = [
        ops.resolve_catalog_source(root, definition)
        for definition in catalog["sources"]
        if definition.get("active")
    ]
    allowed_positions = {str(position).upper() for position in config["population"]["positions"]}
    baseline_by_id = {
        str(player["player_id"]): player
        for player in baseline["players"]
    }
    baseline_ids = set(baseline_by_id)
    shadow_ids: set[str] = set()
    delta_classes: Counter[str] = Counter()
    team_pairs: Counter[str] = Counter()
    source_change_counts: Counter[str] = Counter()
    changed_source_players: set[str] = set()
    detail_rows: list[dict[str, Any]] = []

    legacy_empty_is_free_agent: Counter[str] = Counter()
    legacy_empty_sleeper_status: Counter[str] = Counter()
    legacy_empty_joint_status: Counter[str] = Counter()
    legacy_empty_ownership_status: Counter[str] = Counter()
    legacy_empty_only_team_is_free_agent: Counter[str] = Counter()
    legacy_empty_only_team_sleeper_status: Counter[str] = Counter()
    legacy_empty_only_team_count = 0
    legacy_empty_other_reason_count = 0

    free_agent_added: list[str] = []
    free_agent_removed: list[str] = []
    added_population: list[str] = []
    removed_population: list[str] = []
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

        legacy_team = ops.optional_text(legacy_player.get("TeamAbbr"))
        canonical_team = ops.optional_text(sleeper_player.get("Team"))
        delta_class = classify_team_delta(legacy_team, canonical_team)
        if delta_class != "equal":
            delta_classes[delta_class] += 1
            if legacy_team and canonical_team:
                team_pairs[f"{legacy_team}->{canonical_team}"] += 1

        baseline_player = baseline_by_id.get(player_id)
        baseline_reasons = list((baseline_player or {}).get("population_reasons") or [])
        baseline_listed = bool(
            baseline_player
            and any(
                bool(result.get("listed"))
                for result in (baseline_player.get("source_signals") or {}).values()
                if isinstance(result, dict)
            )
        )
        shadow_listed = baseline_listed
        source_changes: list[dict[str, Any]] = []

        if delta_class != "equal":
            shadow_player = dict(player)
            shadow_player["TeamAbbr"] = canonical_team
            shadow_listed = False
            for source in loaded_sources:
                source_id = source.definition["source_id"]
                shadow_result, _ = player_signals.evaluate_source_for_canonical_player(
                    shadow_player,
                    identity,
                    source,
                )
                if shadow_result.get("listed"):
                    shadow_listed = True

                if baseline_player is None:
                    continue
                baseline_result = (baseline_player.get("source_signals") or {}).get(source_id) or {}
                old_state = {
                    "listed": bool(baseline_result.get("listed")),
                    "join_method": baseline_result.get("join_method"),
                    "coverage_status": baseline_result.get("coverage_status"),
                }
                new_state = {
                    "listed": bool(shadow_result.get("listed")),
                    "join_method": shadow_result.get("join_method"),
                    "coverage_status": shadow_result.get("coverage_status"),
                }
                if old_state != new_state:
                    source_change_counts[source_id] += 1
                    changed_source_players.add(player_id)
                    source_changes.append(
                        {"source_id": source_id, "before": old_state, "after": new_state}
                    )

        shadow_reasons = shadow_population_reasons(
            baseline_reasons,
            canonical_team=canonical_team,
            any_external_source_listed=shadow_listed,
        )
        in_baseline = player_id in baseline_ids
        in_shadow = bool(shadow_reasons)
        if in_shadow:
            shadow_ids.add(player_id)

        ownership_status = (
            ((baseline_player or {}).get("ownership") or {}).get("status")
            if baseline_player
            else None
        )

        if delta_class == "legacy_present_canonical_empty" and in_baseline:
            tank01_is_free_agent = ops.optional_bool(legacy_player.get("IsFreeAgent"))
            sleeper_status = ops.optional_text(sleeper_player.get("Status"))
            is_free_agent_bucket = boolean_bucket(tank01_is_free_agent)
            sleeper_status_bucket = sleeper_status or "null"
            ownership_status_bucket = ops.optional_text(ownership_status) or "null"
            joint_bucket = (
                f"IsFreeAgent={is_free_agent_bucket}|Status={sleeper_status_bucket}"
            )

            legacy_empty_is_free_agent[is_free_agent_bucket] += 1
            legacy_empty_sleeper_status[sleeper_status_bucket] += 1
            legacy_empty_joint_status[joint_bucket] += 1
            legacy_empty_ownership_status[ownership_status_bucket] += 1

            if sorted(baseline_reasons) == ["has_nfl_team"]:
                legacy_empty_only_team_count += 1
                legacy_empty_only_team_is_free_agent[is_free_agent_bucket] += 1
                legacy_empty_only_team_sleeper_status[sleeper_status_bucket] += 1
            else:
                legacy_empty_other_reason_count += 1

        if in_baseline and not in_shadow:
            removed_population.append(player_id)
            if ownership_status == "fantasy_free_agent":
                free_agent_removed.append(player_id)
        elif not in_baseline and in_shadow:
            added_population.append(player_id)
            # A currently excluded player has no baseline ownership object. Keep
            # downstream impact conservative instead of guessing availability.

        if include_details and (delta_class != "equal" or source_changes or in_baseline != in_shadow):
            detail_rows.append(
                {
                    "player_id": player_id,
                    "name": ops.optional_text(identity.get("Name")),
                    "position": position,
                    "legacy_team": legacy_team,
                    "canonical_team": canonical_team,
                    "team_delta_class": delta_class,
                    "baseline_population_reasons": sorted(baseline_reasons),
                    "shadow_population_reasons": shadow_reasons,
                    "baseline_in_population": in_baseline,
                    "shadow_in_population": in_shadow,
                    "ownership_status": ownership_status,
                    "tank01_is_free_agent": ops.optional_bool(legacy_player.get("IsFreeAgent")),
                    "sleeper_status": ops.optional_text(sleeper_player.get("Status")),
                    "source_join_changes": source_changes,
                }
            )

    # The shadow set starts from all eligible players evaluated above. A player
    # that was not in the baseline can only become included here through a newly
    # present Canonical Team value (or a shadow source join); both are represented
    # by shadow_reasons.
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "audit_id": AUDIT_ID,
        "baseline": {
            "dataset_id": baseline.get("dataset_id"),
            "generated_at": baseline.get("generated_at"),
            "input_fingerprint": baseline.get("input_fingerprint"),
            "player_count": len(baseline_ids),
        },
        "summary": {
            "eligible_player_count": eligible_count,
            "team_delta_count": sum(delta_classes.values()),
            "team_delta_classes": dict(sorted(delta_classes.items())),
            "team_value_pairs": dict(sorted(team_pairs.items())),
            "legacy_present_canonical_empty_evidence": {
                "baseline_player_count": sum(legacy_empty_is_free_agent.values()),
                "tank01_is_free_agent": dict(sorted(legacy_empty_is_free_agent.items())),
                "sleeper_status": dict(sorted(legacy_empty_sleeper_status.items())),
                "joint_tank01_free_agent_and_sleeper_status": dict(
                    sorted(legacy_empty_joint_status.items())
                ),
                "fantasy_ownership_status": dict(
                    sorted(legacy_empty_ownership_status.items())
                ),
                "population_dependency": {
                    "only_has_nfl_team_count": legacy_empty_only_team_count,
                    "other_population_reason_count": legacy_empty_other_reason_count,
                    "only_has_nfl_team_tank01_is_free_agent": dict(
                        sorted(legacy_empty_only_team_is_free_agent.items())
                    ),
                    "only_has_nfl_team_sleeper_status": dict(
                        sorted(legacy_empty_only_team_sleeper_status.items())
                    ),
                },
                "interpretation": (
                    "Tank01 IsFreeAgent is the direct structured NFL free-agent signal; "
                    "Sleeper Status and team-field presence are independent source facts and "
                    "must not be treated as proof of an NFL contract."
                ),
            },
            "population": {
                "baseline_count": len(baseline_ids),
                "shadow_count": len(shadow_ids),
                "added_count": len(added_population),
                "removed_count": len(removed_population),
                "added_player_ids": sorted(added_population),
                "removed_player_ids": sorted(removed_population),
            },
            "external_source_joins": {
                "changed_player_count": len(changed_source_players),
                "changed_result_count": sum(source_change_counts.values()),
                "by_source": dict(sorted(source_change_counts.items())),
            },
            "downstream": {
                "free_agent_input_removed_count": len(free_agent_removed),
                "free_agent_input_removed_player_ids": sorted(free_agent_removed),
                "free_agent_input_added_count": 0,
                "free_agent_input_added_player_ids": [],
                "fa_board_input_population_delta": len(added_population) - len(removed_population),
                "movement_input_population_delta": -len(free_agent_removed),
                "note": (
                    "FA Board consumes the full player-signal population; Free-Agent and "
                    "Movement consumers derive from player-signals fantasy-free-agent rows. "
                    "No ownership status is guessed for players absent from the baseline."
                ),
            },
        },
    }
    if include_details:
        result["details"] = detail_rows
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("fantasy-management/automation/player-signal-materialization.json"),
    )
    parser.add_argument("--details", action="store_true", help="Include per-player delta rows")
    args = parser.parse_args()

    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    print(json.dumps(build(root, config_path, include_details=args.details), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
