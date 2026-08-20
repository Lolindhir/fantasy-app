#!/usr/bin/env python3
"""Build the current Mighty Giants roster overview read model.

This materializer intentionally separates deterministic roster facts from evaluative
classification. Deterministic structure is always re-derived from current League and
managed-roster signals. Role/security classifications come from a versioned hybrid
seed plus optional user overrides until a future fully automated classifier is
validated and approved.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_fantasy_operations_inputs as ops  # noqa: E402


SCHEMA_VERSION = 1
VALID_ROLES = {"core_starter", "starter_rotation", "backup", "prospect", "specialist"}
VALID_SECURITY = {"locked", "strong_hold", "hold", "conditional", "churn"}
STARTABLE_ROLES = {"core_starter", "starter_rotation"}
BOUNDARY_SECURITY = {"conditional", "churn"}


class RosterOverviewError(RuntimeError):
    """Raised when the roster overview cannot be built safely."""


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RosterOverviewError(f"Missing required JSON input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RosterOverviewError(f"Invalid JSON input {path}: {exc}") from exc


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _classification_key(name: Any, position: Any) -> tuple[str, str]:
    return (ops.normalize_name(name), str(position or "").upper())


def _validate_state(state: dict[str, Any]) -> None:
    if state.get("schema_version") != 1:
        raise RosterOverviewError("Unexpected roster evaluation state schema version")
    if not isinstance(state.get("classifications"), list):
        raise RosterOverviewError("Roster evaluation state classifications must be an array")
    seen: set[tuple[str, str]] = set()
    for entry in state["classifications"]:
        key = _classification_key(entry.get("name"), entry.get("position"))
        if not key[0] or not key[1]:
            raise RosterOverviewError("Roster classification requires name and position")
        if key in seen:
            raise RosterOverviewError(f"Duplicate roster classification: {entry.get('name')} / {entry.get('position')}")
        seen.add(key)
        if entry.get("roster_role") not in VALID_ROLES:
            raise RosterOverviewError(f"Invalid roster_role for {entry.get('name')}")
        if entry.get("roster_security") not in VALID_SECURITY:
            raise RosterOverviewError(f"Invalid roster_security for {entry.get('name')}")
    overrides = state.get("user_overrides") or []
    if not isinstance(overrides, list):
        raise RosterOverviewError("user_overrides must be an array")
    for entry in overrides:
        if entry.get("roster_role") is not None and entry.get("roster_role") not in VALID_ROLES:
            raise RosterOverviewError(f"Invalid override roster_role for {entry.get('name')}")
        if entry.get("roster_security") is not None and entry.get("roster_security") not in VALID_SECURITY:
            raise RosterOverviewError(f"Invalid override roster_security for {entry.get('name')}")


def _index_classifications(state: dict[str, Any]) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    base = {_classification_key(item["name"], item["position"]): item for item in state["classifications"]}
    overrides = {
        _classification_key(item.get("name"), item.get("position")): item
        for item in state.get("user_overrides") or []
        if _classification_key(item.get("name"), item.get("position"))[0]
    }
    return base, overrides


def _effective_classification(
    player: dict[str, Any],
    base: dict[tuple[str, str], dict[str, Any]],
    overrides: dict[tuple[str, str], dict[str, Any]],
    state: dict[str, Any],
) -> dict[str, Any]:
    key = _classification_key(player.get("name"), player.get("position"))
    seed = base.get(key)
    override = overrides.get(key)
    if seed is None and override is None:
        return {
            "roster_role": None,
            "roster_security": None,
            "boundary_priority": None,
            "confidence": "unknown",
            "source": "unclassified",
            "source_as_of": None,
            "user_override": False,
            "notes": [],
            "evidence": [],
            "review_status": "needs_classification",
        }

    source = dict(seed or {})
    if override:
        for key_name in ("roster_role", "roster_security", "boundary_priority", "confidence", "notes"):
            if key_name in override and override[key_name] is not None:
                source[key_name] = override[key_name]
    return {
        "roster_role": source.get("roster_role"),
        "roster_security": source.get("roster_security"),
        "boundary_priority": source.get("boundary_priority"),
        "confidence": source.get("confidence", state.get("default_confidence", "medium")),
        "source": "user_override" if override else source.get("evaluation_source") or state.get("default_evaluation_source", "manual_seed"),
        "source_as_of": source.get("as_of") or state.get("as_of"),
        "user_override": bool(override),
        "notes": list(source.get("notes") or []),
        "evidence": list(source.get("evidence") or []),
        "review_status": "user_override" if override else "seeded_manual",
    }


def _structural_function(role: str | None) -> str:
    if role in STARTABLE_ROLES:
        return "starter_core"
    if role == "backup":
        return "coverage_reserve"
    if role == "prospect":
        return "development"
    if role == "specialist":
        return "specialist"
    return "unclassified"


def _roster_area(sections: list[str]) -> str:
    values = set(sections)
    if "reserve" in values:
        return "reserve"
    if "taxi" in values:
        return "taxi"
    if "roster" in values:
        return "active"
    return "unknown"


def _derive_taxi_phase(league: dict[str, Any]) -> str:
    final_scored_week = ops.optional_number(league.get("FinalScoredWeek")) or 0
    status = str(league.get("Status") or "").strip().casefold()
    phase = str(league.get("Phase") or "").strip().casefold()
    if float(final_scored_week) > 0:
        return "locked"
    if "draft" in status or "draft" in phase or "preseason" in status or "pre-season" in status:
        return "pre_lock"
    if status in {"in_season", "in season", "regular season", "regular-season"}:
        return "locked"
    return "unknown"


def _fixed_starters(roster_size: list[Any]) -> tuple[dict[str, int], int, int]:
    counts = Counter(str(item or "").upper() for item in roster_size)
    fixed = {
        position: count
        for position, count in counts.items()
        if position not in {"BN", "FLEX", "SUPER_FLEX", "IR", "RESERVE", "TAXI"} and count > 0
    }
    flex_slots = counts.get("FLEX", 0) + counts.get("SUPER_FLEX", 0)
    bench_slots = counts.get("BN", 0)
    return dict(sorted(fixed.items())), flex_slots, bench_slots


def _coverage_status(count: int, floor: int | None, preferred: int | None) -> str:
    if floor is None and preferred is None:
        return "pool_managed"
    if floor is not None and count < floor:
        return "below_floor"
    if preferred is not None and count < preferred:
        return "floor_met_below_preferred"
    return "preferred_met"


def _market_summary(player: dict[str, Any]) -> dict[str, Any]:
    market = player.get("market") if isinstance(player.get("market"), dict) else {}
    fp = market.get("fantasypros") if isinstance(market.get("fantasypros"), dict) else {}
    fc = market.get("fantasycalc") if isinstance(market.get("fantasycalc"), dict) else {}
    return {
        "fantasypros_overall_rank": fp.get("overall_rank"),
        "fantasypros_position_rank": fp.get("position_rank"),
        "fantasycalc_overall_rank": fc.get("overall_rank"),
        "fantasycalc_value": fc.get("value"),
    }


def build(root: Path, config_path: Path) -> dict[str, Any]:
    config = _load_json(config_path)
    if config.get("schema_version") != 1:
        raise RosterOverviewError("Unexpected managed roster overview config schema version")

    sources = config["sources"]
    league_path = root / sources["league"]
    signals_path = root / sources["managed_roster_signals"]
    state_path = root / sources["evaluation_state"]
    league = _load_json(league_path)
    signals = _load_json(signals_path)
    state = _load_json(state_path)
    _validate_state(state)

    team_id = str(config["managed_team"]["team_id"])
    managed_team = next((team for team in league.get("Teams") or [] if str(team.get("TeamID")) == team_id), None)
    if managed_team is None:
        raise RosterOverviewError(f"Managed team {team_id} not found in League.json")
    if str((signals.get("managed_team") or {}).get("team_id")) != team_id:
        raise RosterOverviewError("Managed roster signals belong to a different team")

    base_classifications, user_overrides = _index_classifications(state)
    roster_ids = {str(value) for value in managed_team.get("Roster") or []}
    taxi_ids = {str(value) for value in managed_team.get("Taxi") or []}
    reserve_ids = {str(value) for value in managed_team.get("Reserve") or []}
    held_ids = roster_ids | taxi_ids | reserve_ids
    active_ids = roster_ids - taxi_ids - reserve_ids

    taxi_phase = _derive_taxi_phase(league)
    roster_size = league.get("RosterSize") if isinstance(league.get("RosterSize"), list) else []
    fixed_starters, flex_slots, bench_slots = _fixed_starters(roster_size)
    active_capacity = len(roster_size)
    settings = league.get("Settings") if isinstance(league.get("Settings"), dict) else {}
    taxi_slots = int(ops.optional_number(settings.get("taxi_slots")) or 0)
    reserve_slots = int(ops.optional_number(settings.get("reserve_slots")) or 0)

    coverage_targets = state.get("coverage_targets") if isinstance(state.get("coverage_targets"), dict) else {}
    flex_positions = [str(item).upper() for item in (config.get("policies") or {}).get("flex_eligible_positions", ["RB", "WR", "TE"])]
    churn_target = int((config.get("policies") or {}).get("general_churn_target", 2))

    players: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    matched_signal_ids: set[str] = set()
    for source_player in signals.get("players") or []:
        player_id = str(source_player.get("player_id") or "")
        if not player_id or player_id not in held_ids:
            continue
        matched_signal_ids.add(player_id)
        classification = _effective_classification(source_player, base_classifications, user_overrides, state)
        role = classification["roster_role"]
        security = classification["roster_security"]
        sections = list(source_player.get("roster_sections") or [])
        area = _roster_area(sections)
        position = str(source_player.get("position") or "").upper()
        players.append(
            {
                "player_id": player_id,
                "name": source_player.get("name"),
                "position": position,
                "nfl_team": source_player.get("nfl_team"),
                "roster_area": area,
                "roster_sections": sections,
                "is_current_active": player_id in active_ids,
                "is_current_taxi": player_id in taxi_ids,
                "is_current_reserve": player_id in reserve_ids,
                "roster_role": role,
                "roster_security": security,
                "structural_function": _structural_function(role),
                "classification": classification,
                "app_data": source_player.get("app_data") or {},
                "injury": source_player.get("injury") or {},
                "market": _market_summary(source_player),
            }
        )
        if role is None or security is None:
            issues.append(
                {
                    "severity": "warning",
                    "kind": "unclassified_managed_player",
                    "player_id": player_id,
                    "name": source_player.get("name"),
                }
            )

    missing_signal_ids = sorted(held_ids - matched_signal_ids)
    for player_id in missing_signal_ids:
        issues.append({"severity": "error", "kind": "missing_managed_roster_signal", "player_id": player_id})

    effective_coverage_players = players if taxi_phase == "pre_lock" else [item for item in players if item["is_current_active"]]
    by_position: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in effective_coverage_players:
        by_position[item["position"]].append(item)

    coverage: dict[str, Any] = {}
    all_positions = sorted(set(by_position) | set(fixed_starters) | set(coverage_targets))
    for position in all_positions:
        target = coverage_targets.get(position) if isinstance(coverage_targets.get(position), dict) else {}
        floor_value = ops.optional_number(target.get("floor"))
        preferred_value = ops.optional_number(target.get("preferred"))
        floor = int(floor_value) if floor_value is not None else None
        preferred = int(preferred_value) if preferred_value is not None else None
        relevant = by_position.get(position, [])
        held_count = sum(1 for item in players if item["position"] == position)
        active_count = sum(1 for item in players if item["position"] == position and item["is_current_active"])
        coverage[position] = {
            "fixed_starter_requirement": fixed_starters.get(position, 0),
            "held_count": held_count,
            "current_active_count": active_count,
            "effective_prelock_or_locked_count": len(relevant),
            "startable_count": sum(1 for item in relevant if item["roster_role"] in STARTABLE_ROLES),
            "backup_count": sum(1 for item in relevant if item["roster_role"] == "backup"),
            "coverage_floor": floor,
            "preferred_coverage": preferred,
            "status": _coverage_status(len(relevant), floor, preferred),
        }

    required_skill_slots = sum(fixed_starters.get(position, 0) for position in flex_positions) + flex_slots
    startable_skill_players = [
        item
        for item in effective_coverage_players
        if item["position"] in flex_positions and item["roster_role"] in STARTABLE_ROLES
    ]

    for item in players:
        position_coverage = coverage.get(item["position"]) or {}
        floor = position_coverage.get("coverage_floor")
        effective_count = position_coverage.get("effective_prelock_or_locked_count", 0)
        coverage_protected = floor is not None and effective_count <= floor
        item["coverage_role"] = (
            "fixed_starter_pool"
            if item["roster_role"] in STARTABLE_ROLES and fixed_starters.get(item["position"], 0) > 0
            else "positional_coverage"
            if item["roster_role"] == "backup" and fixed_starters.get(item["position"], 0) > 0
            else "skill_pool"
            if item["position"] in flex_positions and item["roster_role"] in STARTABLE_ROLES
            else "development"
            if item["roster_role"] == "prospect"
            else "specialist"
            if item["roster_role"] == "specialist"
            else "unclassified"
        )
        item["coverage_protected"] = coverage_protected
        item["churn_eligible"] = bool(
            item["roster_security"] in BOUNDARY_SECURITY
            and item["structural_function"] != "specialist"
            and not coverage_protected
            and item["is_current_active"]
        )
        item["potential_churn_after_taxi_reassignment"] = bool(
            taxi_phase == "pre_lock"
            and item["roster_security"] in BOUNDARY_SECURITY
            and item["structural_function"] != "specialist"
            and not coverage_protected
        )

    boundary_pool = [item for item in players if item["potential_churn_after_taxi_reassignment"] or item["churn_eligible"]]
    boundary_pool.sort(
        key=lambda item: (
            0 if item["roster_security"] == "churn" else 1,
            item["classification"].get("boundary_priority") if item["classification"].get("boundary_priority") is not None else 9999,
            item["name"] or "",
        )
    )
    active_boundary = [item for item in boundary_pool if item["churn_eligible"]]

    seed_date = _parse_date(state.get("as_of"))
    generated_dt = _parse_datetime(signals.get("generated_at"))
    classification_age_days = None
    if seed_date and generated_dt:
        classification_age_days = (generated_dt.date() - seed_date).days

    source_records = [
        {
            "id": "league",
            "path": _relative(league_path, root),
            "content_sha256": ops.sha256_text(league_path.read_text(encoding="utf-8")),
        },
        {
            "id": "managed_roster_signals",
            "path": _relative(signals_path, root),
            "content_sha256": ops.sha256_text(signals_path.read_text(encoding="utf-8")),
        },
        {
            "id": "roster_evaluation_state",
            "path": _relative(state_path, root),
            "content_sha256": ops.sha256_text(state_path.read_text(encoding="utf-8")),
        },
    ]

    output = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": "managed-roster-overview",
        "generated_at": signals.get("generated_at"),
        "input_fingerprint": ops.sha256_text(ops.canonical_json(source_records)),
        "sources": source_records,
        "evaluation": {
            "mode": state.get("evaluation_mode", "hybrid_manual_v1"),
            "seed_as_of": state.get("as_of"),
            "classification_age_days": classification_age_days,
            "automatic_fields": [
                "roster_membership",
                "roster_area",
                "starter_requirements",
                "active_capacity",
                "taxi_phase",
                "position_counts",
                "coverage_status",
                "skill_pool_margin",
                "churn_eligibility_given_current_classification",
            ],
            "evaluative_fields": ["roster_role", "roster_security", "coverage_targets", "boundary_priority"],
            "user_override_count": len(user_overrides),
            "unclassified_count": sum(1 for item in players if item["roster_role"] is None),
            "target_state": "fully_automated_with_explainable_criteria_and_user_overrides",
        },
        "team": {
            "team_id": managed_team.get("TeamID"),
            "name": managed_team.get("Team"),
            "abbreviation": managed_team.get("TeamAbbr"),
            "held_player_count": len(held_ids),
        },
        "structure": {
            "capacity": {
                "regular_active_capacity": active_capacity,
                "current_active_count": len(active_ids),
                "taxi_slots": taxi_slots,
                "current_taxi_count": len(taxi_ids),
                "reserve_slots": reserve_slots,
                "current_reserve_count": len(reserve_ids),
                "hard_active_delta": active_capacity - len(active_ids),
            },
            "lineup": {
                "fixed_starters": fixed_starters,
                "flex_slots": flex_slots,
                "bench_slots": bench_slots,
            },
            "taxi": {
                "phase": taxi_phase,
                "binding": taxi_phase == "locked",
                "current_technical_occupants": [
                    {"player_id": item["player_id"], "name": item["name"]}
                    for item in players
                    if item["is_current_taxi"]
                ],
                "virtual_assignment_status": "not_automated_yet" if taxi_phase == "pre_lock" else "not_applicable",
                "interpretation": (
                    "Current preseason Taxi placement is technical only; final Taxi allocation must be optimized across eligible rookies before lock."
                    if taxi_phase == "pre_lock"
                    else "Actual Taxi occupants are binding after lock."
                ),
            },
            "coverage": coverage,
            "skill_pool": {
                "flex_eligible_positions": flex_positions,
                "required_skill_lineup_slots": required_skill_slots,
                "startable_skill_pool": len(startable_skill_players),
                "skill_pool_margin": len(startable_skill_players) - required_skill_slots,
                "startable_players": [
                    {"player_id": item["player_id"], "name": item["name"], "position": item["position"]}
                    for item in startable_skill_players
                ],
            },
            "churn": {
                "target_general_slots": churn_target,
                "assignment_status": "provisional_pre_lock" if taxi_phase == "pre_lock" else "current_locked_roster",
                "current_active_candidate_count": len(active_boundary),
                "candidate_pool_count": len(boundary_pool),
                "guardrail_status": (
                    "provisional_requires_virtual_taxi_assignment"
                    if taxi_phase == "pre_lock"
                    else "met"
                    if len(active_boundary) >= churn_target
                    else "below_target"
                ),
                "candidate_pool": [
                    {
                        "player_id": item["player_id"],
                        "name": item["name"],
                        "position": item["position"],
                        "security": item["roster_security"],
                        "current_area": item["roster_area"],
                        "boundary_priority": item["classification"].get("boundary_priority"),
                    }
                    for item in boundary_pool
                ],
            },
        },
        "players": sorted(players, key=lambda item: (item["position"], item["name"] or "")),
        "quality": {
            "status": "error" if any(issue["severity"] == "error" for issue in issues) else "warning" if issues else "ok",
            "issue_count": len(issues),
            "issues": issues,
            "limitations": [
                "Role and security are hybrid evaluative fields in v1 and are not yet fully machine-derived.",
                "Pre-lock Taxi optimization is intentionally not automated yet; current Taxi placement is not treated as strategic truth.",
                "Coverage targets are versioned strategic inputs, not immutable league constants.",
                "User overrides remain authoritative over automated classifications when the future classifier is introduced.",
            ],
        },
    }
    return output


def render_markdown(data: dict[str, Any]) -> str:
    structure = data["structure"]
    capacity = structure["capacity"]
    skill = structure["skill_pool"]
    churn = structure["churn"]
    taxi = structure["taxi"]
    lines = [
        "# Mighty Giants – Current Roster Overview",
        "",
        f"Generated: `{data.get('generated_at')}`  ",
        f"Evaluation mode: `{data['evaluation']['mode']}`  ",
        f"Taxi phase: `{taxi['phase']}`",
        "",
        "## Roster status",
        "",
        f"- Active: **{capacity['current_active_count']} / {capacity['regular_active_capacity']}** (delta {capacity['hard_active_delta']:+d})",
        f"- Taxi: **{capacity['current_taxi_count']} / {capacity['taxi_slots']}**; binding: **{'yes' if taxi['binding'] else 'no'}**",
        f"- Reserve: **{capacity['current_reserve_count']} / {capacity['reserve_slots']}**",
        f"- Startable Skill Pool: **{skill['startable_skill_pool']} / {skill['required_skill_lineup_slots']}** (margin {skill['skill_pool_margin']:+d})",
        f"- General churn target: **{churn['target_general_slots']}**; status: `{churn['guardrail_status']}`",
        "",
        "## Position coverage",
        "",
        "| Pos | Held | Active | Fixed starters | Startable | Backup | Floor | Preferred | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for position, values in structure["coverage"].items():
        lines.append(
            "| {position} | {held} | {active} | {fixed} | {startable} | {backup} | {floor} | {preferred} | {status} |".format(
                position=position,
                held=values["held_count"],
                active=values["current_active_count"],
                fixed=values["fixed_starter_requirement"],
                startable=values["startable_count"],
                backup=values["backup_count"],
                floor=values["coverage_floor"] if values["coverage_floor"] is not None else "–",
                preferred=values["preferred_coverage"] if values["preferred_coverage"] is not None else "–",
                status=values["status"],
            )
        )

    lines.extend(
        [
            "",
            "## Players",
            "",
            "| Pos | Player | Area | Role | Security | Structural function | Coverage role | Churn |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in data["players"]:
        lines.append(
            f"| {item['position']} | {item['name']} | {item['roster_area']} | "
            f"{item['roster_role'] or 'unclassified'} | {item['roster_security'] or 'unclassified'} | "
            f"{item['structural_function']} | {item['coverage_role']} | "
            f"{'yes' if item['churn_eligible'] else 'no'} |"
        )

    lines.extend(["", "## Churn boundary pool", ""])
    if churn["candidate_pool"]:
        for candidate in churn["candidate_pool"]:
            lines.append(
                f"- {candidate['name']} ({candidate['position']}) — `{candidate['security']}` — "
                f"area `{candidate['current_area']}` — priority `{candidate['boundary_priority']}`"
            )
    else:
        lines.append("- No current boundary candidate available.")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is a current read model, not permanent player truth. Roster membership, capacity, Taxi phase and structural counts are derived automatically. Role/security and current coverage targets are still hybrid evaluative inputs in v1. User overrides remain possible and are surfaced explicitly in the JSON contract.",
            "",
        ]
    )
    return "\n".join(lines)


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def write_outputs(root: Path, config_path: Path, data: dict[str, Any]) -> list[str]:
    config = _load_json(config_path)
    outputs = config["outputs"]
    json_path = root / outputs["json"]
    markdown_path = root / outputs["markdown"]
    changed: list[str] = []
    json_content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    markdown_content = render_markdown(data)
    if write_if_changed(json_path, json_content):
        changed.append(_relative(json_path, root))
    if write_if_changed(markdown_path, markdown_content):
        changed.append(_relative(markdown_path, root))
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("fantasy-management/automation/managed-roster-overview.json"),
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    result = build(root, config_path)
    if args.check:
        print(
            "Validated managed roster overview: players={}; quality={}; unclassified={}.".format(
                len(result["players"]),
                result["quality"]["status"],
                result["evaluation"]["unclassified_count"],
            )
        )
        return 0
    changed = write_outputs(root, config_path, result)
    if changed:
        print("Updated:")
        for path in changed:
            print(f"- {path}")
    else:
        print("No managed roster overview changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
